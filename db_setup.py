import sqlite3

con = sqlite3.connect("xumm.db")
cur = con.cursor()
cur.execute(
    "CREATE TABLE stock (token_id text, signing_txn text, signed integer, seller text)"
)
con.commit()
con.close()
