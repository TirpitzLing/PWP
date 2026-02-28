"""
API resources for managing recipe ingredients.
Handles adding, updating, and removing ingredients within a specific recipe.
"""

from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType, NotFound, Conflict, Forbidden
from api.extensions import db, api, cache
from sqlalchemy.exc import IntegrityError
from database.dbcreation import Ingredient, RecipeIngredient
from api.auth import basic_auth_required


class RecipeIngredientCollection(Resource):
    """Resource for managing a collection of ingredients for a specific recipe."""

    @cache.cached(timeout=None)
    def get(self, recipe):
        """
        Retrieve a list of all ingredients associated with a specific recipe.
        """
        # list all ingredients for a recipe
        return [i.serialize() for i in recipe.ingredients]

    @basic_auth_required
    def post(self, recipe):
        """
        Add a new ingredient to a specific recipe.
        Invalidates cache upon successful addition.
        """
        # add a new ingredient to the recipe with amount
        if recipe.created_by != request.current_user.id:
            raise Forbidden(description="You can only add ingredients to your own recipes.")

        if not request.json:
            raise UnsupportedMediaType(description="Request payload must be JSON.")

        try:
            validate(request.json, RecipeIngredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        # handle no existing ingredient error
        ingredient_id = request.json.get("ingredient_id")
        if not ingredient_id:
            raise BadRequest(description="Missing ingredient_id in the request payload.")

        ingredient = Ingredient.query.get_or_404(ingredient_id)

        assoc = RecipeIngredient(recipe=recipe, ingredient=ingredient)
        assoc.deserialize(request.json)

        # primary key: (recipe_id, ingredient_id)
        # adding an existing ingredient to a recipe may cause internal error
        # catch this and return 409
        try:
            db.session.add(assoc)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise Conflict(description="This ingredient has already been added to the recipe")

        cache.clear()

        return Response(
            status=201, headers={"Location": api.url_for(RecipeIngredientItem, recipe=recipe, ingredient=ingredient)}
        )


class RecipeIngredientItem(Resource):
    """Resource for managing a specific ingredient item within a recipe."""

    @basic_auth_required
    def put(self, recipe, ingredient):
        """
        Update the amount and unit of a specific ingredient in a recipe.
        Invalidates cache upon successful update.
        """
        if recipe.created_by != request.current_user.id:
            raise Forbidden(description="You can only update ingredients in your own recipes.")

        # update the amount and unit of an ingredient
        if not request.json:
            raise UnsupportedMediaType(description="Request payload must be JSON.")

        try:
            validate(request.json, RecipeIngredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        assoc = RecipeIngredient.query.filter_by(recipe_id=recipe.id, ingredient_id=ingredient.id).first()

        if not assoc:
            raise NotFound(description="Ingredient association not found in this recipe.")

        assoc.deserialize(request.json)
        db.session.commit()
        cache.clear()
        return Response(status=204)

    @basic_auth_required
    def delete(self, recipe, ingredient):
        """
        Remove a specific ingredient from a recipe.
        Invalidates cache upon successful deletion.
        """
        # remove an ingredient from the recipe
        if recipe.created_by != request.current_user.id:
            raise Forbidden(description="You can only delete ingredients from your own recipes.")

        assoc = RecipeIngredient.query.filter_by(recipe_id=recipe.id, ingredient_id=ingredient.id).first()

        if assoc:
            db.session.delete(assoc)
            db.session.commit()

            cache.clear()

        return Response(status=204)
