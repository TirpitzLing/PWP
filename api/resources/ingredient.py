from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType
from api.extensions import db, api, cache
from database.dbcreation import Ingredient


class IngredientCollection(Resource):

    @cache.cached(timeout=None)
    def get(self):
        # return all available ingredients
        ingredients = Ingredient.query.all()
        return [i.serialize() for i in ingredients]

    def post(self):
        # add a new ingredient to the database
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, Ingredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        ingredient = Ingredient()
        ingredient.deserialize(request.json)

        db.session.add(ingredient)
        db.session.commit()

        return Response(status=201, headers={"Location": api.url_for(IngredientItem, ingredient=ingredient)})


class IngredientItem(Resource):

    @cache.cached(timeout=None)
    def get(self, ingredient):
        # return details of a specific ingredient
        return ingredient.serialize()

    def put(self, ingredient):
        # update ingredient details
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, Ingredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        ingredient.deserialize(request.json)
        db.session.commit()

        return Response(status=204)
