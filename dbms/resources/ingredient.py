"""
API resources for managing ingredients.
Handles CRUD operations for ingredients.
"""

from flask import Response, request, url_for
from flask_restful import Resource
from jsonschema import validate, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from dbms.extensions import cache, db
from dbms.models import Ingredient
from dbms.utils import get_pagination_args


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
        limit, offset = get_pagination_args()

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
            raise BadRequest(description=str(e)) from e

        ingredient = Ingredient()
        ingredient.deserialize(request.json)

        db.session.add(ingredient)
        db.session.commit()

        cache.clear()

        return Response(
            status=201,
            headers={
                "Location": url_for(
                    "api.ingredientitem", ingredient=ingredient
                )
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
            raise BadRequest(description=str(e)) from e

        ingredient.deserialize(request.json)
        db.session.commit()

        cache.clear()

        return Response(status=204)

    def delete(self, ingredient):
        """
        Delete a specific ingredient from the database.
        Invalidates cache upon successful deletion.
        """
        db.session.delete(ingredient)
        db.session.commit()
        cache.clear()
        return Response(status=204)
