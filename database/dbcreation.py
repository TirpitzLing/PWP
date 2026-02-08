from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dbms.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, unique=True)
    pwd = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False, unique=True)
    created_at = db.Column(db.DateTime)

    # diet = db.Column(
    #     db.String(32),
    #     CheckConstraint(
    #         "diet IN ('omnivore','vegan','vegetarian','pescatarian',"
    #         "'ketogenic','paleo','low_carb','halal','gluten_free','dairy_free')"
    #     )
    # )

    allergies = db.Column(db.Text, nullable=True)

    recipes = db.relationship("Recipe", back_populates="creator")
    saved_recipes = db.relationship("Save", back_populates="user")
    # ingredient_preferences = db.relationship("UserIngredientPreference", back_populates="user")
    # allergies = db.relationship("UserAllergy", back_populates="user")


class Ingredient(db.Model):
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

    recipe_links = db.relationship("RecipeIngredient", back_populates="ingredient")



class Recipe(db.Model):
    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    procedure = db.Column(db.Text)
    created_at = db.Column(db.DateTime)

    servings = db.Column(db.Integer)
    cuisine_type = db.Column(db.String(64))
    cooking_methods = db.Column(db.Text)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)\
    
    creator = db.relationship("User", back_populates="recipes")
    ingredients = db.relationship("RecipeIngredient", back_populates="recipe")
    # cooking_methods = db.relationship("RecipeCookingMethod", back_populates="recipe")
    saved_by = db.relationship("Save", back_populates="recipe")


class RecipeIngredient(db.Model):
    __tablename__ = "recipe_ingredients"

    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("ingredients.id"), primary_key=True)

    amount = db.Column(db.Float) # numeral
    unit = db.Column(db.String(16)) # g, ml

    recipe = db.relationship("Recipe", back_populates="ingredients")
    ingredient = db.relationship("Ingredient", back_populates="recipe_links")


class Save(db.Model):
    __tablename__ = "save"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), primary_key=True)
    created_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="saved_recipes")
    recipe = db.relationship("Recipe", back_populates="saved_by")
