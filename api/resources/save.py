from flask import request, Response
from flask_restful import Resource
from werkzeug.exceptions import NotFound, Conflict, BadRequest, UnsupportedMediaType
from database.dbcreation import Recipe, User
from api.extensions import db, api, cache

class SaveCollection(Resource):

    def get(self, user):
        return [r.serialize() for r in user.favorites]

    def post(self, user):
        recipe_id = request.json.get("recipe_id")
        recipe = Recipe.query.get_or_404(recipe_id)

        if recipe not in user.favorites:
            user.favorites.append(recipe)
            db.session.commit()

        return Response(status=201)


class SaveItem(Resource):

    def delete(self, user, recipe):
        if recipe in user.saved_recipes:
            user.saved_recipes.remove(recipe)
            db.session.commit()
        return Response(status=204)
    
