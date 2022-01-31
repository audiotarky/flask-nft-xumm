from functools import wraps

from flask import redirect, session, url_for
from xrpl.transaction import get_transaction_from_hash
import sqlite3


def check_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        the_wallet = session.get("user_wallet", False)
        if not the_wallet:
            return redirect(url_for("index"))

        return f(*args, **kwargs)

    return decorated_function


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
