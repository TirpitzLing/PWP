import importlib
import os
flask_app = os.environ.get("FLASK_APP")
app = importlib.import_module(flask_app)


with app.app.app_context():

    app.db.create_all()
        
    app.db.session.commit()

