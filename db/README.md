# Dependencies

The Python dependencies include: 

```
WHAT
```

To install these dependencies, it's highly recommended that you use a virtual environment. The Python version we're using is ==What==. 

Here are 2 tutorials about how to create a virtual environment for Python. You can either use venv or conda:

1. https://docs.python.org/3/library/venv.html
2. https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

After the virtual environment is set up, run the following command under the root directory to install all required packages:

```bash
pip install -r requirements.txt
```

# Database version

We use SQLite as the database engine for data persistence. SQLite3 is built into the standard Python library, so no separate installation is required.

# How to set up the database framework

Since we use SQLite with an ORM library, setting up the framework means installing the necessary Python bindings.

1. Activated your virtual environment.
2. The `requirements.txt` installation step has already installed SQLAlchemy.
3. No external server configuration (such as MySQL) is needed.

# How to set up the database

To initialize the database and create the required table schemas, run the initialization script provided in the repository.

```

```

This script generates a file named `[app.db]` in `./instance/` directory.

# How to populate the database

To test the application with data, we have provided a script that fill the database with sample recipes. (We extracted recipes from existing websites and used AI tools to generate realistic fake data to populate the models)

To run the population script:

```
```

