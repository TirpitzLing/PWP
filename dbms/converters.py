"""
This module defines custom URL converters for the Flask application.
"""

from werkzeug.routing import BaseConverter
from werkzeug.exceptions import NotFound
from dbms.models import Recipe, User, Ingredient, Save


class RecipeConverter(BaseConverter):
    """URL converter for Recipe model."""

    def to_python(self, value):
        """Convert URL part to a Recipe object."""
        db_recipe = Recipe.query.filter_by(id=value).first()
        if db_recipe is None:
            raise NotFound(f"Recipe with id {value} not found.")
        return db_recipe

    def to_url(self, value):
        """Convert a Recipe object to its URL part."""
        return str(value.id)


class UserConverter(BaseConverter):
    """URL converter for User model."""

    def to_python(self, value):
        """Convert URL part to a User object."""
        db_user = User.query.filter_by(id=value).first()
        if db_user is None:
            raise NotFound(f"User with id {value} not found.")
        return db_user

    def to_url(self, value):
        """Convert a User object to its URL part."""
        return str(value.id)


class IngredientConverter(BaseConverter):
    """URL converter for Ingredient model."""

    def to_python(self, value):
        """Convert URL part to an Ingredient object."""
        db_ingredient = Ingredient.query.filter_by(id=value).first()
        if db_ingredient is None:
            raise NotFound(f"Ingredient with id {value} not found.")
        return db_ingredient

    def to_url(self, value):
        """Convert an Ingredient object to its URL part."""
        return str(value.id)


class SaveConverter(BaseConverter):
    """URL converter for Save model."""

    def to_python(self, value):
        """Convert URL part to a Save object."""
        try:
            user_id_str, recipe_id_str = value.split("-")
            user_id = int(user_id_str)
            recipe_id = int(recipe_id_str)
        except ValueError as exc:
            raise NotFound(f"Invalid save id format: {value}") from exc

        db_save = Save.query.filter_by(
            user_id=user_id, recipe_id=recipe_id
        ).first()
        if db_save is None:
            raise NotFound(f"Save with id {value} not found.")
        return db_save

    def to_url(self, value):
        """Convert a Save object to its URL part."""
        return f"{value.user_id}-{value.recipe_id}"
