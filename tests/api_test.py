# pylint: disable=redefined-outer-name, import-error
"""
Comprehensive Automated Test Suite for the Flask RESTful API.

Run the tests and generate the coverage report using:
python -m pytest api/test.py --cov=api --cov-report=term-missing
"""

import os
import tempfile
import json
import warnings
from datetime import datetime

import pytest
from flask.testing import FlaskClient
from werkzeug.datastructures import Headers
from werkzeug.exceptions import NotFound
from werkzeug.routing import Map
from werkzeug.security import generate_password_hash

from dbms import create_app
from dbms.converters import SaveConverter
from dbms.extensions import db
from dbms.models import Recipe, Ingredient, RecipeIngredient, User, Save

# ignore ResourceWarnings caused by in-memory SQLite fast connections
warnings.filterwarnings("ignore", category=ResourceWarning)

TEST_KEY = "verysafetestkey"


class AuthHeaderClient(FlaskClient):
    """
    Custom Flask Test Client that automatically injects the API key
    into the request headers to simulate an authenticated user.
    """

    def open(self, *args, **kwargs):
        # put api_key
        headers = kwargs.pop("headers", None)
        new_headers = Headers(headers) if headers is not None else Headers()

        # Inject default test key if no custom key is provided
        if "dbms-api-key" not in new_headers:
            new_headers["dbms-api-key"] = TEST_KEY

        kwargs["headers"] = new_headers
        return super().open(*args, **kwargs)


@pytest.fixture
def client():
    """
    Pytest fixture to set up and tear down a temporary in-memory database
    for each test session. Ensures a clean state with dummy data.
    """
    db_fd, db_fname = tempfile.mkstemp()

    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True,
        "CACHE_TYPE": "NullCache",
        "TEST_CLIENT_CLASS": AuthHeaderClient,
    }

    app = create_app(config)
    app.test_client_class = AuthHeaderClient

    # context
    with app.app_context():
        db.create_all()
        _populate_db()

        yield app.test_client()

        # clear test
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_fname)


def _populate_db():
    """Helper function to populate the test database with initial data."""
    user = User(
        username="test-user",
        pwd=generate_password_hash("test-password"),
        email="test@example.com",
        created_at=datetime.now(),
        allergies="ingredient-2",
        api_key=User.hash_key(TEST_KEY),
    )

    user2 = User(
        username="test-user-2",
        pwd=generate_password_hash("test-password-2"),
        email="test2@example.com",
        created_at=datetime.now(),
        api_key=User.hash_key("user2key"),
    )

    db.session.add_all([user, user2])
    db.session.commit()

    for i in range(1, 4):
        recipe = Recipe(
            title=f"test-recipe-{i}",
            procedure=f"Test procedure {i}",
            servings=i,
            cuisine_type=f"cuisine-{i}",
            cooking_methods=f"method-{i}",
            img_url=f"https://example.com/recipe_{i}.jpg",
            created_at=datetime.now(),
            created_by=user.id,
        )
        db.session.add(recipe)

        # test nutrition
        ing = Ingredient(
            name=f"ingredient-{i}",
            calories=10.0 * i,
            carbs=5.0,
            protein=2.0,
            fat=1.0,
        )
        db.session.add(ing)
        db.session.commit()

        assoc = RecipeIngredient(
            recipe_id=recipe.id, ingredient_id=ing.id, amount=1.0, unit="piece"
        )
        db.session.add(assoc)

    db.session.commit()


def _get_recipe_json(number=1):
    """Helper function to generate valid recipe JSON payloads."""
    return {
        "title": f"extra-recipe-{number}",
        "procedure": "Extra instructions",
        "created_by": 1,
    }


def test_create_app_no_config():
    """
    Test the application factory initialization without test configurations.
    Ensures that the production/default sqlite configuration is loaded.
    """
    app = create_app(test_config=None)
    assert app is not None
    assert "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]


