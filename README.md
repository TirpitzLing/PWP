# PWP SPRING 2026

# Daily Bowl Management System (DBMS)

# Group information

- Student 1. Anqi Zhou -- azhou25@student.oulu.fi
- Student 2. Junxuan Ling -- jling25@student.oulu.fi
- Student 3. Tianyi Liu -- tliu25@student.oulu.fi

**Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment**

# To run the static code analysis

Run the following command in your terminal:

```bash
flake8 .
```

# Overview

This folder contains the database script and instance for **Daily Bowl Management System**. The database schema is implemented using SQLAlchemy ORM within Flask, and the database file is stored in `./instance/dbms.db`

```text
database/
├── dbcreation.py        # Database models and ORM setup
├── requirements.txt     # Python dependencies
├── instance/
│   └── dbms.db          # SQLite database file
├── README.md            # This file
```

# 1. Dependencies

The project uses the following Python libraries:

- **Flask** – Web framework used to manage the application context
- **Flask-SQLAlchemy** – Flask extension for SQLAlchemy ORM integration
- **SQLAlchemy** – ORM for database interaction

## Installation

To install these dependencies, it's highly recommended that you use a virtual environment. The Python version we're using is Python 3.10.

Here are 2 tutorials about how to create a virtual environment for Python. You can either use venv or conda:

1. https://docs.python.org/3/library/venv.html
2. https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

After the virtual environment is set up, run the following command under the this directory (`database/`) to install all required packages:

```bash
pip install -r requirements.txt
```

# 2. Database Type and Version

We use SQLite as the database engine for data persistence. **SQLite 3.x** is built into the standard Python library, so no separate installation is required.

## 3. Database Framework Setup

Since the database is defined and managed using SQLAlchemy ORM within Flask, setting up the framework means installing the necessary Python bindings.

1. Activate your virtual environment.
2. The `requirements.txt` installation step has already installed SQLAlchemy.
3. No external server configuration (such as MySQL) is needed.

**Models** are defined as Python classes: `User`, `Ingredient`, `Recipe`, `RecipeIngredient`, `Save`.

**Relationships** are represented using `db.relationship()` and foreign keys using `db.ForeignKey()`.

### external libraries and resources:

- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
- [SQLite Official Documentation](https://www.sqlite.org/docs.html)

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

This script generates a file named `[dbms.db]` in `database/instance/` directory.

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

```bash
# Run the app
export FLASK_APP=dbms/app.py
flask run

# Run the tests
pytest tests/

```
