"""
Authentication module for the API.
Provides decorators to secure API endpoints using HTTP Basic Auth.
"""

from functools import wraps
from flask import request
from werkzeug.exceptions import Unauthorized
from werkzeug.security import check_password_hash
from database.dbcreation import User


def basic_auth_required(f):
    """
    Decorator to require HTTP Basic Authentication for an API endpoint.
    Checks the 'Authorization' header and verifies credentials against the database.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        # Extract authorization data from the request header
        auth = request.authorization

        # Check if auth details are provided
        if not auth or not auth.username or not auth.password:
            raise Unauthorized(description="Authentication required. Please provide valid username and password.")

        # Verify user exists in the database
        user = User.query.filter_by(username=auth.username).first()

        # Check if user exists and password is correct
        if not user or not check_password_hash(user.pwd, auth.password):
            raise Unauthorized(description="Invalid username or password.")

        # Inject the authenticated user into the request context
        request.current_user = user

        return f(*args, **kwargs)

    return decorated
