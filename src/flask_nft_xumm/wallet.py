"""
Implements one endpoint:

GET /wallet - lists all NFTs owned by the logged in user
"""
import sqlite3
from collections import defaultdict
from http import client

import requests
from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from xrpl.models.requests import AccountNFTs, NFTSellOffers
from xrpl.models.transactions import Memo, NFTokenCancelOffer, NFTokenMint
from xrpl.utils import hex_to_str, str_to_hex
from xrplpers.nfts.entities import TokenID, TransferFee
from xrplpers.xumm.transactions import submit_xumm_transaction

from flask_nft_xumm.utils import get_bithomp, get_nft_list_for_account

wallet = Blueprint("wallet", __name__, template_folder="templates")


@wallet.route("/wallet")
@login_required
def index():
    offer_lookup = defaultdict(list)
    con = sqlite3.connect("xumm.db")
    cur = con.cursor()
    sql = "select token_id, sale_offer from stock where seller = ? and signed=1"
    for row in cur.execute(sql, [current_user.wallet.address]):
        current_app.logger.debug(row)
        offer_lookup[row[0]].append(row[1])
    current_app.logger.debug(offer_lookup)
    con.close()

    nfts = []
    for n in current_user.wallet.nfts:
        # We could look up offers here, but it's slow - round trip to the
        # ledger for each NFT. If you need correctness, use the following:
        # offers = client.request(NFTSellOffers(tokenid=n["NFTokenID"])).result
        current_app.logger.debug(n)
        nfts.append(
            {
                "issuer": n["Issuer"],
                "id": n["NFTokenID"],
                "fee": n["TransferFee"],
                "uri": hex_to_str(n["URI"]),
                "serial": n["nft_serial"],
                "offers": offer_lookup.get(n["NFTokenID"], []),
            }
        )
    return render_template("wallet.html", nfts=nfts)


@wallet.route("/wallet/cancel/<offer>", methods=["GET", "POST"])
@login_required
def cancel(offer):
    current_app.logger.debug("offer is", offer)
    the_wallet = current_user.wallet.address
    if request.method == "GET":
        cancel = NFTokenCancelOffer(account=the_wallet, nftoken_offers=[offer])
        r = submit_xumm_transaction(
            cancel.to_xrpl(), user_token=current_user.user_token
        )
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


@wallet.route("/wallet/mint", methods=["GET", "POST"])
@login_required
def mint():
    if request.method == "GET":
        return render_template("minter.html")
    elif request.json:
        return jsonify({"ok": True})
    else:
        # Call the XUM API to have the signing handled there
        the_wallet = current_user.wallet.address
        memoes = [Memo.from_dict({"memo_data": str_to_hex("Minted by Audiotarky")})]
        if "memo" in request.form and request.form["memo"]:
            memoes.append(
                Memo.from_dict({"memo_data": str_to_hex(request.form["memo"])})
            )
        mint_args = {
            "account": the_wallet,
            "flags": 8,
            "uri": str_to_hex(request.form["uri"]),
            "memos": memoes,
            "transfer_fee": TransferFee.from_percent(int(request.form["fee"])).value,
            "nftoken_taxon": 0,
        }
        mint = NFTokenMint.from_dict(mint_args)
        current_app.logger.debug(mint.to_xrpl())
        try:
            xumm_data = submit_xumm_transaction(
                mint.to_xrpl(), user_token=current_user.user_token
            )
        except requests.HTTPError as h:
            current_app.logger.debug(h.response.text)
            raise h

        current_app.logger.debug(xumm_data)

        return render_template(
            "minter.html",
            qr=xumm_data["refs"]["qr_png"],
            url=xumm_data["next"]["always"],
            ws=xumm_data["refs"]["websocket_status"],
        )
