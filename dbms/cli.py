"""CLI commands for the DBMS application."""

from datetime import datetime, timezone

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from dbms.extensions import db
from dbms.models import User, Ingredient, Recipe, RecipeIngredient


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    db.create_all()
    click.echo("Initialized the database.")


@click.command("populate-db")
@with_appcontext
def populate_db_command():
    """Populate the database with initial test data."""
    # check if have data already
    has_user = User.query.first()
    has_ingredient = Ingredient.query.first()
    has_recipe = Recipe.query.first()

    if has_user and has_ingredient and has_recipe:
        click.echo("Database already populated. Skipping...")
        return

    # create admin user, print api key
    test_key = "admin-secret-key"
    admin = User(
        username="admin",
        email="admin@test.com",
        pwd=generate_password_hash("admin123"),
        created_at=datetime.now(timezone.utc),
        api_key=User.hash_key(test_key),
    )
    db.session.add(admin)
    db.session.commit()  # commit to get id

    # create some ingredient
    ing1 = Ingredient(
        name="Tomato", calories=18.0, carbs=3.9, protein=0.9, fat=0.2
    )
    ing2 = Ingredient(
        name="Egg", calories=155.0, carbs=1.1, protein=13.0, fat=11.0
    )
    ing3 = Ingredient(
        name="Salt", calories=0.0, carbs=0.0, protein=0.0, fat=0.0
    )
    db.session.add_all([ing1, ing2, ing3])
    db.session.commit()

    # create a test recipe
    recipe = Recipe(
        title="Tomato Egg Stir-fry",
        procedure="1. Chop tomatoes. 2. Beat eggs. 3. Fry together with salt.",
        servings=2,
        cuisine_type="Chinese",
        img_url="https://images.getrecipekit.com/20231103000214-andy-20cooks-20-20tomato-20egg-20stir-fry.jpg",
        created_at=datetime.now(timezone.utc),
        created_by=admin.id,
    )
    db.session.add(recipe)
    db.session.commit()

    # add ing to recipe
    db.session.add_all(
        [
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ing1.id,
                amount=200,
                unit="g",
            ),
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ing2.id,
                amount=100,
                unit="g",
            ),
            RecipeIngredient(
                recipe_id=recipe.id, ingredient_id=ing3.id, amount=5, unit="g"
            ),
        ]
    )
    db.session.commit()

    from dbms.extensions import cache

    cache.clear()

    click.echo("Database populated successfully!")
    click.echo("[*] Admin User created: 'admin'")
    click.echo(
        f"[*] Admin API Key: '{test_key}' (Use this in 'dbms-api-key' header)"
    )
