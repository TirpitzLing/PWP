"""
API resources for managing ingredients.
Handles CRUD operations for ingredients.
"""

from flask import request, Response
from flask_restful import Resource
from jsonschema import validate, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType
from api.extensions import db, api, cache
from database.dbcreation import Ingredient


class IngredientCollection(Resource):
    """Resource for managing a collection of ingredients."""

    # TODO filtering by attributes
    @cache.cached(timeout=None, query_string=True)
    def get(self):
        """
        Retrieve a paginated list of ingredients.
        Uses limit and offset for pagination.
        """
        # get limit and offset from query string, default to limit=10, offset=0
        limit = request.args.get("limit", 10, type=int)
        offset = request.args.get("offset", 0, type=int)

        # apply pagination to query
        ingredients = Ingredient.query.limit(limit).offset(offset).all()
        return [i.serialize() for i in ingredients]

    def post(self):
        """
        Create a new ingredient in the database.
        Invalidates cache upon successful creation.
        """
        # add a new ingredient to the database
        if not request.json:
            raise UnsupportedMediaType(
                description="Request payload must be JSON."
            )

        try:
            validate(request.json, Ingredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        ingredient = Ingredient()
        ingredient.deserialize(request.json)

        db.session.add(ingredient)
        db.session.commit()

        cache.clear()

        return Response(
            status=201,
            headers={
                "Location": api.url_for(IngredientItem, ingredient=ingredient)
            },
        )


class IngredientItem(Resource):
    """Resource for managing a specific ingredient item."""

    @cache.cached(timeout=None)
    def get(self, ingredient):
        """
        Retrieve details of a specific ingredient.
        """
        # return details of a specific ingredient
        return ingredient.serialize()

    def put(self, ingredient):
        """
        Update a specific ingredient's details.
        Invalidates cache upon successful update.
        """
        # update ingredient details
        if not request.json:
            raise UnsupportedMediaType(
                description="Request payload must be JSON."
            )

        try:
            validate(request.json, Ingredient.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        ingredient.deserialize(request.json)
        db.session.commit()

        cache.clear()

        return Response(status=204)
