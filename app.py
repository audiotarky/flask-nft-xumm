import uuid
import logging
from flask import Flask, redirect, render_template, url_for

from flask_login import (
    LoginManager,
    login_required,
    current_user,
    logout_user,
)
from login import XUMMUser, login


def create_app():
    app = Flask(__name__)
    app.config.from_object(__name__)
    app.secret_key = str(uuid.uuid1())

    from wallet import wallet as wallet_blueprint
    from trade import trade as trade_blueprint
    from nft import nft as nft_blueprint

    app.register_blueprint(wallet_blueprint)
    app.register_blueprint(trade_blueprint)
    app.register_blueprint(login, url_prefix="/login")
    app.register_blueprint(nft_blueprint, url_prefix="/nft")

    return app


app = create_app()

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "/login"
login_manager.refresh_view = "/login"

login_manager.needs_refresh_message = "Session timed out, please re-login"
login_manager.needs_refresh_message_category = "info"

login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(user_id):
    logging.debug(f"load_user: {user_id}")
    return XUMMUser(user_id)


@app.route("/")
def index():
    logging.debug(f"index: {current_user} {current_user.get_id()}")
    return render_template("index.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app.run(port=5050, debug=True)  # nosec ssl_context="adhoc",
