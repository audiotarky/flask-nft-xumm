import json

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import UserMixin, current_user, login_user
from xrplpers.xumm.transactions import get_xumm_transaction, xumm_login

from utils import XUMMWalletProxy, is_safe_url

login = Blueprint("xumm", __name__)


wallet_cache = {}


class XUMMUser(UserMixin):
    def __init__(self, login, **kwargs):
        self.user_token = login
        self.wallet = XUMMWalletProxy(kwargs.get("account", wallet_cache[login]))

    def get_id(self):
        current_app.logger.debug(f"XUMMUser.get_id: {self.user_token}")
        return self.user_token


@login.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = json.loads(request.json)
        xumm_data = get_xumm_transaction(data["payload_uuidv4"])
        user_id = xumm_data["application"]["issued_user_token"]
        wallet_cache[user_id] = xumm_data["response"]["account"]
        user = XUMMUser(
            user_id,
            **xumm_data["response"],
        )

        login_user(user, remember=False)

        if current_user.is_authenticated:

            next = request.args.get("next")
            if not is_safe_url(next):
                return abort(400)

            return redirect(next or url_for("index"))
    r = xumm_login()
    return render_template(
        "login.html",
        qr=r["refs"]["qr_png"],
        url=r["next"]["always"],
        ws=r["refs"]["websocket_status"],
    )
