from flask import Blueprint, current_app
from flask_login import current_user, login_required

from flask_nft_xumm.decorators import nft_required

nft = Blueprint("nft", __name__, template_folder="templates")


@nft.route("/<name>")
@login_required
@nft_required
def index(name):
    current_app.logger.debug(f"Serving an NFT from {current_user}")
    return f"This am an NFT called {name} dawg! {current_user.is_authenticated}"
