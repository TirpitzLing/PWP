import os
from api.resources.recipeIngredient import (
    RecipeIngredientCollection,
    RecipeIngredientItem,
)
from api.resources.save import SaveCollection, SaveItem
from api.resources.recipe import RecipeCollection, RecipeItem, RecipeNutrition
from api.resources.ingredient import IngredientCollection, IngredientItem
from api.resources.user import UserCollection, UserItem, UserRecipeCollection
from database.dbcreation import (
    User,
    Ingredient,
    Recipe,
    Save,
)
from flask import Flask, jsonify
from sqlalchemy.engine import Engine
from sqlalchemy import event
from werkzeug.routing import BaseConverter
from werkzeug.exceptions import (
    NotFound,
    HTTPException,
)
from api.extensions import db, api, cache


db_path = os.path.join(
    os.path.dirname(__file__), "..", "database", "instance", "dbms.db"
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["CACHE_TYPE"] = "FileSystemCache"
app.config["CACHE_DIR"] = os.path.join(app.instance_path, "cache")

db.init_app(app)
api.init_app(app)
cache.init_app(app)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class RecipeConverter(BaseConverter):

    def to_python(self, recipe_id):
        db_recipe = Recipe.query.filter_by(id=recipe_id).first()
        if db_recipe is None:
            raise NotFound(f"Recipe with id {recipe_id} not found.")
        return db_recipe

    def to_url(self, db_recipe):
        return str(db_recipe.id)


class UserConverter(BaseConverter):

    def to_python(self, user_id):
        db_user = User.query.filter_by(id=user_id).first()
        if db_user is None:
            raise NotFound(f"User with id {user_id} not found.")
        return db_user

    def to_url(self, db_user):
        return str(db_user.id)


class IngredientConverter(BaseConverter):

    def to_python(self, ingredient_id):
        db_ingredient = Ingredient.query.filter_by(id=ingredient_id).first()
        if db_ingredient is None:
            raise NotFound(f"Ingredient with id {ingredient_id} not found.")
        return db_ingredient

    def to_url(self, db_ingredient):
        return str(db_ingredient.id)


class SaveConverter(BaseConverter):

    def to_python(self, save_id):
        try:
            # user_id & recipe_id, primary key
            user_id_str, recipe_id_str = save_id.split("-")
            user_id = int(user_id_str)
            recipe_id = int(recipe_id_str)
        except ValueError:
            raise NotFound(f"Invalid save id format: {save_id}")

        db_save = Save.query.filter_by(
            user_id=user_id, recipe_id=recipe_id
        ).first()
        if db_save is None:
            raise NotFound(f"Save with id {save_id} not found.")
        return db_save

    def to_url(self, db_save):
        return f"{db_save.user_id}-{db_save.recipe_id}"


app.url_map.converters["recipe"] = RecipeConverter
app.url_map.converters["user"] = UserConverter
app.url_map.converters["ingredient"] = IngredientConverter
app.url_map.converters["save"] = SaveConverter

# register recipe routes
api.add_resource(RecipeCollection, "/api/recipes/")
api.add_resource(RecipeItem, "/api/recipes/<recipe:recipe>/")
api.add_resource(RecipeNutrition, "/api/recipes/<recipe:recipe>/nutrition/")
api.add_resource(
    RecipeIngredientCollection, "/api/recipes/<recipe:recipe>/ingredients/"
)
api.add_resource(
    RecipeIngredientItem,
    "/api/recipes/<recipe:recipe>/ingredients/<ingredient:ingredient>/",
)

# register user routes
api.add_resource(UserCollection, "/api/users/")
api.add_resource(UserItem, "/api/users/<user:user>/")
api.add_resource(UserRecipeCollection, "/api/users/<user:user>/recipes/")
api.add_resource(SaveCollection, "/api/users/<user:user>/saves/")
api.add_resource(SaveItem, "/api/users/<user:user>/saves/<recipe:recipe>/")

# register ingredient routes
api.add_resource(IngredientCollection, "/api/ingredients/")
api.add_resource(IngredientItem, "/api/ingredients/<ingredient:ingredient>/")


# so raise BadRequest returns json not html
@app.errorhandler(HTTPException)
def handle_exception(e):
    return (
        jsonify(
            {
                "code": e.code,
                "name": e.name,
                "description": e.description,
            }
        ),
        e.code,
    )
