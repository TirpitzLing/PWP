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
    """Populate the database with initial test data.

    This implementation is idempotent: it ensures the Swagger examples
    (user `oulu_chef`, ingredient `Tomato`, recipe `Tomato and Egg Stir-fry`)
    exist, while also providing additional test data.
    """

    def get_or_create_user(username, email, pwd_plain, api_key_plain):
        u = User.query.filter_by(username=username).first()
        if u:
            return u
        u = User(
            username=username,
            email=email,
            pwd=generate_password_hash(pwd_plain),
            created_at=datetime.now(timezone.utc),
            api_key=User.hash_key(api_key_plain),
        )
        db.session.add(u)
        db.session.commit()
        return u

    admin = get_or_create_user(
        "admin", "admin@test.com", "admin123", "admin-secret-key"
    )
    get_or_create_user("alice", "alice@test.com", "alice123", "alice-key")
    get_or_create_user("bob", "bob@test.com", "bob123", "bob-key")
    oulu_chef = get_or_create_user(
        "oulu_chef",
        "chef@student.oulu.fi",
        "SecurePassword123!",
        "dbms-test-key-7a8b9c",
    )

    # Ingredients to ensure
    ingredients = [
        Ingredient(
            name="Tomato", calories=18.0, carbs=3.9, protein=0.9, fat=0.2
        ),
        Ingredient(
            name="Egg", calories=155.0, carbs=1.1, protein=13.0, fat=11.0
        ),
        Ingredient(name="Salt", calories=0.0, carbs=0.0, protein=0.0, fat=0.0),
        Ingredient(
            name="Chicken Breast",
            calories=165.0,
            carbs=0.0,
            protein=31.0,
            fat=3.6,
        ),
        Ingredient(
            name="Rice", calories=130.0, carbs=28.0, protein=2.7, fat=0.3
        ),
        Ingredient(
            name="Tofu", calories=144.0, carbs=2.8, protein=15.8, fat=8.7
        ),
        Ingredient(
            name="Broccoli", calories=34.0, carbs=6.6, protein=2.8, fat=0.4
        ),
        Ingredient(
            name="Olive Oil", calories=884.0, carbs=0.0, protein=0.0, fat=100.0
        ),
    ]

    for ing_obj in ingredients:
        exists = Ingredient.query.filter_by(name=ing_obj.name).first()
        if not exists:
            db.session.add(ing_obj)
    db.session.commit()

    # refresh ingredient lookup
    ing = {i.name: i for i in Ingredient.query.all()}

    # Ensure example recipe exists and is linked to oulu_chef
    def get_or_create_recipe(
        title, procedure, servings, cuisine_type, img_url, creator
    ):
        r = Recipe.query.filter_by(title=title).first()
        if r:
            return r
        r = Recipe(
            title=title,
            procedure=procedure,
            servings=servings,
            cuisine_type=cuisine_type,
            img_url=img_url,
            created_at=datetime.now(timezone.utc),
            created_by=creator.id,
        )
        db.session.add(r)
        db.session.commit()
        return r

    # r1 = get_or_create_recipe(
    #     "Tomato and Egg Stir-fry",
    #     "1. Beat the eggs. 2. Chop tomatoes into chunks. 3. Scramble eggs in hot oil and set aside. 4. Stir-fry tomatoes until soft and juicy, return eggs to the pan, season with salt and a pinch of sugar, and serve.",
    #     2,
    #     "Chinese",
    #     "https://images.getrecipekit.com/20231103000214-andy-20cooks-20-20tomato-20egg-20stir-fry.jpg",
    #     admin,
    # )

    r1 = get_or_create_recipe(
        "Chicken Rice Bowl",
        "Cook chicken and serve with rice.",
        1,
        "Asian",
        None,
        admin,
    )

    # Attach ingredients to recipes idempotently
    def ensure_recipe_ingredient(recipe, ingredient_name, amount, unit):
        ingredient = Ingredient.query.filter_by(name=ingredient_name).first()
        if not ingredient:
            return
        exists = RecipeIngredient.query.filter_by(
            recipe_id=recipe.id, ingredient_id=ingredient.id
        ).first()
        if exists:
            return
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            amount=amount,
            unit=unit,
        )
        db.session.add(ri)

    # ensure_recipe_ingredient(r1, "Tomato", 300, "grams")
    # ensure_recipe_ingredient(r1, "Egg", 100, "grams")
    # ensure_recipe_ingredient(r1, "Salt", 5, "g")

    ensure_recipe_ingredient(r1, "Chicken Breast", 150, "g")
    ensure_recipe_ingredient(r1, "Rice", 200, "g")
    ensure_recipe_ingredient(r1, "Olive Oil", 10, "g")

    db.session.commit()

    from dbms.extensions import cache

    cache.clear()

    click.echo("Database populated successfully!")
    click.echo("[*] Admin User created: 'admin'")
    click.echo(
        f"[*] Admin API Key: '{admin.api_key}' (Use this in 'dbms-api-key' header)"
    )
    click.echo(
        f"[*] Example user created: 'oulu_chef' with API key: '{oulu_chef.api_key}'"
    )
