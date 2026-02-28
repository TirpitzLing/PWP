from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Conflict, BadRequest, UnsupportedMediaType
from api.extensions import db, api, cache
from database.dbcreation import Recipe


class RecipeCollection(Resource):

    @cache.cached(timeout=None, query_string=True)
    def get(self):
        # get limit and offset from query string
        limit = request.args.get("limit", 10, type=int)
        offset = request.args.get("offset", 0, type=int)

        # apply to query
        recipes = Recipe.query.limit(limit).offset(offset).all()
        return [r.serialize() for r in recipes]

    def post(self):
        # create a new recipe
        if not request.json:
            raise UnsupportedMediaType

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
            raise Conflict(description="recipe already exists")

        return Response(status=201, headers={"Location": api.url_for(RecipeItem, recipe=recipe)})


class RecipeItem(Resource):

    @cache.cached(timeout=None)
    def get(self, recipe):
        # get details of a specific recipe
        return recipe.serialize()

    def put(self, recipe):
        # update a recipe
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, Recipe.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        recipe.deserialize(request.json)
        db.session.commit()

        return Response(status=204)

    def delete(self, recipe):
        # delete a recipe
        db.session.delete(recipe)
        db.session.commit()
        return Response(status=204)


class RecipeNutrition(Resource):

    @cache.cached(timeout=None)
    def get(self, recipe):
        # calculate total nutrition based on ingredients
        total_calories = 0.0
        total_carbs = 0.0
        total_protein = 0.0
        total_fat = 0.0

        for assoc in recipe.ingredients:
            ingredient = assoc.ingredient
            amount = assoc.amount or 0.0

            # calculate ratio assuming base nutrition is per 100g
            ratio = amount / 100.0

            if ingredient.calories:
                total_calories += ingredient.calories * ratio
            if ingredient.carbs:
                total_carbs += ingredient.carbs * ratio
            if ingredient.protein:
                total_protein += ingredient.protein * ratio
            if ingredient.fat:
                total_fat += ingredient.fat * ratio

        return {
            "total_calories": round(total_calories, 2),
            "total_carbs": round(total_carbs, 2),
            "total_protein": round(total_protein, 2),
            "total_fat": round(total_fat, 2),
        }
