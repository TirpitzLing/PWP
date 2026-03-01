"""
Comprehensive Automated Test Suite for the Flask RESTful API.

Run the tests and generate the coverage report using:
python -m pytest api/test.py --cov=api --cov-report=term-missing
"""

import os
import tempfile
import json
import pytest
import warnings
from datetime import datetime
from werkzeug.security import generate_password_hash
from werkzeug.datastructures import Headers
from flask.testing import FlaskClient

from dbms import create_app
from dbms.extensions import db
from dbms.models import Recipe, Ingredient, RecipeIngredient, User, Save

warnings.filterwarnings("ignore", category=ResourceWarning)

TEST_KEY = "verysafetestkey"


class AuthHeaderClient(FlaskClient):
    def open(self, *args, **kwargs):
        # put api_key
        headers = kwargs.pop("headers", None)
        new_headers = Headers(headers) if headers is not None else Headers()

        if "dbms-api-key" not in new_headers:
            new_headers["dbms-api-key"] = TEST_KEY

        kwargs["headers"] = new_headers
        return super().open(*args, **kwargs)


@pytest.fixture
def client():
    # tmp db
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
    return {
        "title": f"extra-recipe-{number}",
        "procedure": "Extra instructions",
        "created_by": 1,
    }


def test_create_app_no_config():
    """test load config without test config"""
    app = create_app(test_config=None)
    assert app is not None
    assert "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]


class TestCLICommands:
    def test_cli(self, client):
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

        resp_get = client.get(resp.headers["Location"])
        assert resp_get.status_code == 200
        body = json.loads(resp_get.data)
        assert body["title"] == "extra-recipe-1"

    def test_wrong_mediatype(self, client):
        resp = client.post(
            self.RESOURCE_URL, data="not json", content_type="text/plain"
        )
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
    # def test_post_name_conflict(self, client):
    #     valid = _get_recipe_json()
    #     valid["title"] = "test-recipe-1"
    #     valid["id"] = 1  # primary key conflict
    #     resp = client.post(self.RESOURCE_URL, json=valid)
    #     assert resp.status_code == 409


