"""
Authentication module for the API.
Provides decorators to secure API endpoints using API key Auth.
"""

from functools import wraps
from flask import request
from werkzeug.exceptions import Unauthorized
from dbms.models import User


def authenticate_user_by_key(api_key_raw: str):
    """Return the User matching *api_key_raw*, or None."""
    if not api_key_raw:
        return None
    hashed = User.hash_key(api_key_raw)
    return User.query.filter_by(api_key=hashed).first()


def api_key_required(f):
    # The decorator is based on
    # the 'require_admin' and 'require_sensor_key' decorators from lovelace
    """
    Decorator to require API Key Authentication for an API endpoint.
    Checks the 'dbms-api-key' header and verifies credentials against the
    database.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        # get api_key from request headers
        api_key_raw = request.headers.get("dbms-api-key")
        if not api_key_raw:
            raise Unauthorized(
                description="Authentication required. Please provide a valid "
                "dbms-api-key header."
            )

        # match api ket after hashing
        hashed_key = User.hash_key(api_key_raw)
        # search for the user with the api key
        user = User.query.filter_by(api_key=hashed_key).first()

        if not user:
            raise Unauthorized(description="Invalid API key.")

        # inject the authenticated user into the request context
        request.current_user = user

        return f(*args, **kwargs)

    return decorated
