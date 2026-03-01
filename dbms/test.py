"""
Comprehensive Automated Test Suite for the Flask RESTful API.

Run the tests and generate the coverage report using:
python -m pytest api/test.py --cov=api --cov-report=term-missing
"""

from datetime import datetime
import json
import pytest
from werkzeug.security import generate_password_hash

from dbms.app import app
from dbms.extensions import db
from database.dbcreation import (
    Recipe,
    Ingredient,
    RecipeIngredient,
    User,
)

from flask.testing import FlaskClient
from werkzeug.datastructures import Headers

TEST_KEY = "verysafetestkey"


@pytest.fixture
def client():
    # no real http request is used
    ctx = app.app_context()
    ctx.push()

    app.config["CACHE_TYPE"] = "NullCache"

    db.drop_all()
    db.create_all()

    try:
        # generate basic data
        _populate_db()
        # client with auth
        app.test_client_class = AuthHeaderClient
        yield app.test_client()
    finally:
        db.session.remove()
        # clear context
        db.drop_all()
        ctx.pop()


def _populate_db():
    user = User(
        username="test-user",
        pwd=generate_password_hash("test-password"),
        email="test@example.com",
        created_at=datetime.now(),
        allergies="ingredient-2",
        api_key=User.hash_key(TEST_KEY),
    )
    db.session.add(user)
    db.session.commit()

    for i in range(1, 4):
        recipe = Recipe(
            title=f"test-recipe-{i}",
            procedure=f"Test procedure {i}",
            servings=i,
            cuisine_type=f"cuisine-{i}",
            cooking_methods=f"method-{i}",
            created_at=datetime.now(),
            created_by=user.id,
        )
        db.session.add(recipe)

        # test nutrition
        ing = Ingredient(name=f"ingredient-{i}", calories=10.0 * i)
        db.session.add(ing)
        db.session.commit()

        assoc = RecipeIngredient(
            recipe_id=recipe.id, ingredient_id=ing.id, amount=1.0, unit="piece"
        )
        db.session.add(assoc)

    db.session.commit()


class AuthHeaderClient(FlaskClient):
    def open(self, *args, **kwargs):
        # put api_key
        headers = Headers({"dbms-api-key": TEST_KEY})

        extra_headers = kwargs.pop("headers", Headers())
        headers.extend(extra_headers)
        kwargs["headers"] = headers

        return super().open(*args, **kwargs)


def _get_recipe_json(number=1):
    return {
        "title": f"extra-recipe-{number}",
        "procedure": "Extra instructions",
        "created_by": 1,
    }


class TestRecipeCollection:

    RESOURCE_URL = "/api/recipes/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 3
        for item in body:
            assert "title" in item
            assert "procedure" in item

    def test_post_valid_request(self, client):
        valid = _get_recipe_json()
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

        resp = client.get(resp.headers["Location"])
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["title"] == "extra-recipe-1"

    def test_wrong_mediatype(self, client):
        valid = _get_recipe_json()
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

    def test_post_missing_field(self, client):
        valid = _get_recipe_json()  # valid data
        valid.pop("title")  # delete title(mandatory) field to test
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_unauthorized(self, client):
        valid = _get_recipe_json()
        # input wrong api key
        resp = client.post(
            self.RESOURCE_URL,
            json=valid,
            headers={"dbms-api-key": "wrong-key"},
        )
        # should be 401 unauthorized
        assert resp.status_code == 401

    # recipe title is not unique
    def test_post_name_conflict(self, client):
        valid = _get_recipe_json()
        valid["title"] = "test-recipe-1"
        valid["id"] = 1  # primary key conflict
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409


