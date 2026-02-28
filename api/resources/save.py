"""
API resources for managing saved recipes.
Handles bookmarking recipes for users and removing them from saved collections.
"""

from datetime import datetime
from flask import request, Response
from flask_restful import Resource
from werkzeug.exceptions import BadRequest, Conflict
from database.dbcreation import Recipe, Save
from api.extensions import db, api


class SaveCollection(Resource):
    """Resource for managing a user's collection of saved recipes."""

    def get(self, user):
        """
        Retrieve a list of all saved recipes for a specific user.
        """
        # list all saved recipes for this user
        return [s.serialize() for s in user.saved_recipes]

    def post(self, user):
        """
        Save a specific recipe to the user's collection.
        """
        # save a recipe for the user
        recipe_id = request.json.get("recipe_id")
        if not recipe_id:
            raise BadRequest(description="Missing recipe_id in the request payload.")

        recipe = Recipe.query.get_or_404(recipe_id)

        existing = Save.query.filter_by(user_id=user.id, recipe_id=recipe.id).first()

        if existing:
            raise Conflict(description="Recipe already saved by this user")

        new_save = Save(user_id=user.id, recipe_id=recipe.id, created_at=datetime.utcnow())
        db.session.add(new_save)
        db.session.commit()

        # successfully created
        return Response(status=201, headers={"Location": api.url_for(SaveItem, user=user, recipe=recipe)})


class SaveItem(Resource):
    """Resource for managing a specific saved recipe entry."""

    def delete(self, user, recipe):
        """
        Remove a specific saved recipe from the user's collection.
        """
        # remove a saved recipe
        existing = Save.query.filter_by(user_id=user.id, recipe_id=recipe.id).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
        return Response(status=204)
