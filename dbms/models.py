"""
Database models for the Daily Bowl Management System.

This module defines the SQLAlchemy models for User, Ingredient, Recipe,
RecipeIngredient, and Save, along with their serialization and validation logic.
it also includes CLI commands for database initialization and population.
"""

import secrets
import hashlib
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash

from dbms.extensions import db


class User(db.Model):
    """Represents a user of the application."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, unique=True)
    pwd = db.Column(db.String(128), nullable=False)
    email = db.Column(
        db.String(128),
        nullable=False,
        unique=True,
    )
    created_at = db.Column(db.DateTime, nullable=False)

    # diet = db.Column(
    #     db.String(32),
    #     CheckConstraint(
    #         "diet IN ('omnivore','vegan','vegetarian','pescatarian',"
    #         "'ketogenic','paleo','low_carb','halal','gluten_free','dairy_free')"
    #     )
    # )

    allergies = db.Column(db.Text, nullable=True)

    recipes = db.relationship(
        "Recipe", back_populates="creator", cascade="all, delete-orphan"
    )
    saved_recipes = db.relationship(
        "Save", back_populates="user", cascade="all, delete-orphan"
    )
    # ingredient_preferences = db.relationship(
    #     "UserIngredientPreference", back_populates="user"
    # )
    # allergies = db.relationship("UserAllergy", back_populates="user")

    # The API key implementation is based on lovelace
    # material on API key authentication.
    api_key = db.Column(db.String(128), unique=True, nullable=False)

    def serialize(self):
        """Serialize the User object to a dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "allergies": self.allergies,
            # "api_key": self.api_key, # deleted for security
        }

    @staticmethod
    def hash_key(token):
        # ref: This method for hashing the API key is based on lovelace material
        """Hash the given API key token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def deserialize(self, doc):
        """
        Deserialize data from a dictionary to the User object.

        Returns the raw API token if a new one is generated.
        """
        # mandatory
        self.username = doc["username"]
        self.email = doc["email"]
        # this hash uses salting to avoid Credential Stuffing Attack
        # use PBKDF2 to slow down calculation
        self.pwd = generate_password_hash(doc["pwd"])

        if "created_at" in doc:
            self.created_at = datetime.fromisoformat(doc["created_at"])

        # self.created_at = (
        #     datetime.fromisoformat(doc["created_at"])
        #     if doc.get("created_at")
        #     else None
        # )

        # optional
        self.allergies = doc.get("allergies")

        # The logic to generate a strong token using `secrets` module
        # is based on lovelace material.
        # generate api_key, store hash but return plain
        if not self.api_key:
            raw_token = secrets.token_hex(32)
            self.api_key = self.hash_key(raw_token)
            return raw_token  # return plaintext just to response
        return None

    @staticmethod
    def json_schema():
        """Return the JSON schema for User validation."""
        return {
            "type": "object",
            "required": [
                "username",
                "email",
                "pwd",
            ],
            "properties": {
                "id": {"type": "integer"},
                "username": {"type": "string"},
                "email": {"type": "string"},
                "pwd": {"type": "string"},
                "created_at": {
                    "type": ["string", "null"],
                    "format": "date-time",
                },
                "allergies": {"type": ["string", "null"]},
            },
        }


class Ingredient(db.Model):
    """Represents a single cooking ingredient."""

    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    img_url = db.Column(db.String(255))
    allergy = db.Column(db.Text)

    # nutrition info
    calories = db.Column(db.Float)
    carbs = db.Column(db.Float)
    protein = db.Column(db.Float)
    fat = db.Column(db.Float)

    recipe_links = db.relationship(
        "RecipeIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )

    def serialize(self):
        """Serialize the Ingredient object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "img_url": self.img_url,
            "allergy": self.allergy,
            "calories": self.calories,
            "carbs": self.carbs,
            "protein": self.protein,
            "fat": self.fat,
        }

    def deserialize(self, doc):
        """Deserialize data from a dictionary to the Ingredient object."""
        self.name = doc["name"]
        self.img_url = doc.get("img_url")
        self.allergy = doc.get("allergy")
        self.calories = doc.get("calories")
        self.carbs = doc.get("carbs")
        self.protein = doc.get("protein")
        self.fat = doc.get("fat")

    @staticmethod
    def json_schema():
        """Return the JSON schema for Ingredient validation."""
        schema = {
            "type": "object",
            "required": ["name"],
        }

        props = schema["properties"] = {}

        props["id"] = {"type": "integer"}
        props["name"] = {"type": "string"}

        props["img_url"] = {"type": ["string", "null"]}
        props["allergy"] = {"type": ["string", "null"]}

        props["calories"] = {"type": ["number", "null"]}
        props["carbs"] = {"type": ["number", "null"]}
        props["protein"] = {"type": ["number", "null"]}
        props["fat"] = {"type": ["number", "null"]}

        return schema