class TestRecipeItem:

    RESOURCE_URL = "/api/recipes/1/"
    INVALID_URL = "/api/recipes/10086/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["title"] == "test-recipe-1"

    def test_get_not_found(self, client):
        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_put_valid_request(self, client):
        valid = _get_recipe_json()
        valid["title"] = "Updated Title"
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

        # check if the update is actually successful
        check_resp = client.get(self.RESOURCE_URL)
        assert json.loads(check_resp.data)["title"] == "Updated Title"

    def test_wrong_mediatype(self, client):
        valid = _get_recipe_json()
        resp = client.put(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

    def test_put_missing_field(self, client):
        valid = _get_recipe_json()
        valid.pop("title")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_put_title_conflict(self, client):
        valid = _get_recipe_json()
        valid["title"] = "test-recipe-2"
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409

    def test_delete(self, client):
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 404

    def test_unauthorized(self, client):
        valid = _get_recipe_json()
        resp = client.put(
            self.RESOURCE_URL,
            json=valid,
            headers={"dbms-api-key": "invalid-key"},
        )
        assert resp.status_code == 401


class TestRecipeIngredient:

    RESOURCE_URL = "/api/recipes/1/ingredients/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert isinstance(body, list)
        assert len(body) == 1

    def test_post_valid_request(self, client):
        valid = {"ingredient_id": 2, "amount": 1.0, "unit": "g"}
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

        resp = client.get(self.RESOURCE_URL)
        body = json.loads(resp.data)
        assert len(body) == 2
        # check Location's resource url
        assert resp.headers["Location"].endswith(self.RESOURCE_URL + "4/")

    def test_post_wrong_mediatype(self, client):
        valid = {"ingredient_id": 2}
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415


class TestSave:

    COLLECTION_URL = "/api/users/1/saves/"
    ITEM_URL = "/api/users/1/saves/"

    def test_get_empty(self, client):
        resp = client.get(self.COLLECTION_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body == []

    def test_post_save(self, client):
        valid = {"recipe_id": 1}
        resp = client.post(self.COLLECTION_URL, json=valid)
        assert resp.status_code == 201
        resp = client.get(self.COLLECTION_URL)
        body = json.loads(resp.data)
        assert any(r["title"] == "test-recipe-1" for r in body)

    def test_delete_save(self, client):
        client.post(self.COLLECTION_URL, json={"recipe_id": 1})
        resp = client.delete(self.ITEM_URL + "1/")
        assert resp.status_code == 204
        resp = client.get(self.COLLECTION_URL)
        body = json.loads(resp.data)
        assert all(r["title"] != "test-recipe-1" for r in body)

    def test_unauthorized(self, client):
        resp = client.post(
            self.COLLECTION_URL,
            json={"recipe_id": 1},
            headers={"dbms-api-key": "wrong"},
        )
        assert resp.status_code == 401


class TestUserCollection:
    RESOURCE_URL = "/api/users/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

    def test_post(self, client):
        valid = {"username": "new-user", "email": "new@test.com", "pwd": "123"}
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201


class TestUserItem:
    RESOURCE_URL = "/api/users/1/"
    INVALID_URL = "/api/users/999/"

    def test_get_success(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

    def test_get_not_found(self, client):
        """test get user not exist"""
        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_put_success(self, client):
        valid = {
            "username": "updated-user",
            "email": "test@example.com",
            "pwd": "pwd",
        }
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

    def test_put_conflict(self, client):
        """test when update, username conflict (409)"""
        # create user2
        client.post(
            "/api/users/",
            json={
                "username": "user2",
                "email": "user2@test.com",
                "pwd": "123",
            },
        )
        # try update user1 name to user2
        valid = {
            "username": "user2",
            "email": "test@example.com",
            "pwd": "pwd",
        }
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409

    def test_put_bad_request(self, client):
        """update with out required field (400)"""
        valid = {"email": "test@example.com"}  # no usernam and pwd
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_put_wrong_mediatype(self, client):
        """test wrong media type (415)"""
        resp = client.put(self.RESOURCE_URL, data="not json")
        assert resp.status_code == 415

    def test_delete(self, client):
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204
        # test if really deleted
        assert client.get(self.RESOURCE_URL).status_code == 404

    def test_unauthorized(self, client):
        valid = {"username": "hacker", "email": "hacker@test.com"}
        resp = client.put(
            self.RESOURCE_URL, json=valid, headers={"dbms-api-key": "none"}
        )
        assert resp.status_code == 401


class TestIngredientCollection:
    RESOURCE_URL = "/api/ingredients/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

    def test_get_with_pagination(self, client):
        """test get with pagination request"""
        resp = client.get(self.RESOURCE_URL + "?limit=1&offset=0")
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 1

    def test_post_success(self, client):
        valid = {"name": "Salt", "calories": 0.0}
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

    def test_post_missing_field(self, client):
        """test without required name (400)"""
        valid = {"calories": 100.0}
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_post_wrong_mediatype(self, client):
        """test wrong media type (415)"""
        resp = client.post(self.RESOURCE_URL, data="not json")
        assert resp.status_code == 415


class TestIngredientItem:
    RESOURCE_URL = "/api/ingredients/1/"
    INVALID_URL = "/api/ingredients/999/"

    def test_get_success(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

    def test_get_not_found(self, client):
        """test get non-exist ingredient"""
        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_put_success(self, client):
        valid = {"name": "Salt Updated", "calories": 5.0}
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

    def test_put_invalid_type(self, client):
        """
        test input wrong type, calories should be number but
        provided string (400)
        """
        valid = {"name": "Salt", "calories": "too high"}
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_put_wrong_mediatype(self, client):
        resp = client.put(self.RESOURCE_URL, data="not json")
        assert resp.status_code == 415


class TestRecipeNutrition:
    RESOURCE_URL = "/api/recipes/1/nutrition/"
    INVALID_URL = "/api/recipes/999/nutrition/"

    def test_get_nutrition_success(self, client):
        """test get correct calc result for nutrition"""
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "total_calories" in body
        assert "total_protein" in body

    def test_get_nutrition_not_found(self, client):
        """test calc nutrition for a non-exist recipe (404)"""
        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404
