"""
Implements one endpoint:

GET /wallet - lists all NFTs owned by the logged in user
"""
from collections import defaultdict
from crypt import methods
from flask import Blueprint, jsonify, render_template, session, request
from xrpl.account import get_account_info
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountNFTs
from xrpl.models.transactions import NFTokenCancelOffer
from xrpl.utils import drops_to_xrp, hex_to_str
from xrplpers.xumm.transactions import submit_xumm_transaction
import sqlite3
from utils import check_login

wallet = Blueprint("wallet", __name__)


@wallet.route("/wallet")
@check_login
def index():
    the_wallet = session.get("user_wallet", False)
    client = JsonRpcClient("http://xls20-sandbox.rippletest.net:51234")
    result = get_account_info(the_wallet, client).result
    info = {
        "address": the_wallet,
        "minted": result["account_data"].get("MintedTokens", 0),
        "balance_xrp": str(drops_to_xrp(result["account_data"]["Balance"])),
        "balance_drops": result["account_data"]["Balance"],
    }

    result = client.request(AccountNFTs(account=the_wallet, limit=150)).result
    info["nft_count"] = len(result["account_nfts"])
    nfts = []
    con = sqlite3.connect("xumm.db")
    cur = con.cursor()
    offer_lookup = defaultdict(list)
    sql = "select token_id, sale_offer from stock where seller = ? and signed=1"
    for row in cur.execute(sql, [the_wallet]):
        print(row)
        offer_lookup[row[0]].append(row[1])
    print(offer_lookup)
    con.close()
    for n in result["account_nfts"]:
        # We could look up offers here, but it's slow - round trip to the ledge for each NFT
        # offers = client.request(NFTSellOffers(tokenid=n["TokenID"])).result
        nfts.append(
            {
                "issuer": n["Issuer"],
                "id": n["TokenID"],
                "fee": n["TransferFee"],
                "uri": hex_to_str(n["URI"]),
                "serial": n["nft_serial"],
                "offers": offer_lookup.get(n["TokenID"], []),
            }
        )
    return render_template("wallet.html", info=info, nfts=nfts)


@wallet.route("/wallet/cancel/<offer>", methods=["GET", "POST"])
@check_login
def cancel(offer):
    print("offer is", offer)
    the_wallet = session.get("user_wallet", False)
    if request.method == "GET":
        cancel = NFTokenCancelOffer(account=the_wallet, token_offers=[offer])
        r = submit_xumm_transaction(cancel.to_xrpl(), user_token=session["user_token"])
        xumm_data = r.json()
        return render_template(
            "cancel.html",
            offer=offer,
            qr=xumm_data["refs"]["qr_png"],
            url=xumm_data["next"]["always"],
            ws=xumm_data["refs"]["websocket_status"],
        )
    else:
        # TODO: verify the XUMM transaction coming in
        con = sqlite3.connect("xumm.db")
        cur = con.cursor()
        sql = "delete from stock where sale_offer=?"
        cur.execute(sql, [offer])
        con.commit()
        con.close()

        return jsonify({"ok": True})