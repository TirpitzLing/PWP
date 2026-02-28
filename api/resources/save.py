from datetime import datetime
from flask import request, Response
from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from database.dbcreation import Recipe, Save
from api.extensions import db, api


class SaveCollection(Resource):

    def get(self, user):
        # list all saved recipes for this user
        return [s.serialize() for s in user.saved_recipes]

    def post(self, user):
        # save a recipe for the user
        recipe_id = request.json.get("recipe_id")
        if not recipe_id:
            raise BadRequest(description="missing recipe_id")

        recipe = Recipe.query.get_or_404(recipe_id)

        existing = Save.query.filter_by(user_id=user.id, recipe_id=recipe.id).first()

        if not existing:
            new_save = Save(user_id=user.id, recipe_id=recipe.id, created_at=datetime.utcnow())
            db.session.add(new_save)
            db.session.commit()
            # successfully created
            return Response(status=201, headers={"Location": api.url_for(SaveItem, user=user, recipe=recipe)})

        # already exist, return 204
        return Response(status=204)


class SaveItem(Resource):

    def delete(self, user, recipe):
        # remove a saved recipe
        existing = Save.query.filter_by(user_id=user.id, recipe_id=recipe.id).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
        return Response(status=204)
