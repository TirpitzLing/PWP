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

The **Daily Bowl Management System(DBMS)** is a **RESTful API** built with **Flask** and **SQLAlchemy**. It is designed to manage users, ingredients, and recipes, allowing users to create, save their favorite recipes, and track nutritional information.

```text
.
├── dbms/                 # Main application package
│   ├── api.py            # Main API routing and setup
│   ├── auth.py           # Authentication logic
│   ├── cli.py            # Custom CLI commands
│   ├── models.py         # SQLAlchemy ORM models
│   ├── resources/        # API route handlers (endpoints)
│   └── static/schema/    # Swagger UI OpenAPI specification
├── instance/             # Local database storage (dbms.db)
├── tests/                # Unit and API tests
├── pyproject.toml        # Project metadata and build configuration
└── requirements.txt      # Project dependencies
```


# 1. Dependencies (External Libraries)

The project uses **Python 3.10** and relies on several external libraries. The complete list with exact versions is pinned in the `requirements.txt` file.

The core dependencies include:

- **Flask** – Web framework used to manage the application context
- **Flask-SQLAlchemy** – Flask extension for SQLAlchemy ORM integration
- **SQLAlchemy** – ORM for database interaction

Other libraries used:

- **API & Routing:** `Flask-RESTful` (0.3.10), `Werkzeug` (3.1.5)
- **Documentation:** `flask-swagger-ui` (4.11.1) to serve the interactive Swagger/OpenAPI documentation
- **Utilities:** `click` (8.3.1) for CLI commands, `Flask-Caching` (2.3.1) & `cachelib` (0.13.0) for API caching
- **Development & Testing:** `pytest` (9.0.2) for unit testing and `flake8` for code linting

# 2. How to Setup the Framework

To install the dependencies and set up the framework safely, it's highly recommended that you use a virtual environment. The Python version we're using is **Python 3.10**.

Here are 2 tutorials about how to create a virtual environment for Python. You can either use `venv` or `conda`:

1. https://docs.python.org/3/library/venv.html
2. https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

**Step 1: Create and activate a virtual environment**

Navigate to the root directory of the project, then run:

* **macOS/Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
* **Windows:**
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
**Step 2: Install dependencies**

After the virtual environment is set up and activated, run the following command under this directory to install all required packages:

```bash
pip install -r requirements.txt
```

### external libraries and resources:

- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
- [SQLite Official Documentation](https://www.sqlite.org/docs.html)

# 3. How to Populate and Setup the Database

Since we use **SQLite** as the built-in database engine, no external database server installation (like MySQL or PostgreSQL) is required. The database schema is managed via SQLAlchemy, and the database file (`dbms.db`) will be automatically generated in the `instance/` folder.

We have created custom Click commands to make initialization and population easy.

**Step 1: Set the Flask application environment variable**
Before running Flask commands, you need to tell the CLI where your application lives. Run the command appropriate for your operating system:

* **macOS/Linux:**
  ```bash
  export FLASK_APP=dbms
  ```
* **Windows:**
  ```bash
  set FLASK_APP=dbms
  ```  
**Step 2: Initialize the database**

Run the custom CLI command to create the database and all necessary tables:

```bash
flask init-db
```
**Step 3: Populate the database with sample data**

To add sample data to the database, run the following command:

```bash
flask populate-db
```
This will insert predefined users, ingredients, and recipes into the database for testing and development purposes.

**Important:** When you run the `populate-db` command, the terminal will output an Admin API Key. Copy this key, as you will need it to authenticate requests when testing the API!
