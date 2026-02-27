from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType
from api.extensions import db, api, cache
from database.dbcreation import Recipe, Ingredient

class RecipeIngredientCollection(Resource):

    @cache.cached(timeout=None)
    def get(self, recipe):
        return [i.serialize() for i in recipe.ingredients]

    def post(self, recipe):
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, Ingredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        ingredient = Ingredient()
        ingredient.deserialize(request.json)
        recipe.ingredients.append(ingredient)

        db.session.commit()

        return Response(status=201)


class RecipeIngredientItem(Resource):

    def delete(self, recipe, ingredient):
        recipe.ingredients.remove(ingredient)
        db.session.commit()
        return Response(status=204)


