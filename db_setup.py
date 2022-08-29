import sqlite3

con = sqlite3.connect("xumm.db")
cur = con.cursor()
cur.execute(
    "CREATE TABLE stock (token_id text, sale_offer text, signed integer, seller text)"
)
cur.execute(
    "create table wallet_cache (user_token varchar primary key, wallet_address varchar)"
)
con.commit()
con.close()
