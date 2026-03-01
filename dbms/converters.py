from werkzeug.routing import BaseConverter
from werkzeug.exceptions import NotFound
from dbms.models import Recipe, User, Ingredient, Save


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
