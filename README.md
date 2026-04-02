# PWP SPRING 2026

# Daily Bowl Management System (DBMS)

# Group information

- Student 1. Anqi Zhou -- azhou25@student.oulu.fi
- Student 2. Junxuan Ling -- jling25@student.oulu.fi
- Student 3. Tianyi Liu -- tliu25@student.oulu.fi

**Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment**


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
├── nginx/                # NGINX configuration and SSL certificates
├── scripts/              # Automated deployment scripts
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
- **Production Server:** `gunicorn` as WSGI HTTP server, and `nginx` as a reverse proxy.

### External libraries and resources:

- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
- [SQLite Official Documentation](https://www.sqlite.org/docs.html)


# 2. How to Setup and Run the Application

You can choose to run this API using either **Docker (Option A)** or a **Manual Python Virtual Environment (Option B)**.


## Option A: Run using Docker (Recommended)

Using Docker simplifies the setup process by containerizing the application and its environment. Ensure you have Docker and Docker Compose installed. You can download Docker from [here](https://www.docker.com/) and with Docker service running, you can follow the instructions below.

**Step 1: Generate SSL Certificates**
Before running Docker, you must generate the self-signed SSL certificates for NGINX. Navigate to the root directory and run the provided script:
- **Windows:** Double-click `generate_cert.bat` or run it in CMD.
- **macOS/Linux:** Run `bash generate_cert.sh`.

*(This will create `server.crt` and `server.key` inside the `nginx/certs/` folder).*


**Step 2: Build and start the app in container**

Navigate to the root directory of the project and run:

```bash
docker compose up
```

This will build the image, start the container (dbms-api and nginx), and map the API to your machine. Visit `http://127.0.0.1:8080/api/docs` and you can already see the documentation.

> [!NOTE] 
> 
> **Initialize and populate the database**
> 
> (Initialization and population command has already been included in the docker-compose file. So there is **no need** to run these commands manually!)
> 
> Since we use **SQLite** as the built-in database engine, no external database server installation is required. We have created custom Click commands to make initialization and population easy.
> 
> Run these commands inside the running container to set up the database:
> 
> ```bash
> docker compose exec dbms-api flask init-db
> docker compose exec dbms-api flask populate-db
> ```

After the command `populate-db` is executed, the terminal will output an Admin API Key. Copy this key, as you will need it to authenticate requests when testing the API!

### Option A.1: Automated Deployment Scripts (Windows Cloud Server)

To facilitate a smooth CI/CD pipeline on our Windows Cloud Server, we have implemented two custom batch scripts for automated deployment:

- **`start_server.bat`**: A one-click hosting script that automatically navigates to the project directory, cleanly brings down any existing containers, and rebuilds/starts the Docker environment in detached mode. It provides a visual confirmation when the server is successfully running.
- **`autodeploy.bat`**: A watchdog script that enables continuous deployment. It runs a continuous loop that fetches updates from the remote `main` branch. If it detects that the local code is behind the remote repository, it automatically pulls the latest code, rebuilds the Docker containers, and restarts the services. It checks for updates every 15 minutes to ensure the production environment stays up to date without manual intervention.

*(Note: If utilizing these scripts on a new server, ensure the absolute directory path `cd /d F:\Coding\Projects\pwp\PWP` inside the `.bat` files is updated to match your deployment environment).*

## Option B: Manual Setup (Virtual Environment)

To install the dependencies and set up the framework safely, it's highly recommended that you use a virtual environment. The Python version we're using is **Python 3.10**.

Here are 2 tutorials about how to create a virtual environment for Python. You can either use `venv` or `conda`:

1. https://docs.python.org/3/library/venv.html
2. https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

Here we provide a guide using venv.

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

**Step 3: Set the Flask application environment variable**

Before running Flask commands, you need to tell the CLI where your application lives. Run the command appropriate for your operating system:

* **macOS/Linux:**
  ```bash
  export FLASK_APP=dbms
  ```
* **Windows:**
  ```bash
  set FLASK_APP=dbms
  ```

**Step 4: Initialize and populate the database**

Run the custom CLI command to create the database and all necessary tables:

```bash
flask init-db
```

To add sample data to the database, run the following command:

```bash
flask populate-db
```

This will insert predefined users, ingredients, and recipes into the database for testing and development purposes.

**Important:** When you run the `populate-db` command, the terminal will output an Admin API Key. Copy this key, as you will need it to authenticate requests when testing the API!

**Step 5: Start the server**

Start the RESTful API by running the following command:

```bash
flask run
```

This will boot up the Flask application, connect to the database in your `instance/` folder, and start listening for incoming HTTP requests.

# 3. The URL to access the API

Once the backend server is running, your RESTful API is accessible locally.

**Main Entry Point (Base URL):**

The base path to your application depends on how you started it:

- If using **Docker (Option A)**: http://localhost:8080/
- If using **Manual Setup (Option B)**: http://localhost:5000/

**Interactive API Documentation (Swagger UI):**

We use Swagger UI for easy endpoint exploration. To view all available routes (like `/api/users/` or `/api/recipes/`), check required parameters, and test the API directly from your browser, navigate to:

- **Cloud Production Deployment (Docker + NGINX):**
  > **https://edvic.ddns.net/api/docs**
  > *(Note: Since we use self-signed certificates, please click "Advanced" -> "Proceed/Continue" if your browser shows a security warning.)*

- **Local Manual Setup (Flask dev server):**
  > **http://localhost:5000/api/docs**

(This interface is automatically generated by reading `dbms/static/schema/swagger.yaml` file).

# 4. How to Run the Test

To verify that the API functions correctly, we use `pytest`. Ensure your virtual environment is activated, then run:

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=dbms --cov-report=term-missing
```

More information about testing, please refer to this document: [Readme before test](tests/README.md)