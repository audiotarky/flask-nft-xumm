"""
Implements four endpoints:

GET /shop/$OWNER - lists all NFTs for sale from a given owner
GET /shop/$ISSUER - lists all NFTs for sale from a given issuer, regardless of owner

GET /sell/$NFT - buy the NFT as a brokered transaction

GET /sell/$NFT - put the NFT up for sale
"""
import json
import sqlite3
import sys

py_version = sys.version_info
if py_version.major == 3 and py_version.minor >= 9:
    from functools import cache
else:
    from functools import lru_cache as cache
from os import environ
from pathlib import Path

from flask import (
    Blueprint,
    Markup,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from requests import HTTPError
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountNFTs, NFTSellOffers, NFTBuyOffers
from xrpl.models.transactions import (
    Memo,
    NFTokenAcceptOffer,
    NFTokenCreateOffer,
    NFTokenCreateOfferFlag,
)
from xrpl.transaction import (
    safe_sign_and_autofill_transaction,
    send_reliable_submission,
)
from xrpl.utils import drops_to_xrp, hex_to_str, str_to_hex, xrp_to_drops
from xrpl.wallet import Wallet
from xrplpers.nfts.entities import TokenID
from xrplpers.xumm.transactions import get_xumm_transaction, submit_xumm_transaction

from utils import (
    check_login,
    cache_offer_to_db,
    offer_id_from_transaction_hash,
)

trade = Blueprint("trade", __name__)
ledger_url = "http://xls20-sandbox.rippletest.net:51234"
client = JsonRpcClient(ledger_url)
environ["XUMM_CREDS_PATH"] = "xumm_creds.json"
creds = json.loads(Path("creds.json").read_text())
marketplace_wallet = Wallet(seed=creds["secret"], sequence=creds["sequence"])


@cache
def get_nft_list_for_account(account, marker=None):
    print("uncached")
    return client.request(AccountNFTs(account=account, limit=150))


environ["XUMM_CREDS_PATH"] = "xumm_creds.json"


@trade.route("/shop")
@trade.route("/shop/<issuer>")
@check_login
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

        offers = client.request(NFTSellOffers(tokenid=t.to_str())).result
        result = get_nft_list_for_account(row[2])
        for n in offers.get("offers", []):
            detail = [
                x
                for x in result.result["account_nfts"]
                if x["TokenID"] == offers["tokenid"]
            ][0]
            if n["owner"] == row[2]:
                nfts.append(
                    {
                        "issuer": t.issuer,
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


@trade.route("/buy", methods=["POST", "GET"])
@trade.route("/buy/<nft>", methods=["POST", "GET"])
@check_login
def buy(nft=None):
    if request.method == "POST":

        # BROKER MODE IN DEVELOPMENT
        # Now do the NFTokenAcceptOffer as a broker
        # https://github.com/XRPLF/XRPL-Standards/discussions/46#discussioncomment-1970982
        # con = sqlite3.connect("xumm.db")
        # cur = con.cursor()
        # # TODO: look up the sell offer index form the DB here
        # sale_txn = cur.execute(
        #     "select sale_offer from stock where token_id = ?",
        #     [nft],
        # ).fetchone()[0]
        # con.close()

        data = json.loads(request.json)
        print(data)
        # xumm_data = {
        #     "buy": get_xumm_transaction(data["payload_uuidv4"]),
        #     "sell": get_xumm_transaction(sale_txn),
        # }
        # nft = xumm_data["buy"]["payload"]["request_json"]["TokenID"]

        # ammount = int(xumm_data["buy"]["payload"]["request_json"]["Amount"])
        # broker_fee = str(int(ammount - (ammount / 1.1)))

        # purchase = {
        #     "account": creds["address"],
        #     "broker_fee": broker_fee,
        #     "buy_offer": offer_id_from_transaction_hash(
        #         xumm_data["buy"]["response"]["txid"], client
        #     ),
        #     "sell_offer": offer_id_from_transaction_hash(
        #         xumm_data["sell"]["response"]["txid"], client
        #     ),
        # }

        # sells = client.request(NFTSellOffers(tokenid=nft)).result["offers"]
        # assert len([o for o in sells if o["index"] == purchase["sell_offer"]]) == 1

        # print(purchase)
        # accept = NFTokenAcceptOffer.from_dict(purchase)
        # accept.validate()

        # purchase_txn = safe_sign_and_autofill_transaction(
        #     accept, marketplace_wallet, client
        # )
        # print(purchase_txn)

        # submitted_purchase_txn = send_reliable_submission(purchase_txn, client)
        # print(submitted_purchase_txn)
        return '{"ok": true}'
        # TODO: if the sale falls through, cancel the buy offer via NFTokenCancelOffer
    the_wallet = session.get("user_wallet", False)
    if not nft:
        return redirect(url_for("trade.shop"))
    # BROKER MODE IN DEVELOPMENT
    # Create the purchase offer then bring the two together as a broker
    # purchase = {
    #     "account": the_wallet,
    #     "owner": offers["offers"][-1]["owner"],
    #     "amount": str(int(1.1 * int(offers["offers"][-1]["amount"]))),
    #     "token_id": token.to_str(),
    # }
    # print(purchase)
    # buy = NFTokenCreateOffer.from_dict(purchase)
    offers = client.request(NFTSellOffers(tokenid=nft)).result
    if not offers.get("offers", False):
        flash("No sell offers available")
        return redirect(url_for("trade.shop"))

    buy = NFTokenAcceptOffer(
        account=the_wallet,
        sell_offer=offers["offers"][-1]["index"],
    )
    try:
        r = submit_xumm_transaction(buy.to_xrpl(), user_token=session["user_token"])
    except HTTPError as e:
        print(e)
    xumm_data = r.json()
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
@check_login
def sell(nft=None):
    """
    Create a sale offer (NFTokenCreateOffer), have the owner sign it & store
    the transaction id to the database.
    """
    print("selling things")
    if request.method == "POST" and nft:
        # Store the Sell offer transaction id
        con = sqlite3.connect("xumm.db")
        cur = con.cursor()
        sell_offer = get_xumm_transaction(json.loads(request.json)["payload_uuidv4"])
        txn = sell_offer["response"]["txid"]
        offer_id = offer_id_from_transaction_hash(txn, client)

        cur.execute(
            "update stock set signed = 1, sale_offer = ? where sale_offer = ?",
            [offer_id, json.loads(request.json)["payload_uuidv4"]],
        )
        con.commit()
        con.close()
        return jsonify({"ok": True})
    elif request.method == "POST":
        # Create the sale offer, and have XUMM generate the QR to let the seller sign it
        offers = client.request(NFTSellOffers(tokenid=request.form["tokenid"])).result
        if len(offers.get("offers", [])) > 0:
            _flash_nft_sell_exists(request.form["tokenid"], offers)

            return render_template(
                "sell.html", nft=request.form["tokenid"], cant_sell=True
            )
        token = TokenID.from_hex(request.form["tokenid"])
        the_wallet = session.get("user_wallet", False)
        price = xrp_to_drops(int(request.form["price"]))
        # TODO: set expires
        sell = NFTokenCreateOffer(
            account=the_wallet,
            amount=str(price),
            token_id=token.to_str(),
            flags=[NFTokenCreateOfferFlag(1)],
        )
        # Call the XUM API to have the signing handled there
        r = submit_xumm_transaction(sell.to_xrpl(), user_token=session["user_token"])
        xumm_data = r.json()
        print(xumm_data)
        # offer_id_from_transaction_hash()

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
        offers = client.request(NFTSellOffers(tokenid=nft)).result
        cant_sell = False
        if len(offers.get("offers", [])) > 0:
            # TODO: add the sale offer to the DB if not in it already
            _flash_nft_sell_exists(nft, offers)
            cant_sell = True
        return render_template("sell.html", nft=nft, cant_sell=cant_sell)


@trade.route("/sold", methods=["GET"])
@trade.route("/sold/<nft>", methods=["GET"])
@check_login
def sold(nft=None):
    if nft:
        return render_template("sold.html", nft=nft)
    else:
        return redirect(url_for("trade.shop"))


# TODO: unlist a token via a NFTokenCancelOffer
