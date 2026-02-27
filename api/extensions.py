from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask_caching import Cache

db = SQLAlchemy()
api = Api()
cache = Cache()