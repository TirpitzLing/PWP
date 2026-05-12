"""
Initialize the Daily Bowl Management System API.

this module initializes the Flask app, extensions, blueprints, and configuration.
"""

import os
from flask import Flask, jsonify
from sqlalchemy.engine import Engine
from sqlalchemy import event
from werkzeug.exceptions import HTTPException
from flask_swagger_ui import get_swaggerui_blueprint

from dbms.extensions import db, cache
from dbms.converters import (
    RecipeConverter,
    UserConverter,
    IngredientConverter,
    SaveConverter,
)
from dbms import models
from dbms import cli as clipy
from dbms.api import api_bp


def create_app(test_config=None):
    """
    Create and configure an instance of the Flask application.
    As recommended in the layout section
    """
    # init flask
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        db_path = os.path.join(app.instance_path, "dbms.db")
        # cache config comes from lovelace material
        app.config.from_mapping(
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            CACHE_TYPE="FileSystemCache",
            CACHE_DIR=os.path.join(app.instance_path, "cache"),
            WORKER_API_KEY=os.getenv(
                "WORKER_API_KEY", "worker-secret-key-change-me"
            ),
        )
    else:
        app.config.from_mapping(test_config)

    # instance dir
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # init extensions
    db.init_app(app)
    cache.init_app(app)

    # activate foreign key(for sqlite)
    # ref: https://stackoverflow.com/questions/13712381/how-to-turn-on-pragma-foreign-keys-on-in-sqlalchemy-migration-script-or-conf
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # swagger
    # ref: AI guided
    swagger_url = "/api/docs"
    api_url = "/static/schema/swagger.yaml"
    swaggerui_blueprint = get_swaggerui_blueprint(
        swagger_url,
        api_url,
        config={"app_name": "DBMS Recipe API"},
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix=swagger_url)

    # url map
    app.url_map.converters["recipe"] = RecipeConverter
    app.url_map.converters["user"] = UserConverter
    app.url_map.converters["ingredient"] = IngredientConverter
    app.url_map.converters["save"] = SaveConverter

    # ref: lovelace Flask API Project Layout
    # CLI cmd
    app.cli.add_command(clipy.init_db_command)
    app.cli.add_command(clipy.populate_db_command)

    # register blueprint (common prefix)
    app.register_blueprint(api_bp)

    @app.route('/admin')
    def admin_dashboard():
        from flask import redirect
        return redirect('/static/admin/index.html')

    # intercept all http exceptions and return in a json format
    # ref: https://flask.palletsprojects.com/en/stable/errorhandling/
    @app.errorhandler(HTTPException)
    def handle_exception(e):
        return (
            jsonify(
                {
                    "code": e.code,
                    "name": e.name,
                    "description": e.description,
                }
            ),
            e.code,
        )

    return app
