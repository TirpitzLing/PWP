# Overview


This folder contains the database script and instance for **Daily Bowl Management System**. The database schema is implemented using SQLAlchemy ORM with Flask, and the database file is stored in instance/dbms.db

```text
database-ddl2/
│
├── dbcreation.py        # Database models and ORM setup
├── requirements.txt     # Python dependencies
├── instance/
│   └── dbms.db          # SQLite database file
├── README.md            # This file
```

# 1. Dependencies


The project uses the following Python libraries:

-**Flask** – Web framework used to manage the application context
-**Flask-SQLAlchemy** – Flask extension for SQLAlchemy ORM integration
-**SQLAlchemy** – ORM for database interaction

## Installation

It is recommended to use a Python virtual environment. 

To install all dependencies:

```bash
pip install -r requirements.txt
```

# 2. Database Type and Version


**Database:** SQLite 

**Version Tested:** SQLite 3.x (default bundled with Python)


## 3. Database Framework Setup


The database is defined and managed using SQLAlchemy ORM within Flask.

**Models** are defined as Python classes: `User`, `Ingredient`, `Recipe`, `RecipeIngredient`, `Save`.

**Relationships** are represented using `db.relationship()` and foreign keys using `db.ForeignKey()`.

### external libraries and resources:
* [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/)
* [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
* [SQLite Official Documentation](https://www.sqlite.org/docs.html)


# 4. setup and populate


## Database Creation
To create the database and tables, open a Python terminal and run the following commands:

```python
from dbcreation import db, app
ctx = app.app_context()
ctx.push()
db.create_all()
ctx.pop()
```

## Populating the Database
To populate the database with initial data, you can create a script or use the Python terminal. For example, to add a new user: 

```python
from dbcreation import db, app
from dbcreation import User # Import the User model
from datetime import datetime
import json
ctx = app.app_context()
ctx.push()
new_user = User(
    username="XXX",
    pwd="XXXXXXXXX",
    email="XXXXXXXXX",
    created_at=datetime.utcnow(),
    allergies=json.dumps(["XXX"])
)
db.session.add(new_user)
db.session.commit()
ctx.pop()
```

For other tables sample data can be added similarly, and for more complex data, you can create a separate script to insert multiple records at once.