class Recipe(db.Model):
    """Represents a cooking recipe."""

    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    procedure = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)

    servings = db.Column(db.Integer)
    cuisine_type = db.Column(db.String(64))
    cooking_methods = db.Column(db.Text)

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    creator = db.relationship("User", back_populates="recipes")
    ingredients = db.relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
    saved_by = db.relationship(
        "Save", back_populates="recipe", cascade="all, delete-orphan"
    )
    # cooking_methods = db.relationship(
    #     "RecipeCookingMethod", back_populates="recipe"
    # )

    def serialize(self):
        """Serialize the Recipe object to a dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "procedure": self.procedure,
            "created_at": self.created_at.isoformat(),
            "servings": self.servings,
            "cuisine_type": self.cuisine_type,
            "cooking_methods": self.cooking_methods,
            "created_by": self.created_by,
        }

    def deserialize(self, doc):
        """Deserialize data from a dictionary to the Recipe object."""
        self.title = doc["title"]
        self.procedure = doc.get("procedure")
        self.servings = doc.get("servings")
        self.cuisine_type = doc.get("cuisine_type")
        self.cooking_methods = doc.get("cooking_methods")

        if "created_at" in doc:
            self.created_at = datetime.fromisoformat(doc["created_at"])

    @staticmethod
    def json_schema():
        """Return the JSON schema for Recipe validation."""
        schema = {
            "type": "object",
            "required": ["title"],
        }

        props = schema["properties"] = {}

        props["id"] = {"type": "integer"}
        props["title"] = {"type": "string"}
        props["procedure"] = {"type": ["string", "null"]}

        props["created_at"] = {
            "type": "string",
            "format": "date-time",
        }

        props["servings"] = {"type": ["integer", "null"]}
        props["cuisine_type"] = {"type": ["string", "null"]}
        props["cooking_methods"] = {"type": ["string", "null"]}
        props["created_by"] = {"type": "integer"}

        return schema


class RecipeIngredient(db.Model):
    """Association object between Recipe and Ingredient."""

    __tablename__ = "recipe_ingredients"

    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ingredient_id = db.Column(
        db.Integer,
        db.ForeignKey("ingredients.id", ondelete="CASCADE"),
        primary_key=True,
    )

    amount = db.Column(db.Float)  # numeral
    unit = db.Column(db.String(16))  # g, ml

    recipe = db.relationship("Recipe", back_populates="ingredients")
    ingredient = db.relationship(
        "Ingredient",
        back_populates="recipe_links",
    )

    def serialize(self):
        """Serialize the RecipeIngredient object to a dictionary."""
        return {
            "recipe_id": self.recipe_id,
            "ingredient_id": self.ingredient_id,
            "amount": self.amount,
            "unit": self.unit,
        }

    def deserialize(self, doc):
        """Deserialize data from a dictionary to the RecipeIngredient object."""
        self.amount = doc.get("amount")
        self.unit = doc.get("unit")

    @staticmethod
    def json_schema():
        """Return the JSON schema for RecipeIngredient validation."""
        schema = {
            "type": "object",
            "required": [],
        }

        props = schema["properties"] = {}

        props["recipe_id"] = {"type": "integer"}
        props["ingredient_id"] = {"type": "integer"}
        props["amount"] = {"type": ["number", "null"]}
        props["unit"] = {"type": ["string", "null"]}

        return schema


class Save(db.Model):
    """Represents a user saving a recipe (a 'like' or 'favorite')."""

    __tablename__ = "save"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User", back_populates="saved_recipes")
    recipe = db.relationship("Recipe", back_populates="saved_by")

    def serialize(self):
        """Serialize the Save object to a dictionary."""
        return {
            "user_id": self.user_id,
            "recipe_id": self.recipe_id,
            "created_at": self.created_at.isoformat(),
        }

    def deserialize(self, doc):
        """Deserialize data from a dictionary to the Save object."""
        if "created_at" in doc:
            self.created_at = datetime.fromisoformat(doc["created_at"])

    @staticmethod
    def json_schema():
        """Return the JSON schema for Save validation."""
        schema = {
            "type": "object",
            "required": [],
        }

        props = schema["properties"] = {}

        props["user_id"] = {"type": "integer"}
        props["recipe_id"] = {"type": "integer"}

        props["created_at"] = {
            "type": "string",
            "format": "date-time",
        }

        return schema