class TestCLICommands:  # pylint: disable=R0903
    """Tests for Custom Flask CLI commands (init-db and populate-db)."""

    def test_cli(self, client):
        """
        Test the execution of database management CLI commands.
        Forces the execution of data insertion logic by wiping the database
        first.
        """
        runner = client.application.test_cli_runner()
        # init db
        assert runner.invoke(args=["init-db"]).exit_code == 0
        # populate the first time, if have user, return
        assert runner.invoke(args=["populate-db"]).exit_code == 0

        # clear db to test populate in models.py
        with client.application.app_context():
            db.session.query(Save).delete()
            db.session.query(RecipeIngredient).delete()
            db.session.query(Recipe).delete()
            db.session.query(Ingredient).delete()
            db.session.query(User).delete()
            db.session.commit()

        assert runner.invoke(args=["populate-db"]).exit_code == 0


class TestRecipeCollection:
    """Tests for the RecipeCollection resource (/api/recipes/)."""

    RESOURCE_URL = "/api/recipes/"

    def test_get(self, client):
        """
        Test retrieving a paginated list of recipes successfully
        (200 OK).
        """
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 3
        for item in body:
            assert "title" in item
            assert "procedure" in item

    def test_post_valid_request(self, client):
        """Test creating a new recipe with a valid payload (201 Created)."""
        valid = _get_recipe_json()
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

        resp_get = client.get(resp.headers["Location"])
        assert resp_get.status_code == 200
        body = json.loads(resp_get.data)
        assert body["title"] == "extra-recipe-1"

    def test_wrong_mediatype(self, client):
        """
        Test creating a recipe with an invalid media type.
        Forces a 415 Unsupported Media Type error by sending plain text
        instead of JSON.
        """
        resp = client.post(
            self.RESOURCE_URL, data="not json", content_type="text/plain"
        )
        assert resp.status_code == 415

    def test_post_missing_field(self, client):
        """
        Test creating a recipe with a missing mandatory field.
        Forces a 400 Bad Request error by removing the required 'title' field,
        triggering JSON schema validation failure.
        """
        valid = _get_recipe_json()
        valid.pop("title")
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_unauthorized(self, client):
        """
        Test creating a recipe with invalid authentication.
        Forces a 401 Unauthorized error by providing an invalid 'dbms-api-key'.
        """
        valid = _get_recipe_json()
        # input wrong api key
        resp = client.post(
            self.RESOURCE_URL,
            json=valid,
            headers={"dbms-api-key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_get_invalid_pagination_type(self, client):
        """Test getting recipes with non-integer limit."""
        resp = client.get(self.RESOURCE_URL + "?limit=abc")
        assert resp.status_code == 400

    def test_get_negative_pagination(self, client):
        """Test getting recipes with negative limit."""
        resp = client.get(self.RESOURCE_URL + "?limit=-5")
        assert resp.status_code == 400


class TestRecipeItem:
    """Tests for the RecipeItem resource (/api/recipes/{id}/)."""

    RESOURCE_URL = "/api/recipes/1/"
    INVALID_URL = "/api/recipes/10086/"

    def test_get(self, client):
        """Test retrieving a specific recipe successfully (200 OK)."""
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["title"] == "test-recipe-1"

    def test_get_not_found(self, client):
        """
        Test retrieving a non-existent recipe.
        Forces a 404 Not Found error by providing an invalid recipe ID (10086).
        """
        assert client.get(self.INVALID_URL).status_code == 404

    def test_put_valid_request(self, client):
        """Test updating a recipe with a valid payload (204 No Content)."""
        valid = _get_recipe_json()
        valid["title"] = "Updated Title"
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

        # check if the update is actually successful
        check_resp = client.get(self.RESOURCE_URL)
        assert json.loads(check_resp.data)["title"] == "Updated Title"

    def test_put_not_found(self, client):
        """
        Test updating a non-existent recipe.
        Forces a 404 Not Found error using an invalid recipe ID.
        """
        valid = _get_recipe_json()
        assert client.put(self.INVALID_URL, json=valid).status_code == 404

    def test_wrong_mediatype(self, client):
        """
        Test updating a recipe with an invalid media type.
        Forces a 415 Unsupported Media Type error by sending plain text.
        """
        assert (
            client.put(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )

    def test_put_missing_field(self, client):
        """
        Test updating a recipe with missing mandatory fields.
        Forces a 400 Bad Request error by omitting the required 'title'.
        """
        valid = _get_recipe_json()
        valid.pop("title")
        assert client.put(self.RESOURCE_URL, json=valid).status_code == 400

    def test_put_forbidden(self, client):
        """
        Test updating a recipe created by another user.
        Forces a 403 Forbidden error by using 'user2key' to edit User 1's
        recipe.
        """
        valid = _get_recipe_json()
        assert (
            client.put(
                self.RESOURCE_URL,
                json=valid,
                headers={"dbms-api-key": "user2key"},
            ).status_code
            == 403
        )

    def test_delete_forbidden(self, client):
        """
        Test deleting a recipe created by another user.
        Forces a 403 Forbidden error by using 'user2key' on User 1's recipe.
        """
        assert (
            client.delete(
                self.RESOURCE_URL, headers={"dbms-api-key": "user2key"}
            ).status_code
            == 403
        )

    def test_delete(self, client):
        """Test deleting a recipe successfully (204 No Content)."""
        assert client.delete(self.RESOURCE_URL).status_code == 204
        assert client.get(self.RESOURCE_URL).status_code == 404

    def test_unauthorized(self, client):
        """
        Test updating a recipe with invalid credentials.
        Forces a 401 Unauthorized error by providing 'invalid-key'.
        """
        valid = _get_recipe_json()
        assert (
            client.put(
                self.RESOURCE_URL,
                json=valid,
                headers={"dbms-api-key": "invalid-key"},
            ).status_code
            == 401
        )


class TestRecipeIngredient:
    """
    Tests for the RecipeIngredientCollection resource
    (/api/recipes/{id}/ingredients/).
    """

    RESOURCE_URL = "/api/recipes/1/ingredients/"

    def test_get(self, client):
        """Test retrieving all ingredients for a specific recipe (200 OK)."""
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert isinstance(body, list)
        assert len(body) == 1

    def test_post_valid_request(self, client):
        """
        Test adding a new ingredient to a recipe successfully
        (201 Created).
        """
        valid = {"ingredient_id": 2, "amount": 1.0, "unit": "g"}
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.headers["Location"].endswith(self.RESOURCE_URL + "2/")

        resp_get = client.get(self.RESOURCE_URL)
        body = json.loads(resp_get.data)
        assert len(body) == 2

    def test_post_wrong_mediatype(self, client):
        """
        Test adding an ingredient with invalid media type.
        Forces a 415 Unsupported Media Type error by sending a raw string.
        """
        assert (
            client.post(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )

    def test_post_forbidden(self, client):
        """
        Test adding an ingredient to another user's recipe.
        Forces a 403 Forbidden error using 'user2key'.
        """
        valid = {"ingredient_id": 2, "amount": 1.0, "unit": "g"}
        assert (
            client.post(
                self.RESOURCE_URL,
                json=valid,
                headers={"dbms-api-key": "user2key"},
            ).status_code
            == 403
        )

    def test_post_missing_field(self, client):
        """
        Test adding an ingredient without providing the required ingredient_id.
        Forces a 400 Bad Request error.
        """
        assert (
            client.post(self.RESOURCE_URL, json={"amount": 1.0}).status_code
            == 400
        )

    def test_post_conflict(self, client):
        """
        Test adding an ingredient that is already part of the recipe.
        Forces a 409 Conflict error by adding ingredient_id=1 which exists.
        """
        valid = {"ingredient_id": 1, "amount": 1.0, "unit": "g"}
        assert client.post(self.RESOURCE_URL, json=valid).status_code == 409


class TestRecipeIngredientItem:
    """
    Tests for the RecipeIngredientItem resource
    (/api/recipes/{id}/ingredients/{id}/).
    """

    RESOURCE_URL = "/api/recipes/1/ingredients/1/"

    def test_put_success(self, client):
        """
        Test updating the amount and unit of an ingredient successfully
        (204 No Content).
        """
        assert (
            client.put(
                self.RESOURCE_URL, json={"amount": 5.0, "unit": "kg"}
            ).status_code
            == 204
        )

    def test_put_wrong_mediatype(self, client):
        """
        Test updating an ingredient with incorrect media type.
        Forces a 415 Unsupported Media Type error.
        """
        assert (
            client.put(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )

    def test_put_missing_field(self, client):
        """
        Test updating an ingredient with invalid data types.
        Forces a 400 Bad Request error by sending a string instead of a float
        for 'amount'.
        """
        assert (
            client.put(self.RESOURCE_URL, json={"amount": "str"}).status_code
            == 400
        )

    def test_put_not_found(self, client):
        """
        Test updating an ingredient for a non-existent recipe.
        Forces a 404 Not Found error.
        """
        assert (
            client.put(
                "/api/recipes/1/ingredients/99/", json={"amount": 5.0}
            ).status_code
            == 404
        )

    def test_put_assoc_not_found(self, client):
        """
        Test updating an ingredient that exists but is NOT linked to this
        recipe. Forces a 404 Not Found error.
        """
        assert (
            client.put(
                "/api/recipes/1/ingredients/2/", json={"amount": 5.0}
            ).status_code
            == 404
        )

    def test_put_forbidden(self, client):
        """
        Test updating an ingredient in a recipe owned by someone else.
        Forces a 403 Forbidden error using 'user2key'.
        """
        assert (
            client.put(
                self.RESOURCE_URL,
                json={"amount": 5.0},
                headers={"dbms-api-key": "user2key"},
            ).status_code
            == 403
        )

    def test_delete_forbidden(self, client):
        """
        Test deleting an ingredient from a recipe owned by someone else.
        Forces a 403 Forbidden error.
        """
        assert (
            client.delete(
                self.RESOURCE_URL, headers={"dbms-api-key": "user2key"}
            ).status_code
            == 403
        )

    def test_delete_success(self, client):
        """
        Test deleting an ingredient from a recipe successfully
        (204 No Content).
        """
        assert client.delete(self.RESOURCE_URL).status_code == 204

    def test_delete_assoc_not_found(self, client):
        """
        Test deleting an ingredient that is not linked to the recipe.
        This gracefully returns 204 No Content without crashing.
        """
        assert (
            client.delete("/api/recipes/1/ingredients/2/").status_code == 204
        )


class TestSave:
    """
    Tests for the SaveCollection and SaveItem resources
    (/api/users/{id}/saves/).
    """

    COLLECTION_URL = "/api/users/1/saves/"
    ITEM_URL = "/api/users/1/saves/"

    def test_get_empty(self, client):
        """Test retrieving the saved recipes list when it is empty (200 OK)."""
        resp = client.get(self.COLLECTION_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body == []

    def test_get_forbidden(self, client):
        """
        Test attempting to view another user's saved recipes.
        Forces a 403 Forbidden error using 'user2key' to access User 1's saves.
        """
        assert (
            client.get(
                self.COLLECTION_URL, headers={"dbms-api-key": "user2key"}
            ).status_code
            == 403
        )

    def test_post_save(self, client):
        """
        Test saving a recipe to the user's collection successfully
        (201 Created).
        """
        valid = {"recipe_id": 1}
        resp = client.post(self.COLLECTION_URL, json=valid)
        assert resp.status_code == 201
        resp_get = client.get(self.COLLECTION_URL)
        body = json.loads(resp_get.data)
        assert any(r["recipe_id"] == 1 for r in body)

    def test_post_conflict(self, client):
        """
        Test saving the same recipe twice.
        Forces a 409 Conflict error by saving recipe_id=2 consecutively.
        """
        client.post(self.COLLECTION_URL, json={"recipe_id": 2})
        assert (
            client.post(self.COLLECTION_URL, json={"recipe_id": 2}).status_code
            == 409
        )

    def test_post_missing_field(self, client):
        """
        Test saving a recipe with missing payload data.
        Forces a 400 Bad Request error by sending an empty JSON object.
        """
        assert client.post(self.COLLECTION_URL, json={}).status_code == 400

    def test_delete_save(self, client):
        """
        Test removing a saved recipe from the user's collection
        (204 No Content).
        """
        client.post(self.COLLECTION_URL, json={"recipe_id": 2})
        assert client.delete(self.ITEM_URL + "2/").status_code == 204

    def test_delete_save_not_found(self, client):
        """
        Test removing a saved recipe that the user has not saved yet.
        Uses a valid Recipe ID (3) to bypass Converter 404, gracefully
        returning 204.
        """
        assert client.delete(self.ITEM_URL + "3/").status_code == 204

    def test_unauthorized(self, client):
        """
        Test saving a recipe with invalid authentication credentials.
        Forces a 401 Unauthorized error.
        """
        assert (
            client.post(
                self.COLLECTION_URL,
                json={"recipe_id": 1},
                headers={"dbms-api-key": "wrong"},
            ).status_code
            == 401
        )


class TestUserCollection:
    """Tests for the UserCollection resource (/api/users/)."""

    RESOURCE_URL = "/api/users/"

    def test_get(self, client):
        """Test retrieving a paginated list of users (200 OK)."""
        assert client.get(self.RESOURCE_URL).status_code == 200

    def test_post(self, client):
        """Test registering a new user successfully (201 Created)."""
        valid = {"username": "new-user", "email": "new@test.com", "pwd": "123"}
        assert client.post(self.RESOURCE_URL, json=valid).status_code == 201

    def test_post_conflict(self, client):
        """
        Test registering a user with a username that already exists.
        Forces a 409 Conflict error, triggering an IntegrityError rollback.
        """
        valid = {
            "username": "test-user",
            "email": "test@example.com",
            "pwd": "123",
        }
        assert client.post(self.RESOURCE_URL, json=valid).status_code == 409

    def test_post_missing_field(self, client):
        """
        Test registering a user missing mandatory fields (e.g., username/pwd).
        Forces a 400 Bad Request error via schema validation.
        """
        valid = {"email": "new@test.com"}
        assert client.post(self.RESOURCE_URL, json=valid).status_code == 400

    def test_post_wrong_mediatype(self, client):
        """
        Test registering a user with an invalid media type.
        Forces a 415 Unsupported Media Type error.
        """
        assert (
            client.post(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )


class TestUserItem:
    """Tests for the UserItem resource (/api/users/{id}/)."""

    RESOURCE_URL = "/api/users/1/"
    INVALID_URL = "/api/users/999/"

    def test_get_success(self, client):
        """Test retrieving profile details for a specific user (200 OK)."""
        assert client.get(self.RESOURCE_URL).status_code == 200

    def test_get_not_found(self, client):
        """
        Test retrieving profile details for a non-existent user.
        Forces a 404 Not Found error via UserConverter.
        """
        assert client.get(self.INVALID_URL).status_code == 404

    def test_put_success(self, client):
        """Test updating user profile details successfully (204 No Content)."""
        valid = {
            "username": "updated-user",
            "email": "test@example.com",
            "pwd": "pwd",
            "created_at": "2026-01-01T00:00:00",
        }
        assert client.put(self.RESOURCE_URL, json=valid).status_code == 204

    def test_put_conflict(self, client):
        """
        Test updating user profile with an already taken username.
        Forces a 409 Conflict error.
        """
        valid = {
            "username": "test-user-2",
            "email": "test@example.com",
            "pwd": "pwd",
            "created_at": "2026-01-01T00:00:00",
        }
        assert client.put(self.RESOURCE_URL, json=valid).status_code == 409

    def test_put_bad_request(self, client):
        """
        Test updating user profile with missing fields.
        Forces a 400 Bad Request error.
        """
        assert (
            client.put(
                self.RESOURCE_URL, json={"email": "test@example.com"}
            ).status_code
            == 400
        )

    def test_put_wrong_mediatype(self, client):
        """
        Test updating user profile with an invalid media type.
        Forces a 415 Unsupported Media Type error.
        """
        assert (
            client.put(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )

    def test_delete(self, client):
        """Test deleting a user account successfully (204 No Content)."""
        assert client.delete(self.RESOURCE_URL).status_code == 204
        assert client.get(self.RESOURCE_URL).status_code == 404

    def test_unauthorized(self, client):
        """
        Test updating user profile with an empty/missing authentication header.
        Forces a 401 Unauthorized error.
        """
        valid = {
            "username": "hacked",
            "email": "hack@test.com",
            "pwd": "123",
            "created_at": "2026-01-01T00:00:00",
        }
        assert (
            client.put(
                self.RESOURCE_URL, json=valid, headers={"dbms-api-key": ""}
            ).status_code
            == 401
        )

    def test_forbidden(self, client):
        """
        Test attempting to update or delete someone else's user profile.
        Forces a 403 Forbidden error using 'user2key' to modify User 1.
        """
        valid = {
            "username": "hacked",
            "email": "hack@test.com",
            "pwd": "123",
            "created_at": "2026-01-01T00:00:00",
        }
        assert (
            client.put(
                self.RESOURCE_URL,
                json=valid,
                headers={"dbms-api-key": "user2key"},
            ).status_code
            == 403
        )
        assert (
            client.delete(
                self.RESOURCE_URL, headers={"dbms-api-key": "user2key"}
            ).status_code
            == 403
        )


class TestUserRecipeCollection:
    """
    Tests for the UserRecipeCollection resource (/api/users/{id}/recipes/).
    """

    def test_get_user_recipes(self, client):
        """Test retrieving all recipes created by a specific user (200 OK)."""
        resp = client.get("/api/users/1/recipes/")
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) > 0
        assert "title" in body[0]

    def test_get_user_not_found(self, client):
        """
        Test retrieving recipes for a non-existent user.
        Forces a 404 Not Found error via UserConverter.
        """
        assert client.get("/api/users/999/recipes/").status_code == 404


class TestIngredientCollection:
    """Tests for the IngredientCollection resource (/api/ingredients/)."""

    RESOURCE_URL = "/api/ingredients/"

    def test_get(self, client):
        """Test retrieving a paginated list of ingredients (200 OK)."""
        assert client.get(self.RESOURCE_URL).status_code == 200
        assert (
            client.get(self.RESOURCE_URL + "?limit=1&offset=0").status_code
            == 200
        )

    def test_post_success(self, client):
        """Test creating a new ingredient successfully (201 Created)."""
        assert (
            client.post(
                self.RESOURCE_URL, json={"name": "Salt", "calories": 0.0}
            ).status_code
            == 201
        )

    def test_post_missing_field(self, client):
        """
        Test creating a new ingredient with missing mandatory name field.
        Forces a 400 Bad Request error.
        """
        assert (
            client.post(
                self.RESOURCE_URL, json={"calories": 100.0}
            ).status_code
            == 400
        )

    def test_post_wrong_mediatype(self, client):
        """
        Test creating a new ingredient with an invalid media type.
        Forces a 415 Unsupported Media Type error.
        """
        assert (
            client.post(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )


class TestIngredientItem:
    """Tests for the IngredientItem resource (/api/ingredients/{id}/)."""

    RESOURCE_URL = "/api/ingredients/1/"
    INVALID_URL = "/api/ingredients/999/"

    def test_get_success(self, client):
        """Test retrieving a specific ingredient's details (200 OK)."""
        assert client.get(self.RESOURCE_URL).status_code == 200

    def test_get_not_found(self, client):
        """
        Test retrieving a non-existent ingredient.
        Forces a 404 Not Found error via IngredientConverter.
        """
        assert client.get(self.INVALID_URL).status_code == 404

    def test_put_success(self, client):
        """
        Test updating an ingredient's details successfully (204 No Content).
        """
        assert (
            client.put(
                self.RESOURCE_URL,
                json={"name": "Salt Updated", "calories": 5.0},
            ).status_code
            == 204
        )

    def test_put_invalid_type(self, client):
        """
        Test updating an ingredient with incorrect data types.
        Forces a 400 Bad Request error by passing a string for
        a float field ('calories').
        """
        assert (
            client.put(
                self.RESOURCE_URL,
                json={"name": "Salt", "calories": "too high"},
            ).status_code
            == 400
        )

    def test_put_wrong_mediatype(self, client):
        """
        Test updating an ingredient with an invalid media type.
        Forces a 415 Unsupported Media Type error.
        """
        assert (
            client.put(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )


class TestRecipeNutrition:
    """
    Tests for the RecipeNutrition resource (/api/recipes/{id}/nutrition/).
    """

    RESOURCE_URL = "/api/recipes/1/nutrition/"
    INVALID_URL = "/api/recipes/999/nutrition/"

    def test_get_nutrition_success(self, client):
        """
        Test retrieving correct nutritional calculation results for a recipe
        (200 OK). Ensures all key nutritional data points are returned in the
        payload.
        """
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "total_calories" in body
        assert "total_protein" in body
        assert "total_carbs" in body
        assert "total_fat" in body

    def test_get_nutrition_not_found(self, client):
        """
        Test attempting to calculate nutrition for a non-existent recipe.
        Forces a 404 Not Found error via RecipeConverter.
        """
        assert client.get(self.INVALID_URL).status_code == 404


class TestSaveConverter:  # pylint: disable=R0903
    """Tests for the custom SaveConverter routing logic."""

    def test_save_converter(self, client):
        """
        Test routing converter logic for parsing and formatting save IDs.
        Forces NotFound exceptions by providing malformed strings
        ("invalid-format") and IDs pointing to non-existent database
        relations ("99-99").
        """
        conv = SaveConverter(Map())

        # Create a save resource first to test successful extraction
        client.post("/api/users/1/saves/", json={"recipe_id": 1})

        # Test string -> python obj conversion
        obj = conv.to_python("1-1")
        assert obj.user_id == 1
        assert obj.recipe_id == 1

        # Test python obj -> url string conversion
        assert conv.to_url(obj) == "1-1"

        # Force a 404 Not Found error by passing an incorrectly
        # formatted string
        with pytest.raises(NotFound):
            conv.to_python("invalid-format")

        # Force a 404 Not Found error by requesting a non-existent save pair
        with pytest.raises(NotFound):
            conv.to_python("99-99")


class TestToken:
    """Tests for Token collection (login/logout)."""

    URL = "/api/tokens/"

    def test_post_login_success(self, client):
        """Test successful login returns a new token."""
        # test user from _populate_db
        data = {"email": "test@example.com", "pwd": "test-password"}
        resp = client.post(self.URL, json=data)
        assert resp.status_code == 201
        body = json.loads(resp.data)
        assert "token" in body
        assert len(body["token"]) == 64

    def test_post_login_invalid_email(self, client):
        """Test login with non-existent email."""
        data = {"email": "nonexistent@example.com", "pwd": "test-password"}
        resp = client.post(self.URL, json=data)
        assert resp.status_code == 401

    def test_post_login_invalid_pwd(self, client):
        """Test login with wrong password."""
        data = {"email": "test@example.com", "pwd": "wrongpwd"}
        resp = client.post(self.URL, json=data)
        assert resp.status_code == 401

    def test_post_login_missing_fields(self, client):
        """Test login missing fields."""
        data = {"email": "test@example.com"}
        resp = client.post(self.URL, json=data)
        assert resp.status_code == 400

    def test_delete_logout_success(self, client):
        """Test successful logout invalidates the token."""
        # Client automatically uses valid token "verysafetestkey"
        resp = client.delete(self.URL)
        assert resp.status_code == 204

        # The old token should now be invalid
        # Requesting an endpoint that requires auth (like DELETE /api/tokens/)
        # with the same old token should fail.
        resp_after = client.delete(self.URL)
        assert resp_after.status_code == 401

    def test_delete_logout_unauthorized(self, client):
        """Test logout with invalid token fails."""
        resp = client.delete(self.URL, headers={"dbms-api-key": "invalid_key"})
        assert resp.status_code == 401

