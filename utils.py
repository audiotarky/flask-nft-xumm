from functools import wraps

from flask import redirect, session, url_for


def check_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        the_wallet = session.get("user_wallet", False)
        if not the_wallet:
            return redirect(url_for("index"))

        return f(*args, **kwargs)

    return decorated_function
