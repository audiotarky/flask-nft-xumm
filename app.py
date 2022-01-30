from flask import Flask, redirect, render_template, url_for, session, request
from xrplpers.xumm.transactions import xumm_login, get_xumm_transaction
import uuid
from os import environ
import json
from utils import check_login


def create_app():
    app = Flask(__name__)
    app.config.from_object(__name__)
    app.secret_key = str(uuid.uuid1())

    from wallet import wallet as wallet_blueprint

    app.register_blueprint(wallet_blueprint)

    from trade import trade as trade_blueprint

    app.register_blueprint(trade_blueprint)

    return app


app = create_app()


environ["XUMM_CREDS_PATH"] = "xumm_creds.json"


@app.route("/", methods=["POST"])
@app.route("/")
def index():
    if request.method == "POST":
        data = json.loads(request.json)
        xumm_data = get_xumm_transaction(data["payload_uuidv4"])
        session["user_token"] = xumm_data["application"]["issued_user_token"]
        session["user_wallet"] = xumm_data["response"]["account"]
        session.modified = True
        return '{"ok": true}'
    elif session.get("user_wallet", False):
        return redirect(url_for("wallet.index"))
    else:
        r = xumm_login()
        return render_template(
            "index.html",
            qr=r["refs"]["qr_png"],
            url=r["next"]["always"],
            ws=r["refs"]["websocket_status"],
        )


@app.route("/logout")
@check_login
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)  # nosec
