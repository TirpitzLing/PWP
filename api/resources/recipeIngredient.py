from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType, NotFound
from api.extensions import db, api, cache
from database.dbcreation import Ingredient, RecipeIngredient


class RecipeIngredientCollection(Resource):

    @cache.cached(timeout=None)
    def get(self, recipe):
        # list all ingredients for a recipe
        return [i.serialize() for i in recipe.ingredients]

    def post(self, recipe):
        # add a new ingredient to the recipe with amount
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, RecipeIngredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        # handle no existing ingredient error
        ingredient_id = request.json.get("ingredient_id")
        if not ingredient_id:
            raise BadRequest(description="missing ingredient_id")

        ingredient = Ingredient.query.get_or_404(ingredient_id)

        assoc = RecipeIngredient(recipe=recipe, ingredient=ingredient)
        assoc.deserialize(request.json)

        db.session.add(assoc)
        db.session.commit()

        return Response(
            status=201, headers={"Location": api.url_for(RecipeIngredientItem, recipe=recipe, ingredient=ingredient)}
        )


class RecipeIngredientItem(Resource):

    def put(self, recipe, ingredient):
        # update the amount and unit of an ingredient
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, RecipeIngredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        assoc = RecipeIngredient.query.filter_by(recipe_id=recipe.id, ingredient_id=ingredient.id).first()

        if not assoc:
            raise NotFound

        assoc.deserialize(request.json)
        db.session.commit()
        return Response(status=204)

    def delete(self, recipe, ingredient):
        # remove an ingredient from the recipe
        assoc = RecipeIngredient.query.filter_by(recipe_id=recipe.id, ingredient_id=ingredient.id).first()

        if assoc:
            db.session.delete(assoc)
            db.session.commit()

        return Response(status=204)
