import json
import secrets
from flask import Response, request
from flask_restful import Resource
from werkzeug.exceptions import BadRequest, Unauthorized, UnsupportedMediaType
from werkzeug.security import check_password_hash

from dbms.auth import api_key_required
from dbms.extensions import db
from dbms.models import User

class Token(Resource):
    """Resource for managing authentication tokens (login/logout)."""

    def post(self):
        """
        Login: Submit email and pwd, verify, and create a new Token.
        """
        if not request.json:
            raise UnsupportedMediaType(description="Request payload must be JSON.")

        email = request.json.get("email")
        pwd = request.json.get("pwd")

        if not email or not pwd:
            raise BadRequest(description="Missing email or password.")

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.pwd, pwd):
            raise Unauthorized(description="Invalid email or password.")

        # Generate a new token
        raw_token = secrets.token_hex(32)
        user.api_key = User.hash_key(raw_token)
        db.session.commit()

        # Return the new token and username
        response_data = {
            "token": raw_token,
            "username": user.username,
            "email": user.email,
            "id": user.id
        }
        
        return Response(
            json.dumps(response_data),
            status=201,
            mimetype="application/json",
        )

    @api_key_required
    def delete(self):
        """
        Logout: Destroy the current Token.
        """
        user = request.current_user
        
        # Invalidate the current token by generating a new random one
        # Since api_key is nullable=False, we can't set it to None.
        new_token = secrets.token_hex(32)
        user.api_key = User.hash_key(new_token)
        db.session.commit()

        return Response(status=204)
