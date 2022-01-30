"""
Implements one endpoint:

GET /wallet - lists all NFTs owned by the logged in user
"""

from flask import Blueprint, redirect, render_template, session, url_for
from xrpl.account import get_account_info
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountNFTs
from xrpl.utils import drops_to_xrp, hex_to_str

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
    # TODO: list buy/sell offers that are open for the things in the wallet
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
