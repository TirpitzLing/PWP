from datetime import datetime
from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Conflict, BadRequest, UnsupportedMediaType
from api.extensions import db, api
from database.dbcreation import User


class UserCollection(Resource):

    def get(self):
        # get all registered users
        users = User.query.all()
        return [u.serialize() for u in users]

    def post(self):
        # register a new user
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, User.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        user = User()
        user.deserialize(request.json)

        # set creation time if not provided
        if not user.created_at:
            user.created_at = datetime.utcnow()

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            raise Conflict(description="username or email already exists")

        return Response(status=201, headers={"Location": api.url_for(UserItem, user=user)})


class UserItem(Resource):

    def get(self, user):
        # retrieve user profile
        return user.serialize()

    def put(self, user):
        # update user information including allergies
        if not request.json:
            raise UnsupportedMediaType

        validate(request.json, User.json_schema())
        user.deserialize(request.json)
        db.session.commit()

        return Response(status=204)

    def delete(self, user):
        # delete a user account
        db.session.delete(user)
        db.session.commit()
        return Response(status=204)


class UserRecipeCollection(Resource):

    def get(self, user):
        # get all recipes created by this user
        return [r.serialize() for r in user.recipes]
