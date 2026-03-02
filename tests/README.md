# DBMS API Functional Testing Suite

This document outlines the functional testing suite for the DBMS Recipe RESTful API, including dependencies, execution instructions.

## 1. Dependencies (External Libraries)

To execute the test suite successfully, the following Python libraries must be installed in your virtual environment:

* **pytest** (`>=7.0.0`): The core testing framework used to write and execute the test cases.
* **pytest-cov** (`>=4.0.0`): A pytest plugin used to measure and generate code coverage reports.
* **Flask** (`>=3.0.0`): Provides the `FlaskClient` used to simulate HTTP requests to the application.
* **Werkzeug** (`>=3.0.0`): Used for managing custom HTTP test headers (`Headers`) and password hashing during dummy data generation.

*You can install the testing dependencies using:*
`pip install pytest pytest-cov`

## 2. Instructions: How to Run the Tests

The test suite is fully automated and uses an isolated, in-memory SQLite database (`tempfile.mkstemp()`). This ensures that your production/development database is never affected by the tests.

Make sure your virtual environment is activated and you are located in the root directory of the project.

**Run the full test suite with coverage report:**
```bash
pytest tests/ -v --cov=dbms --cov-report=term-missing
```
tests/: Tells pytest to discover and run all tests located in the tests directory.

-v: (Verbose mode) Prints the name of every single test case and its PASS/FAIL status clearly in the terminal.

--cov=dbms: Instructs the coverage tool to measure exactly how much of the dbms application code is executed during the tests.

--cov-report=term-missing: Displays a detailed table in the terminal showing the exact line numbers of any code that was not covered by the tests.

## 3. Main Errors Detected

#### Routing Converter Interception (404 vs 204 error): 
While testing the `DELETE /api/users/{id}/saves/{recipe_id}/` endpoint for a non-existent save, the API returned a 404 Not Found instead of the expected 204 No Content.

#### Authentication Header Overwriting: 
When testing 403 Forbidden access (trying to modify User 1's resources using User 2's API key), the API unexpectedly returned 401 Unauthorized. 

#### Unhandled Database Integrity Constraints: 
The tests highlighted a vulnerability in the `PUT /api/users/{id}/` endpoint. When a user attempted to update their username to one that already belonged to someone else, the server crashed with a 500 Internal Server Error due to a SQLite UNIQUE constraint violation. 