"""
Implements one endpoint:

GET /wallet - lists all NFTs owned by the logged in user
"""

from xrpl.clients import JsonRpcClient
from xrpl.account import get_account_info
from xrpl.models.requests import AccountNFTs
from xrpl.utils import hex_to_str, drops_to_xrp
from flask import Blueprint, render_template, session, redirect, url_for

wallet = Blueprint("wallet", __name__)


@wallet.route("/wallet")
def index():
    the_wallet = session.get("user_wallet", False)
    if not the_wallet:
        return redirect(url_for("index"))
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
    for n in result["account_nfts"]:
        nfts.append(
            {
                "issuer": n["Issuer"],
                "id": n["TokenID"],
                "fee": n["TransferFee"],
                "uri": hex_to_str(n["URI"]),
                "serial": n["nft_serial"],
            }
        )
    return render_template("wallet.html", info=info, nfts=nfts)
