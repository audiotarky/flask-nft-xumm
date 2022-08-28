from os import environ
import sqlite3
from xrpl.transaction import get_transaction_from_hash
from urllib.parse import urlparse, urljoin
from flask import request

from decorators import time_cache
from xrpl.utils import hex_to_str
from xrpl.models.requests import AccountNFTs
from xrpl.clients import JsonRpcClient

environ["XUMM_CREDS_PATH"] = "xumm_creds.json"

ledger_url = "http://xls20-sandbox.rippletest.net:51234"
client = JsonRpcClient(ledger_url)


def offer_id_from_transaction_hash(txn_hash, client):
    print("searching for", txn_hash)
    txn = get_transaction_from_hash(txn_hash, client)
    print(txn)
    for node in txn.result["meta"]["AffectedNodes"]:
        for node_type in ["CreatedNode", "ModifiedNode"]:
            if node_type in node:
                if node[node_type]["LedgerEntryType"] == "NFTokenOffer":
                    print("found", node[node_type]["LedgerIndex"], "for", txn_hash)
                    return node[node_type]["LedgerIndex"]


def cache_offer_to_db(token_id, sale_offer, signed, seller):
    con = sqlite3.connect("xumm.db")
    cur = con.cursor()
    cur.execute(
        "insert into stock values (?, ?, ?, ?)",
        (token_id, sale_offer, signed, seller),
    )
    con.commit()
    con.close()


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


class XUMMWalletProxy:
    def __init__(self, address):
        self.address = address

    @property
    def nfts(self, as_string=False):
        data = self._get_wallet_nfts()
        if as_string:
            return [hex_to_str(nft["URI"]) for nft in data.result["account_nfts"]]
        return [nft["URI"] for nft in data.result["account_nfts"]]

    @time_cache(60)
    def _get_wallet_nfts(self, force=False):
        """Retrieve the users NFTs from their wallet, caching the result for
        60 seconds.

        Pass in a random value to force (or a value that hasn't been used in
        the past 60s) to force a refresh of the cache. Useful after you make a
        transaction that you know affects the wallets NFTs.
        """
        return client.request(AccountNFTs(account=self.address, limit=150))
