import sqlite3

con = sqlite3.connect("xumm.db")
cur = con.cursor()
cur.execute(
    "CREATE TABLE stock (token_id text, sale_offer text, signed integer, seller text)"
)
con.commit()
con.close()
