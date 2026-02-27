from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import NotFound, Conflict, BadRequest, UnsupportedMediaType
from api.extensions import db, api, cache
from database.dbcreation import Recipe

class RecipeCollection(Resource):

    @cache.cached(timeout=None)
    def get(self):
        recipes = Recipe.query.all()
        return [r.serialize() for r in recipes]

    def post(self):
        if not request.json:
            raise UnsupportedMediaType()

        try:
            validate(request.json, Recipe.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        recipe = Recipe()
        recipe.deserialize(request.json)

        try:
            db.session.add(recipe)
            db.session.commit()
        except IntegrityError:
            raise Conflict(description="Recipe already exists.")

        return Response(status=201, headers={
            "Location": api.url_for(RecipeItem, recipe=recipe)
        })


class RecipeItem(Resource):

    @cache.cached(timeout=None)
    def get(self, recipe):
        return recipe.serialize()

    def put(self, recipe):
        if not request.json:
            raise UnsupportedMediaType()

        validate(request.json, Recipe.json_schema())
        recipe.deserialize(request.json)
        db.session.commit()

        return Response(status=204)

    def delete(self, recipe):
        db.session.delete(recipe)
        db.session.commit()
        return Response(status=204)


