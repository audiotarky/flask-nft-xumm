import time
from functools import lru_cache, wraps

from flask import request
from flask_login import current_user
from xrpl.utils import str_to_hex


class NFTAccessDenied(Exception):
    status_code = 403

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv


def nft_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        the_url = request.url
        hexed_url = str_to_hex(the_url).upper()

        if hexed_url not in current_user.wallet.nft_uris:
            raise NFTAccessDenied("You do not own the NFT at this URL")

        return f(*args, **kwargs)

    return decorated_function


def time_cache(max_age, maxsize=128, typed=False):
    """
    https://stackoverflow.com/a/63674816
    Least-recently-used cache decorator with time-based cache invalidation.

    Args:
        max_age: Time to live for cached results (in seconds).
        maxsize: Maximum cache size (see `functools.lru_cache`).
        typed: Cache on distinct input types (see `functools.lru_cache`).
    """

    def _decorator(fn):
        @lru_cache(maxsize=maxsize, typed=typed)
        def _new(*args, __time_salt, **kwargs):
            return fn(*args, **kwargs)

        @wraps(fn)
        def _wrapped(*args, **kwargs):
            return _new(*args, **kwargs, __time_salt=int(time.time() / max_age))

        return _wrapped

    return _decorator
