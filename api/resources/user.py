"""
API resources for managing users.
Handles user registration, profile updates, account deletion, and fetching user recipes.
"""

from datetime import datetime, timezone
from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Conflict, BadRequest, UnsupportedMediaType, Forbidden
from api.extensions import db, api
from database.dbcreation import User
from api.auth import api_key_required
import json


class UserCollection(Resource):
    """Resource for managing a collection of users."""

    # TODO filtering by attributes
    # frequent user registration, no cache
    def get(self):
        """
        Retrieve a paginated list of all users.
        Uses limit and offset for pagination.
        """
        # get limit and offset from query string
        limit = request.args.get("limit", 10, type=int)
        offset = request.args.get("offset", 0, type=int)

        # apply pagination
        users = User.query.limit(limit).offset(offset).all()
        return [u.serialize() for u in users]

    def post(self):
        """
        Register a new user in the system.
        """
        # register a new user
        if not request.json:
            raise UnsupportedMediaType(description="Request payload must be JSON.")

        try:
            validate(request.json, User.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        user = User()
        # get plain api key, first time register, generate a key and response with the key
        # otherwise, return None
        raw_api_key = user.deserialize(request.json)

        # set creation time if not provided
        if not user.created_at:
            user.created_at = datetime.now(timezone.utc)

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            raise Conflict(description="Username or email already exists")

        response_data = user.serialize()
        response_data["api_key"] = raw_api_key  # return api_key only when registered

        return Response(
            json.dumps(response_data),
            status=201,
            headers={"Location": api.url_for(UserItem, user=user)},
            mimetype="application/json",
        )


class UserItem(Resource):
    """Resource for managing a specific user profile."""

    # user's private data, no cache
    def get(self, user):
        """
        Retrieve details of a specific user profile.
        """
        # retrieve user profile
        return user.serialize()

    @api_key_required
    def put(self, user):
        """
        Update user information including password, email, and allergies.
        """
        # check user api key
        if request.current_user.id != user.id:
            raise Forbidden(description="You can only update your own profile.")

        # update user information including allergies
        if not request.json:
            raise UnsupportedMediaType(description="Request payload must be JSON.")

        try:
            validate(request.json, User.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        user.deserialize(request.json)
        db.session.commit()

        return Response(status=204)

    @api_key_required
    def delete(self, user):
        """
        Delete a specific user account from the system.
        """
        # check user api key
        if request.current_user.id != user.id:
            raise Forbidden(description="You can only delete your own account.")

        # delete a user account
        db.session.delete(user)
        db.session.commit()
        return Response(status=204)


class UserRecipeCollection(Resource):
    """Resource for retrieving recipes created by a specific user."""

    def get(self, user):
        """
        Retrieve all recipes created by this specific user.
        """
        # get all recipes created by this user
        return [r.serialize() for r in user.recipes]
