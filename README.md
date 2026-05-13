# PWP SPRING 2026

# Daily Bowl Management System (DBMS)

# Group information

- Student 1. Anqi Zhou -- azhou25@student.oulu.fi
- Student 2. Junxuan Ling -- jling25@student.oulu.fi
- Student 3. Tianyi Liu -- tliu25@student.oulu.fi

**Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment**

# Overview

The **Daily Bowl Management System (DBMS)** is a **RESTful API** built with **Flask** and **SQLAlchemy**. It is designed to manage users, ingredients, and recipes, allowing users to create, save their favorite recipes, and track nutritional information.

```text
.
├── dbms/                 # Main application package
│   ├── api.py            # Main API routing and setup
│   ├── auth.py           # Authentication logic
│   ├── cli.py            # Custom CLI commands
│   ├── models.py         # SQLAlchemy ORM models
│   ├── resources/        # API route handlers (endpoints)
│   ├── static/schema/    # Swagger UI OpenAPI specification
│   └── utils.py          # Utility functions
├── deployment/           # Deployment & configuration scripts
│   ├── auto_deploy.bat   # Script for auto update code and re-deploy on Windows
│   ├── generate_cert.bat # Script for generating SSL certificates on Windows
│   └── generate_cert.sh  # Script for generating SSL certificates on MacOS/Linux
├── docker-compose.yml    # Docker Compose configuration for deployment
├── Dockerfile            # Docker image configuration
├── instance/             # Local database storage (dbms.db) and cache
├── nginx/                # NGINX configuration and SSL certificates
├── tests/                # Unit and API tests
├── pyproject.toml        # Project metadata and build configuration
└── requirements.txt      # Project dependencies
```

# 1. Prerequisites & Dependencies (External Libraries)

### Required Software

To set up and maintain the environment, the following software must be installed on the host machine:

- **Docker & Docker Compose**: For containerized deployment and environment management.
- **OpenSSL**: Essential for creating and maintaining the SSL certificates required for HTTPS.
- **Git**: Required for version control and utilizing the automated deployment scripts.
- **Python 3.10**: Required only for manual setup (Option B).

### External Libraries

The complete list of Python dependencies is pinned in `requirements.txt`. Core libraries include:

- **Flask** – Web framework used to manage the application context
- **Flask-SQLAlchemy** – Flask extension for SQLAlchemy ORM integration
- **SQLAlchemy** – ORM for database interaction

Other libraries used:

- **API & Routing:** `Flask-RESTful` (0.3.10), `Werkzeug` (3.1.5)
- **Documentation:** `flask-swagger-ui` (4.11.1) to serve the interactive Swagger/OpenAPI documentation
- **Utilities:** `click` (8.3.1) for CLI commands, `Flask-Caching` (2.3.1) & `cachelib` (0.13.0) for API caching
- **Development & Testing:** `pytest` (9.0.2) for unit testing and `flake8` for code linting
- **Production Server:** `gunicorn` as WSGI HTTP server, and `nginx` as a reverse proxy.

### Resources:

- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
- [SQLite Official Documentation](https://www.sqlite.org/docs.html)

# 2. How to Setup, Run and Deploy the Application

You can choose to run this API using either **Docker (Option A)** or a **Manual Python Virtual Environment (Option B)**.

## Option A: Run and Deploy using Docker (Recommended)

Using Docker simplifies the setup process by containerizing the application and its environment. Ensure you have Docker and Docker Compose installed. You can download Docker from [here](https://www.docker.com/) and with Docker service running, you can follow the instructions below.

**Step 1: Generate SSL Certificates**

Before running Docker, you must generate self-signed SSL certificates for NGINX. Navigate to the root directory and run the provided script:

- **Windows:** Double-click `generate_cert.bat` or run it in CMD.
- **macOS/Linux: Enter project root directory** and run `bash generate_cert.sh`.

_(This creates `server.crt` and `server.key` inside the `nginx/certs/` folder)._

**Step 2: Configure Port Forwarding on Deployment Server**

For the API server to be accessible externally, you must obtain a public IP address from your hosting provider. As an alternative, the application can be deployed on a personal computer configured with public IP access. 

Here is an example on how to deploy the Docker container on a Windows operating system using a public IP:

 - **Port Forwarding(Router Settings)**: 
   - **Find your Local IP**: Open Command Prompt (cmd) on your Windows PC and type `ipconfig`. Note down your IPv4 Address (e.g., 192.168.1.x).
   - **Access Router Admin Panel**: Open a web browser and enter your router's default gateway address (usually 192.168.1.1 or 192.168.0.1), this might varies on your router brands and settings. Log in with your admin credentials.
   - **Create a Port Forwarding Rule**: Locate the "Port Forwarding" section in your router settings.
   - **Map the Ports**: Add a new rule to forward external traffic to your PC.
     - **Internal IP**: Enter your Windows PC's IPv4 address.
     - **Internal/External Port**: Enter the ports for your configuration. In our setup, set the External Port to 443 and the Internal Port to 10013 (the port the Docker container listens to). Note: Using standard external ports (like 80 for HTTP or 443 for HTTPS) allows access via the URL without appending a port number. If a custom port is used, it must be included in the domain address.
     - **Protocol**: Select TCP.
   - **Save and apply the changes.**
 - **Enable ports in firewall settings(Windows Defender Firewall)**:
   - Open the Start menu, search for Windows Defender Firewall, and open it.
   - Click on Advanced settings on the left panel to open "Windows Defender Firewall with Advanced Security".
   - Select Inbound Rules from the left pane, then click New Rule... on the right panel.
   - **Rule Type**: Select Port and click Next.
   - **Protocol and Ports**: Select TCP and specific local ports. Enter the port number your backend is running on (e.g., 80, 443, 10013), then click Next.
   - **Action**: Select Allow the connection and click Next.
   - **Profile**: Leave all profiles (Domain, Private, Public) checked, or select according to your network security preference.
   - **Name**: Give your rule a recognizable name (e.g., Docker Backend API) and **click Finis**h.

Note: If your public IP is dynamic, it is highly recommended to set up a DDNS (Dynamic DNS) service, to bind your changing public IP to a fixed domain name.



**Step 3: Build and Start Containers**

Navigate to the root directory of the project and run:

```bash
docker compose up
```

This will build the image, starts the container (`dbms-api` and `nginx`), and map the API to your machine. Visit `http://127.0.0.1:10013/api/docs/` for the documentation.

### Environment Configuration Check

To verify the environment is properly configured, perform the following tests:

1.  **Check Container Status**: Run `docker compose ps`. Both services should be in the `Up` state.
2.  **Verify HTTPS Connectivity**:
    - **Windows (PowerShell):** `curl.exe -k -I https://localhost:10013/api/docs/`
    - **Linux/Mac:** `curl -k -I https://localhost:10013/api/docs/`
      _(Expected: `HTTP/1.1 200 OK`)_
3.  **Database Check**: Confirm that the `instance/dbms.db` file is present in the project directory after startup.

**Step 4: Initialize and Populate the Database**

Initialization is handled automatically by the Docker entrypoint. To manually reset or add sample data, run:

```bash
docker compose exec dbms-api flask init-db
docker compose exec dbms-api flask populate-db
```

> [!NOTE]
>
> **Initialize and populate the database**
>
> (Initialization and population command has already been included in the docker-compose file. So there is **no need** to run these commands manually!)
>
> Since we use **SQLite** as the built-in database engine, no external database server installation is required. We have created custom Click commands to make initialization and population easy.

After the command `populate-db` is executed, the terminal will output an Admin API Key. Copy this key, as you will need it to authenticate requests when testing the API!

### Option A.1: Automated Deployment Scripts (Windows Cloud Server)

- **Automated Deployment**: Use `scripts/autodeploy.bat` (Windows) for a CI/CD loop that pulls from GitHub and restarts containers every 15 minutes. _(Note: If utilizing these scripts on a new server, ensure the absolute directory path `cd /d X:\FILE_PATH_TO_THE_PROJECT` inside the `.bat` files is updated to match your deployment environment)._
- **Firewall Configuration**: Ensure **TCP port 10013** is open in your Windows Firewall and (if have) router's port-forwarding settings to allow external access.
- **TLS Protocol**: The NGINX proxy is configured to use **TLS 1.2 and 1.3** to ensure secure data transmission.

To facilitate a smooth CI/CD pipeline on Windows Cloud Server, we have implemented a custom batch script for automated deployment:

## Option B: Manual Setup Locally (Virtual Environment)

To install the dependencies and set up the framework safely, it's highly recommended that you use a virtual environment. The Python version we're using is **Python 3.10**.

Here are 2 tutorials about how to create a virtual environment for Python. You can either use `venv` or `conda`:

1. https://docs.python.org/3/library/venv.html
2. https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

Here we provide a guide using venv.

**Step 1: Create and activate a virtual environment**

Navigate to the root directory of the project, then run:

- **macOS/Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **Windows:**
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

- **macOS/Linux:**
  ```bash
  export FLASK_APP=dbms
  ```
- **Windows:**
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

- If using **Docker (Option A)**: http://localhost:10013/
- If using **Manual Setup (Option B)**: http://localhost:5000/

**Interactive API Documentation (Swagger UI):**

We use Swagger UI for easy endpoint exploration. To view all available routes (like `/api/users/` or `/api/recipes/`), check required parameters, and test the API directly from your browser, navigate to:

- **Cloud Production Deployment (Docker + NGINX):**

  > **https://<your.host.ip>/api/docs/**
  > _(Note: Since we use self-signed certificates, please click "Advanced" -> "Proceed/Continue" if your browser shows a security warning.)_

- **Local Manual Setup (Flask dev server):**
  > **http://localhost:5000/api/docs/**

(This interface is automatically generated by reading `dbms/static/schema/swagger.yaml` file).

# 4. How to Run the Test

To verify that the API functions correctly, we use `pytest`. Ensure your virtual environment is activated, then run:

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=dbms --cov-report=term-missing
```

More information about testing, please refer to this document: [Readme before test](tests/README.md)

# 5. Live Demo

- Docs: https://dbms.ddns.net:10013/api/docs/
- Base Path: https://dbms.ddns.net:10013/api/

# 6. Client Configuration (env.json)

The Flutter client application loads its API connection settings from an `env.json` file.

### File Location

Place `env.json` at the **root of the Flutter project**:

```
daily_bowl/
├── env.json          ← here
├── lib/
├── pubspec.yaml
└── ...
```

The file is registered as a Flutter asset in `pubspec.yaml` (line 38):

```yaml
flutter:
  assets:
    - env.json
```

### File Structure

```json
{
    "SUPABASE_URL": "https://dummy.supabase.co",
    "SUPABASE_ANON_KEY": "dummykey.updateyourkkey.here",
    "DBMS_BASE_URL": "https://dbms.ddns.net:10013/api",
    "DBMS_API_KEY": "admin-secret-key"
}
```

### Field Descriptions

| Field | Required | Description |
|---|---|---|
| `DBMS_BASE_URL` | **Yes** | Base URL of the DBMS API, including the `/api` prefix. Format: `https://<host>:<port>/api`. Change this to match your deployment address. |
| `DBMS_API_KEY` | **Yes** | Default API key used as a fallback when no user-specific key is stored. After running `flask populate-db`, copy the admin key printed in the terminal here. |
| `SUPABASE_URL` | No | Placeholder — not used by DBMS. Retained for template compatibility. |
| `SUPABASE_ANON_KEY` | No | Placeholder — not used by DBMS. Retained for template compatibility. |

### Configuration Examples

**Local development (Flask dev server):**
```json
"DBMS_BASE_URL": "http://localhost:5000/api"
```

**Production with Docker on a cloud server:**
```json
"DBMS_BASE_URL": "https://dbms.ddns.net:10013/api"
```

**Testing on the same machine with Docker:**
```json
"DBMS_BASE_URL": "https://localhost:10013/api"
```

> After changing `env.json`, rebuild the Flutter app with `flutter clean && flutter pub get && flutter run`.

# 7. Auxiliary Service — Nutrition Report Generator

The auxiliary service (`report_worker/`) is a standalone Flask application that
generates nutrition report PDFs.  It communicates with the DBMS API **exclusively
via HTTP** — it never accesses the DBMS database directly.

## Architecture

```
Client → POST /aux/reports/ → Nginx → Aux Service (Flask, port 5000)
                                           │
                                     Publishes to RabbitMQ
                                           │
                                     Worker thread picks up job
                                           │
                                     GET /api/recipes/{id}/nutrition/  (from DBMS API)
                                           │
                                     Generates PDF → stored locally
                                           │
Client ← GET /aux/reports/{id}/download/ ← PDF
```

## Prerequisites

- Python 3.10+
- The DBMS API must be running and reachable
- RabbitMQ must be running (provided by Docker Compose)

## Dependencies

Defined in `report_worker/requirements.txt`:

| Package | Purpose |
|---|---|
| `flask` | HTTP API framework |
| `gunicorn` | Production WSGI server |
| `flask-cors` | Cross-origin support |
| `flask-swagger-ui` | Interactive API docs at `/aux/docs/` |
| `pika` | RabbitMQ client |
| `requests` | HTTP client for calling DBMS API |
| `pyyaml` | Swagger YAML parsing |

## How to Setup & Run

### Option A: Docker Compose (Recommended)

The service is included in `docker-compose.yml` as `aux-service`:

```bash
docker compose up -d --build aux-service
```

It is automatically wired up via Nginx — the `/aux/` URL prefix routes to the
aux service.  No manual configuration needed.

Environment variables (set in `docker-compose.yml`):

| Variable | Purpose | Default |
|---|---|---|
| `RABBITMQ_URL` | RabbitMQ connection string | `amqp://guest:guest@rabbitmq:5672/%2F` |
| `DBMS_API_BASE_URL` | DBMS API base URL | `http://dbms-api:8000/api` |
| `DBMS_API_KEY` | API key for DBMS API calls | `admin-secret-key` |

### Option B: Manual Setup

```bash
cd report_worker
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Start with gunicorn (worker thread starts automatically)
gunicorn -w 1 --threads 4 -b 0.0.0.0:5000 app:create_app
```

## API Endpoints

All paths below are prefixed with `/aux` by Nginx.  The aux service's Flask
routes are at `/reports/…` internally; clients always use the `/aux` prefix.

Full interactive documentation: `https://<host>:10013/aux/docs/`

| Method | Client-facing URL | Description |
|---|---|---|
| `POST` | `/aux/reports/` | Create a report job. Body: `{"recipe_ids": [1,2,3]}`. Add `?wait=true` to block until done. |
| `GET` | `/aux/reports/{id}/` | Get job status and nutrition data |
| `GET` | `/aux/reports/{id}/download/` | Download the generated PDF |

## Connection to the Main API

The aux service calls the DBMS API at:

```
GET /api/recipes/{id}/           — fetch recipe title
GET /api/recipes/{id}/nutrition/ — fetch nutrition data
```

It authenticates with the `dbms-api-key` header using the admin API key
(`admin-secret-key` by default, configured via `DBMS_API_KEY`).

## Running Tests

```bash
cd report_worker
pip install pytest pytest-cov
pytest tests/ -v --cov=. --cov-report=term-missing
```

## Linting

```bash
pip install pylint
pylint report_worker/
```

# 8. Deployment Configuration Tests

To verify that the production environment is properly configured, isolated, and functional, please run the following tests sequentially. **Ensure you are in the project root directory before running any commands.**

### Test 1: Container & Process Verification

Ensure all isolated environments are running and managed by Docker.

**Command:** 
```bash
  docker compose ps
```
**Expected Result:** `nginx` and `dbms-api` containers should display a status of `Up` and `Up (healthy)`.

### Test 2: Network Configuration Test

Verify that Nginx is correctly terminating SSL, exposing port 10013, and routing traffic to the internal Gunicorn server.

- **Command (macOS/Linux):**

```bash
  curl -k -I https://localhost:10013/api/docs/
```

- **Command (Windows PowerShell):**

```bash
  curl.exe -k -I https://localhost:10013/api/docs/
```

**Expected Result:** The terminal should return `HTTP/1.1 200 OK` and show `Server: nginx`. This proves the external-to-internal port mapping (10013 -> 443 -> 8000) is successful.

### Test 3: Database Volume Verification

Check if the SQLite database is properly persisting data on the host machine, independent of the container lifecycle.

- **Command (macOS/Linux):**

```bash
  ls -l instance/dbms.db
```
- **Command (Windows CMD):**

```bash
  dir instance
```


**Expected Result:** The file should exist and have a file size greater than 0 bytes after running the `populate-db` command.

### Test 4: API Tests

Run the automated integration and unit tests to ensure the Flask application logic and database ORM are functioning properly within the configured environment.
**Command:**

```bash
  docker compose exec dbms-api pytest tests/ -v
```

**Expected Result:** All tests should pass (green output), proving that the application logic runs perfectly inside the containerized Python 3.10 runtime.
