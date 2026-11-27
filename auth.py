"""
HTTP Basic Auth for the whole Flask server behind the Dash app.

Credentials come from DASH_USER and DASH_PASSWORD (.env). The app refuses to
start if either is missing, so it is never served without a password by accident.
"""

import hmac
import os

from dotenv import load_dotenv
from flask import Flask, Response, request

load_dotenv()


def init_basic_auth(server: Flask) -> None:
    user = os.getenv("DASH_USER")
    password = os.getenv("DASH_PASSWORD")
    if not user or not password:
        raise RuntimeError(
            "DASH_USER and DASH_PASSWORD must be set (see .env.example)."
        )

    expected_user = user.encode()
    expected_password = password.encode()

    @server.before_request
    def _require_auth():
        auth = request.authorization
        if auth and auth.type == "basic":
            # compare_digest avoids leaking information through timing
            user_ok = hmac.compare_digest((auth.username or "").encode(), expected_user)
            password_ok = hmac.compare_digest((auth.password or "").encode(), expected_password)
            if user_ok and password_ok:
                return None
        return Response(
            "Authentication required",
            401,
            {"WWW-Authenticate": 'Basic realm="Finance Dashboard", charset="UTF-8"'},
        )
