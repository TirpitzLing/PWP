"""
API resources for managing saved recipes.
Handles bookmarking recipes for users and removing them from saved collections.
"""

from datetime import datetime, timezone
from flask import request, Response
from flask_restful import Resource
from werkzeug.exceptions import BadRequest, Conflict, Forbidden
from database.dbcreation import Recipe, Save
from api.extensions import db, api
from api.auth import api_key_required


class SaveCollection(Resource):
    """Resource for managing a user's collection of saved recipes."""

    @api_key_required
    def get(self, user):
        """
        Retrieve a list of all saved recipes for a specific user.
        """
        if request.current_user.id != user.id:
            raise Forbidden(
                description="You can only view your own saved recipes."
            )

        # list all saved recipes for this user
        return [s.serialize() for s in user.saved_recipes]

    @api_key_required
    def post(self, user):
        """
        Save a specific recipe to the user's collection.
        """
        if request.current_user.id != user.id:
            raise Forbidden(
                description="You can only save recipes to your own account."
            )

        # save a recipe for the user
        recipe_id = request.json.get("recipe_id")
        if not recipe_id:
            raise BadRequest(
                description="Missing recipe_id in the request payload."
            )

        recipe = Recipe.query.get_or_404(recipe_id)

        existing = Save.query.filter_by(
            user_id=user.id, recipe_id=recipe.id
        ).first()

        if existing:
            raise Conflict(description="Recipe already saved by this user")

        new_save = Save(
            user_id=user.id,
            recipe_id=recipe.id,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(new_save)
        db.session.commit()

        # successfully created
        return Response(
            status=201,
            headers={
                "Location": api.url_for(SaveItem, user=user, recipe=recipe)
            },
        )


class SaveItem(Resource):
    """Resource for managing a specific saved recipe entry."""

    @api_key_required
    def delete(self, user, recipe):
        """
        Remove a specific saved recipe from the user's collection.
        """
        if request.current_user.id != user.id:
            raise Forbidden(
                description="You can only remove recipes from your own account"
            )

        # remove a saved recipe
        existing = Save.query.filter_by(
            user_id=user.id, recipe_id=recipe.id
        ).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
        return Response(status=204)
