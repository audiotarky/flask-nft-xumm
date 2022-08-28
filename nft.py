from flask import Blueprint, current_app

from flask_login import login_required, current_user

from decorators import nft_required


nft = Blueprint("nft", __name__)


@nft.route("/<name>")
@login_required
@nft_required
def index(name):
    current_app.logger.debug(f"Serving an NFT from {current_user}")
    return f"This am an NFT called {name} dawg! {current_user.is_authenticated}"
