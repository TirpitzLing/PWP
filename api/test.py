from datetime import datetime
import json
import pytest

from api.app import app
from api.extensions import db
from database.dbcreation import Recipe, Ingredient, RecipeIngredient, User


@pytest.fixture
def client():
    ctx = app.app_context()
    ctx.push()

    db.drop_all()
    db.create_all()

    try:
        _populate_db()
        yield app.test_client()
    finally:
        db.session.remove()
        db.drop_all()
        ctx.pop()


def _populate_db():
    user = User(username="test-user", pwd="test-password", email="test@example.com", created_at=datetime.now(), allergies="ingredient-2")
    db.session.add(user)
    db.session.flush()

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

        ing = Ingredient(name=f"ingredient-{i}")
        db.session.add(ing)
        db.session.flush()

        assoc = RecipeIngredient(recipe=recipe, ingredient=ing, amount=1.0, unit="piece")
        db.session.add(assoc)
        db.session.add(recipe)

    db.session.commit()

    for i in range(1, 4):
        recipe = Recipe(
            title=f"test-recipe-{i}",
            procedure=f"Test procedure {i}",
            servings=i,
            cuisine_type=f"cuisine-{i}",
            cooking_methods=f"method-{i}",
        )
        ing = Ingredient(name=f"ingredient-{i}")
        recipe.ingredients.append(ing)
        db.session.add(recipe)

    user = User(username="test-user", pwd="test-password", email="test@example.com")
    allergy = Ingredient(name="ingredient-2")
    user.allergies.append(allergy)
    db.session.add(user)

    db.session.commit()


def _get_recipe_json(number=1):
    return {"name": f"extra-recipe-{number}", "description": "Extra description", "instructions": "Extra instructions"}


class TestRecipeCollection:

    RESOURCE_URL = "/api/recipes/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 3
        for item in body:
            assert "name" in item
            assert "description" in item
            assert "instructions" in item

    def test_post_valid_request(self, client):
        valid = _get_recipe_json()
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.headers["Location"].endswith(self.RESOURCE_URL + valid["name"] + "/")
        resp = client.get(resp.headers["Location"])
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["name"] == "extra-recipe-1"

    def test_wrong_mediatype(self, client):
        valid = _get_recipe_json()
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

    def test_post_missing_field(self, client):
        valid = _get_recipe_json()
        valid.pop("instructions")
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_post_name_conflict(self, client):
        valid = _get_recipe_json()
        valid["name"] = "test-recipe-1"
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409


class TestRecipeItem:

    RESOURCE_URL = "/api/recipes/1/"
    INVALID_URL = "/api/recipes/10086/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["name"] == "test-recipe-1"
        assert "ingredients" in body

    def test_get_not_found(self, client):
        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_put_valid_request(self, client):
        valid = _get_recipe_json()
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

    def test_wrong_mediatype(self, client):
        valid = _get_recipe_json()
        resp = client.put(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

    def test_put_missing_field(self, client):
        valid = _get_recipe_json()
        valid.pop("instructions")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_put_name_conflict(self, client):
        valid = _get_recipe_json()
        valid["name"] = "test-recipe-2"
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409

    def test_delete(self, client):
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 404


class TestRecipeIngredient:

    RESOURCE_URL = "/api/recipes/1/ingredients/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert isinstance(body, list)
        assert len(body) == 1
        assert "name" in body[0]

    def test_post_valid_request(self, client):
        valid = {"name": "extra-ingredient"}
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        resp = client.get(self.RESOURCE_URL)
        body = json.loads(resp.data)
        assert any(i["name"] == "extra-ingredient" for i in body)

    def test_post_wrong_mediatype(self, client):
        valid = {"name": "extra-ingredient"}
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
        assert any(r["name"] == "test-recipe-1" for r in body)

    def test_delete_save(self, client):
        client.post(self.COLLECTION_URL, json={"recipe_id": 1})
        resp = client.delete(self.ITEM_URL + "1/")
        assert resp.status_code == 204
        resp = client.get(self.COLLECTION_URL)
        body = json.loads(resp.data)
        assert all(r["name"] != "test-recipe-1" for r in body)