class TestRecipeItem:

    RESOURCE_URL = "/api/recipes/1/"
    INVALID_URL = "/api/recipes/10086/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["title"] == "test-recipe-1"

    def test_get_not_found(self, client):
        assert client.get(self.INVALID_URL).status_code == 404

    def test_put_valid_request(self, client):
        valid = _get_recipe_json()
        valid["title"] = "Updated Title"
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

        # check if the update is actually successful
        check_resp = client.get(self.RESOURCE_URL)
        assert json.loads(check_resp.data)["title"] == "Updated Title"

    def test_put_not_found(self, client):
        # 404 if not found recipe
        valid = _get_recipe_json()
        assert client.put(self.INVALID_URL, json=valid).status_code == 404

    def test_wrong_mediatype(self, client):
        assert (
            client.put(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )

    def test_put_missing_field(self, client):
        valid = _get_recipe_json()
        valid.pop("title")
        assert client.put(self.RESOURCE_URL, json=valid).status_code == 400

    def test_put_forbidden(self, client):
        # try use user2 key edit user1's recipe (403)
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
        # try use user2 key delete user1's recipe (403)
        assert (
            client.delete(
                self.RESOURCE_URL, headers={"dbms-api-key": "user2key"}
            ).status_code
            == 403
        )

    def test_delete(self, client):
        assert client.delete(self.RESOURCE_URL).status_code == 204
        assert client.get(self.RESOURCE_URL).status_code == 404

    def test_unauthorized(self, client):
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
        assert resp.headers["Location"].endswith(self.RESOURCE_URL + "2/")

        resp_get = client.get(self.RESOURCE_URL)
        body = json.loads(resp_get.data)
        assert len(body) == 2
        # check Location's resource url
        # assert resp.headers["Location"].endswith(self.RESOURCE_URL + "4/")

    def test_post_wrong_mediatype(self, client):
        assert (
            client.post(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )

    def test_post_forbidden(self, client):
        # add ing using user2 to user1's recipe
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
        assert (
            client.post(self.RESOURCE_URL, json={"amount": 1.0}).status_code
            == 400
        )

    def test_post_conflict(self, client):
        # ingredient_id=1 added already when init
        valid = {"ingredient_id": 1, "amount": 1.0, "unit": "g"}
        assert client.post(self.RESOURCE_URL, json=valid).status_code == 409


class TestRecipeIngredientItem:
    # test single ingredient put and del
    RESOURCE_URL = "/api/recipes/1/ingredients/1/"

    def test_put_success(self, client):
        assert (
            client.put(
                self.RESOURCE_URL, json={"amount": 5.0, "unit": "kg"}
            ).status_code
            == 204
        )

    def test_put_wrong_mediatype(self, client):
        assert (
            client.put(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )

    def test_put_missing_field(self, client):
        assert (
            client.put(self.RESOURCE_URL, json={"amount": "str"}).status_code
            == 400
        )

    def test_put_not_found(self, client):
        assert (
            client.put(
                "/api/recipes/1/ingredients/99/", json={"amount": 5.0}
            ).status_code
            == 404
        )

    def test_put_assoc_not_found(self, client):
        # test edit a non-exist ingredient(404)
        assert (
            client.put(
                "/api/recipes/1/ingredients/2/", json={"amount": 5.0}
            ).status_code
            == 404
        )

    def test_put_forbidden(self, client):
        assert (
            client.put(
                self.RESOURCE_URL,
                json={"amount": 5.0},
                headers={"dbms-api-key": "user2key"},
            ).status_code
            == 403
        )

    def test_delete_forbidden(self, client):
        assert (
            client.delete(
                self.RESOURCE_URL, headers={"dbms-api-key": "user2key"}
            ).status_code
            == 403
        )

    def test_delete_success(self, client):
        assert client.delete(self.RESOURCE_URL).status_code == 204

    def test_delete_assoc_not_found(self, client):
        # delete a non-exist assoc ingredient (204)
        assert (
            client.delete("/api/recipes/1/ingredients/2/").status_code == 204
        )


class TestSave:
    COLLECTION_URL = "/api/users/1/saves/"
    ITEM_URL = "/api/users/1/saves/"

    def test_get_empty(self, client):
        resp = client.get(self.COLLECTION_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body == []

    def test_get_forbidden(self, client):
        # test check other user's save folder
        assert (
            client.get(
                self.COLLECTION_URL, headers={"dbms-api-key": "user2key"}
            ).status_code
            == 403
        )

    def test_post_save(self, client):
        valid = {"recipe_id": 1}
        resp = client.post(self.COLLECTION_URL, json=valid)
        assert resp.status_code == 201
        resp_get = client.get(self.COLLECTION_URL)
        body = json.loads(resp_get.data)
        assert any(r["recipe_id"] == 1 for r in body)

    def test_post_conflict(self, client):
        client.post(self.COLLECTION_URL, json={"recipe_id": 2})
        assert (
            client.post(self.COLLECTION_URL, json={"recipe_id": 2}).status_code
            == 409
        )

    # test missing recipe_id (400)
    def test_post_missing_field(self, client):
        assert client.post(self.COLLECTION_URL, json={}).status_code == 400

    def test_delete_save(self, client):
        client.post(self.COLLECTION_URL, json={"recipe_id": 2})
        assert client.delete(self.ITEM_URL + "2/").status_code == 204

    def test_delete_save_not_found(self, client):
        # test delete a non-exist save
        assert client.delete(self.ITEM_URL + "3/").status_code == 204

    def test_unauthorized(self, client):
        assert (
            client.post(
                self.COLLECTION_URL,
                json={"recipe_id": 1},
                headers={"dbms-api-key": "wrong"},
            ).status_code
            == 401
        )


class TestUserCollection:
    RESOURCE_URL = "/api/users/"

    def test_get(self, client):
        assert client.get(self.RESOURCE_URL).status_code == 200

    def test_post(self, client):
        valid = {"username": "new-user", "email": "new@test.com", "pwd": "123"}
        assert client.post(self.RESOURCE_URL, json=valid).status_code == 201

    # test name conflict (409)
    def test_post_conflict(self, client):
        valid = {
            "username": "test-user",
            "email": "test@example.com",
            "pwd": "123",
        }
        assert client.post(self.RESOURCE_URL, json=valid).status_code == 409

    # test missing field (400)
    def test_post_missing_field(self, client):
        valid = {"email": "new@test.com"}
        assert client.post(self.RESOURCE_URL, json=valid).status_code == 400

    def test_post_wrong_mediatype(self, client):
        assert (
            client.post(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )


class TestUserItem:
    RESOURCE_URL = "/api/users/1/"
    INVALID_URL = "/api/users/999/"

    def test_get_success(self, client):
        assert client.get(self.RESOURCE_URL).status_code == 200

    def test_get_not_found(self, client):
        assert client.get(self.INVALID_URL).status_code == 404

    def test_put_success(self, client):
        valid = {
            "username": "updated-user",
            "email": "test@example.com",
            "pwd": "pwd",
            "created_at": "2026-01-01T00:00:00",
        }
        assert client.put(self.RESOURCE_URL, json=valid).status_code == 204

    def test_put_conflict(self, client):
        """test when update, username conflict (409)"""
        # try update user1 name to existing name user2
        valid = {
            "username": "test-user-2",
            "email": "test@example.com",
            "pwd": "pwd",
            "created_at": "2026-01-01T00:00:00",
        }
        assert client.put(self.RESOURCE_URL, json=valid).status_code == 409

    def test_put_bad_request(self, client):
        """update with out required field (400)"""
        assert (
            client.put(
                self.RESOURCE_URL, json={"email": "test@example.com"}
            ).status_code
            == 400
        )

    def test_put_wrong_mediatype(self, client):
        assert (
            client.put(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )

    def test_delete(self, client):
        assert client.delete(self.RESOURCE_URL).status_code == 204
        assert client.get(self.RESOURCE_URL).status_code == 404

    def test_unauthorized(self, client):
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
        # try edit user1 info with user2
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
    def test_get_user_recipes(self, client):
        resp = client.get("/api/users/1/recipes/")
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) > 0
        assert "title" in body[0]


class TestIngredientCollection:
    RESOURCE_URL = "/api/ingredients/"

    def test_get(self, client):
        assert client.get(self.RESOURCE_URL).status_code == 200
        assert (
            client.get(self.RESOURCE_URL + "?limit=1&offset=0").status_code
            == 200
        )

    def test_post_success(self, client):
        assert (
            client.post(
                self.RESOURCE_URL, json={"name": "Salt", "calories": 0.0}
            ).status_code
            == 201
        )

    def test_post_missing_field(self, client):
        assert (
            client.post(
                self.RESOURCE_URL, json={"calories": 100.0}
            ).status_code
            == 400
        )

    def test_post_wrong_mediatype(self, client):
        assert (
            client.post(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )


class TestIngredientItem:
    RESOURCE_URL = "/api/ingredients/1/"
    INVALID_URL = "/api/ingredients/999/"

    def test_get_success(self, client):
        assert client.get(self.RESOURCE_URL).status_code == 200

    def test_get_not_found(self, client):
        assert client.get(self.INVALID_URL).status_code == 404

    def test_put_success(self, client):
        assert (
            client.put(
                self.RESOURCE_URL,
                json={"name": "Salt Updated", "calories": 5.0},
            ).status_code
            == 204
        )

    def test_put_invalid_type(self, client):
        """
        test input wrong type, calories should be number but
        provided string (400)
        """
        assert (
            client.put(
                self.RESOURCE_URL,
                json={"name": "Salt", "calories": "too high"},
            ).status_code
            == 400
        )

    def test_put_wrong_mediatype(self, client):
        assert (
            client.put(
                self.RESOURCE_URL, data="not json", content_type="text/plain"
            ).status_code
            == 415
        )


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
        assert "total_carbs" in body
        assert "total_fat" in body

    def test_get_nutrition_not_found(self, client):
        """test calc nutrition for a non-exist recipe (404)"""
        assert client.get(self.INVALID_URL).status_code == 404


class TestSaveConverter:
    # for SaveConverter
    def test_save_converter(self, client):
        from dbms.converters import SaveConverter
        from werkzeug.routing import Map
        from werkzeug.exceptions import NotFound

        conv = SaveConverter(Map())

        # create a save
        client.post("/api/users/1/saves/", json={"recipe_id": 1})

        # test string convert to python obj
        obj = conv.to_python("1-1")
        assert obj.user_id == 1
        assert obj.recipe_id == 1

        # test py obj -> url string
        assert conv.to_url(obj) == "1-1"

        # test format error/not found
        with pytest.raises(NotFound):
            conv.to_python("invalid-format")

        with pytest.raises(NotFound):
            conv.to_python("99-99")
