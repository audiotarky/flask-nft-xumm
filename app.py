import json
import logging
import sqlite3
import sys
import uuid
from pathlib import Path

from flask import Flask, current_app, redirect, render_template, url_for
from flask_login import LoginManager, current_user, login_required, logout_user
from flask_login.signals import user_logged_in
from xrpl.clients import JsonRpcClient, WebsocketClient
from xrpl.wallet import Wallet

from flask_nft_xumm.login import XUMMUser, login


def create_app():

    statics = Path(sys.modules[XUMMUser.__module__].__file__)
    statics = statics / "../static"
    app = Flask(__name__, static_folder=statics.resolve())
    app.config.from_object(__name__)
    app.secret_key = str(uuid.uuid1())
    app.creds = json.loads(Path("creds.json").read_text())
    app.config.ledger_url = app.creds["ledger"]
    app.xrpl_client = WebsocketClient(app.config.ledger_url)

    from flask_nft_xumm.detail import detail as detail_blueprint
    from flask_nft_xumm.nft import nft as nft_blueprint
    from flask_nft_xumm.trade import trade as trade_blueprint
    from flask_nft_xumm.wallet import wallet as wallet_blueprint

    app.register_blueprint(detail_blueprint)
    app.register_blueprint(trade_blueprint)
    app.register_blueprint(wallet_blueprint)
    app.register_blueprint(login, url_prefix="/login")
    app.register_blueprint(nft_blueprint, url_prefix="/nft")

    app.marketplace_wallet = Wallet(
        seed=app.creds["secret"], sequence=app.creds["sequence"]
    )
    return app


app = create_app()

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "/login"
login_manager.refresh_view = "/login"

login_manager.needs_refresh_message = "Session timed out, please re-login"
login_manager.needs_refresh_message_category = "info"

login_manager.session_protection = "strong"


def wallet_cache_put(key, value):
    current_app.logger.debug(f"wallet_cache_put: {key}: {value}")
    con = sqlite3.connect("xumm.db")
    with con:
        sql = "insert into wallet_cache (user_token, wallet_address) values (:user_token, :wallet_address)"
        sql += "ON CONFLICT(user_token) DO UPDATE SET wallet_address=:wallet_address"
        con.execute(sql, {"user_token": key, "wallet_address": value})
    con.close()


def wallet_cache_get(key):
    current_app.logger.debug(f"wallet_cache_get: {key}")
    con = sqlite3.connect("xumm.db")
    cur = con.cursor()
    sql = "select wallet_address from wallet_cache where user_token = ?"
    result = cur.execute(sql, [key]).fetchone()
    con.close()
    current_app.logger.debug(f"wallet_cache_get result: {result}")
    if not result:
        raise KeyError(f"{key} not found in cache")
    return result[0]


@user_logged_in.connect_via(app)
def when_user_logged_in(sender, user, **extra):
    """
    Listen to this signal to write the logged in user to the cache, to support
    remember me and other flask-loging features.
    """
    wallet_cache_put(user.user_token, user.wallet.address)


@login_manager.user_loader
def load_user(user_id):
    logging.debug(f"load_user: {user_id}")
    wallet = wallet_cache_get(user_id)
    current_app.logger.debug(f"{user_id, wallet}")
    return XUMMUser(user_id, account=wallet)


@app.route("/")
def index():
    logging.debug(f"index: {current_user} {current_user.get_id()}")
    return render_template("index.html", current_app=current_app)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app.run(port=5050, debug=True)  # nosec ssl_context="adhoc",
