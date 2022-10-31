"""
Implements four endpoints:

GET /shop/$OWNER - lists all NFTs for sale from a given owner
GET /shop/$ISSUER - lists all NFTs for sale from a given issuer, regardless of owner

GET /sell/$NFT - buy the NFT as a brokered transaction

GET /sell/$NFT - put the NFT up for sale
"""
import json
import sqlite3

from os import environ
from pathlib import Path

from flask import (
    Blueprint,
    Markup,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from requests import HTTPError

from xrpl.models.requests import AccountNFTs, NFTSellOffers
from xrpl.models.transactions import (
    NFTokenAcceptOffer,
    NFTokenCreateOffer,
    NFTokenCreateOfferFlag,
)
from xrpl.transaction import (
    safe_sign_and_autofill_transaction,
    send_reliable_submission,
)
from xrpl.utils import drops_to_xrp, hex_to_str, xrp_to_drops

from xrplpers.nfts.entities import TokenID
from xrplpers.xumm.transactions import get_xumm_transaction, submit_xumm_transaction

from utils import (
    cache_offer_to_db,
    get_nft_list_for_account,
    offer_id_from_transaction_hash,
)

trade = Blueprint("trade", __name__)
environ["XUMM_CREDS_PATH"] = "xumm_creds.json"


@trade.route("/shop")
@trade.route("/shop/<issuer>")
# @login_required
def shop(issuer=None):
    info = None
    nfts = []
    con = sqlite3.connect("xumm.db")
    cur = con.cursor()
    sql = "select token_id, sale_offer, seller from stock where signed = 1"

    for row in cur.execute(sql):
        t = TokenID.from_hex(row[0])
        # TODO: narrow the search over NFTokenPage
        # https://xrpl.org/nftokenpage.html
        # TODO: Cross reference against all sell offers for a token
        # https://xrpl-py.readthedocs.io/en/stable/source/xrpl.models.requests.html?highlight=NFToken#xrpl.models.requests.NFTSellOffers.tokenid

        offers = current_app.xrpl_client.request(
            NFTSellOffers(nft_id=t.to_str())
        ).result
        result = get_nft_list_for_account(row[2])
        for n in offers.get("offers", []):
            details = [x for x in result if x["NFTokenID"] == t.to_str()]
            if len(details):
                detail = details[0]
                if n["owner"] == row[2]:
                    nfts.append(
                        {
                            "issuer": t.issuer_as_string,
                            "id": t.to_str(),
                            "fee": t.transfer_fee,
                            "uri": hex_to_str(detail["URI"]),
                            "serial": detail["nft_serial"],
                            "owner": row[2],
                            "offer": n,
                        }
                    )
    con.close()
    return render_template(
        "shop.html",
        info=info,
        nfts=nfts,
        drops_to_xrp=drops_to_xrp,
    )


def calculate_broker_fee(amount):
    """
    Takes a numeric amount and returns the 10% or 1XRP broker fee
    """
    x = int(0.1 * int(amount))
    return str(x) if x > int(xrp_to_drops(1)) else xrp_to_drops(1)


def make_buy_offer(the_wallet, offers):
    the_offer = offers["offers"][-1]
    fee = calculate_broker_fee(the_offer["amount"])
    amount = int(the_offer["amount"]) + int(fee)
    purchase = {
        "account": the_wallet,
        "owner": the_offer["owner"],
        "amount": str(amount),
        "nftoken_id": offers["nft_id"],
    }
    buy = NFTokenCreateOffer.from_dict(purchase)
    return submit_xumm_transaction(buy.to_xrpl(), user_token=current_user.user_token)


def accept_brokered_offer(offers, payload):
    xumm_data = {"buy": get_xumm_transaction(payload), "sell": offers["offers"][-1]}
    print(xumm_data)
    nft = xumm_data["buy"]["payload"]["request_json"]["NFTokenID"]
    ammount = int(xumm_data["sell"]["amount"])
    broker_fee = calculate_broker_fee(ammount)
    purchase = {
        "account": current_app.creds["address"],
        "nftoken_broker_fee": broker_fee,
        "nftoken_buy_offer": offer_id_from_transaction_hash(
            xumm_data["buy"]["response"]["txid"], current_app.xrpl_client
        ),
    }

    sells = current_app.xrpl_client.request(NFTSellOffers(nft_id=nft)).result["offers"]

    print("ammount is", ammount)
    print("purchase is", purchase)
    assert (
        len(
            [
                o
                for o in sells
                if o["nft_offer_index"] == xumm_data["sell"]["nft_offer_index"]
            ]
        )
        >= 1
    )
    purchase["nftoken_sell_offer"] = sells[0]["nft_offer_index"]

    accept = NFTokenAcceptOffer.from_dict(purchase)
    accept.validate()

    purchase = safe_sign_and_autofill_transaction(
        accept, current_app.marketplace_wallet, current_app.xrpl_client
    )
    purchase_txn = send_reliable_submission(purchase, current_app.xrpl_client)
    return purchase_txn


@trade.route("/buy", methods=["POST", "GET"])
@trade.route("/buy/<nft>", methods=["POST", "GET"])
@login_required
def buy(nft=None):
    if not nft:
        return redirect(url_for("trade.shop"))
    offers = current_app.xrpl_client.request(NFTSellOffers(nft_id=nft)).result
    if not offers.get("offers", False):
        flash("No sell offers available")
        return redirect(url_for("trade.shop"))
    if request.method == "POST":
        data = json.loads(request.json)
        return jsonify({"status": "ok"})
        # TODO: if the sale falls through, cancel the buy offer via NFTokenCancelOffer
    the_wallet = current_user.wallet.address

    confirmation = request.args.get("confirm", None)
    if confirmation:
        # Conclude sale in broker mode
        # Create the purchase offer then bring the two together as a broker
        # Need to show the transaction or something here
        sale_txn_data = accept_brokered_offer(offers, confirmation)
        return render_template(
            "buy.html",
            offer=offers["offers"][-1],
            nft=nft,
            drops_to_xrp=drops_to_xrp,
            confirmation=True,
            sale=sale_txn_data,
        )
    # First QR code to sign the buy offer at the price + the broker fee
    xumm_data = make_buy_offer(the_wallet, offers)
    if offers["offers"][-1]["owner"] == the_wallet:
        flash("You own this NFT")
    return render_template(
        "buy.html",
        qr=xumm_data["refs"]["qr_png"],
        url=xumm_data["next"]["always"],
        ws=xumm_data["refs"]["websocket_status"],
        offer=offers["offers"][-1],
        nft=nft,
        drops_to_xrp=drops_to_xrp,
    )


def _flash_nft_sell_exists(nft, offers):
    offers = [x["index"] for x in offers["offers"]]
    flash(Markup(render_template("_nft_sale_exists.html", nft=nft, offers=offers)))


@trade.route("/sell", methods=["POST", "GET"])
@trade.route("/sell/<nft>", methods=["POST", "GET"])
@login_required
def sell(nft=None):
    """
    Create a sale offer (NFTokenCreateOffer), have the owner sign it & store
    the transaction id to the database.
    """
    if request.method == "POST" and nft:
        # Store the Sell offer transaction id
        con = sqlite3.connect("xumm.db")
        cur = con.cursor()
        sell_offer = get_xumm_transaction(json.loads(request.json)["payload_uuidv4"])
        txn = sell_offer["response"]["txid"]
        offer_id = offer_id_from_transaction_hash(txn, current_app.xrpl_client)

        cur.execute(
            "update stock set signed = 1, sale_offer = ? where sale_offer = ?",
            [offer_id, json.loads(request.json)["payload_uuidv4"]],
        )
        con.commit()
        con.close()
        return jsonify({"ok": True})
    elif request.method == "POST":
        # Create the sale offer, and have XUMM generate the QR to let the seller sign it
        offers = current_app.xrpl_client.request(
            NFTSellOffers(nft_id=request.form["tokenid"])
        ).result
        if len(offers.get("offers", [])) > 0:
            _flash_nft_sell_exists(request.form["tokenid"], offers)

            return render_template(
                "sell.html", nft=request.form["tokenid"], cant_sell=True
            )
        token = TokenID.from_hex(request.form["tokenid"])
        the_wallet = current_user.wallet.address
        price = xrp_to_drops(float(request.form["price"]))
        # TODO: set expires
        sell = NFTokenCreateOffer(
            account=the_wallet,
            amount=str(price),
            nftoken_id=token.to_str(),
            flags=[NFTokenCreateOfferFlag(1)],
        )
        # Call the XUMM API to have the signing handled there
        xumm_data = submit_xumm_transaction(
            sell.to_xrpl(), user_token=current_user.user_token
        )

        cache_offer_to_db(token.to_str(), xumm_data["uuid"], 0, the_wallet)

        qr = xumm_data["refs"]["qr_png"]
        url = xumm_data["next"]["always"]
        return render_template(
            "sell.html",
            qr=qr,
            url=url,
            ws=xumm_data["refs"]["websocket_status"],
            token=token.to_str(),
            price=drops_to_xrp(price),
        )
    elif not nft:
        # Bounce to the index page
        return redirect(url_for("index"))
    else:
        # Render the form to list the specified NFT
        token = TokenID.from_hex(nft)
        offers = current_app.xrpl_client.request(NFTSellOffers(nft_id=nft)).result
        cant_sell = False
        if len(offers.get("offers", [])) > 0:
            # TODO: add the sale offer to the DB if not in it already
            _flash_nft_sell_exists(nft, offers)
            cant_sell = True
        return render_template("sell.html", nft=nft, cant_sell=cant_sell)


@trade.route("/sold", methods=["GET"])
@trade.route("/sold/<nft>", methods=["GET"])
@login_required
def sold(nft=None):
    if nft:
        return render_template("sold.html", nft=nft)
    else:
        return redirect(url_for("trade.shop"))
