"""
This module defines the API blueprint and registers the API resources.
"""

from flask import Blueprint
from flask_restful import Api
from dbms.resources.recipe import RecipeCollection, RecipeItem, RecipeNutrition
from dbms.resources.ingredient import IngredientCollection, IngredientItem
from dbms.resources.report import (
    Report,
    ReportDownload,
)
from dbms.resources.user import UserCollection, UserItem, UserRecipeCollection
from dbms.resources.recipe_ingredient import (
    RecipeIngredientCollection,
    RecipeIngredientItem,
)
from dbms.resources.save import SaveCollection, SaveItem
from dbms.resources.token import Token


api_bp = Blueprint("api", __name__, url_prefix="/api")
api = Api(api_bp)


# register routes
api.add_resource(RecipeCollection, "/recipes/")
api.add_resource(RecipeItem, "/recipes/<recipe:recipe>/")
api.add_resource(RecipeNutrition, "/recipes/<recipe:recipe>/nutrition/")

api.add_resource(
    RecipeIngredientCollection, "/recipes/<recipe:recipe>/ingredients/"
)
api.add_resource(
    RecipeIngredientItem,
    "/recipes/<recipe:recipe>/ingredients/<ingredient:ingredient>/",
)

api.add_resource(UserCollection, "/users/")
api.add_resource(UserItem, "/users/<user:user>/")
api.add_resource(UserRecipeCollection, "/users/<user:user>/recipes/")
api.add_resource(Report, "/users/<user:user>/reports/")
api.add_resource(
    ReportDownload, "/users/<user:user>/reports/<int:report_job_id>/download/"
)

api.add_resource(SaveCollection, "/users/<user:user>/saves/")
api.add_resource(SaveItem, "/users/<user:user>/saves/<recipe:recipe>/")

api.add_resource(Token, "/tokens/")

api.add_resource(IngredientCollection, "/ingredients/")
api.add_resource(IngredientItem, "/ingredients/<ingredient:ingredient>/")
