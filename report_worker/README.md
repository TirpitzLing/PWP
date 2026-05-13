# Nutrition Report Service

A lightweight, asynchronous microservice for generating PDF nutrition reports. This service runs as an independent container and communicates with the main DBMS API via HTTP and RabbitMQ for event-driven job processing.

## Overview

The report service provides three main operations:

- **Create Report** (`POST /reports/`) — Submit recipes for analysis; returns job ID immediately with status `pending`
- **Check Status** (`GET /reports/{job_id}/`) — Poll job progress; returns aggregated nutrition data when `status: "done"`
- **Download PDF** (`GET /reports/{job_id}/download/`) — Download the generated PDF report

### Architecture

- **API Layer** (`app.py`) — Flask REST endpoints served via gunicorn
- **Worker** (`worker.py`) — RabbitMQ consumer; fetches nutrition from DBMS API, generates PDFs
- **Storage** (`storage.py`) — Thread-safe in-memory job tracking (scoped to service lifetime)
- **OpenAPI Docs** — Swagger UI at `/docs/`

---

## Dependencies

### External Libraries

See [`requirements.txt`](./requirements.txt):

| Package | Version | Purpose |
|---------|---------|---------|
| `flask` | 3.1.2 | Web framework |
| `gunicorn` | 23.0.0 | Production WSGI server |
| `flask-cors` | 5.0.1 | Cross-origin resource sharing |
| `flask-swagger-ui` | 4.11.1 | Interactive API documentation |
| `pika` | 1.3.2 | RabbitMQ client |
| `requests` | 2.31.0 | HTTP client for DBMS API calls |
| `pyyaml` | 6.0.2 | YAML parsing (for swagger schema) |

### System Requirements

- **Python 3.10+**
- **RabbitMQ 3.x** (for event broker)
- **DBMS API** (for nutrition endpoint `/api/recipes/{id}/nutrition/`)

---

## Setup & Installation

### Option 1: Docker (Recommended — Production & Development)

The service is designed to run in Docker as part of the full stack.

**Prerequisites:**
- Docker & Docker Compose
- Main DBMS API running

**Build & run via compose:**

```bash
cd /path/to/PWP
docker compose up --build aux-service
```

This will:
1. Build the `aux-service` image from `./report_worker/Dockerfile`
2. Start the Flask API on port 5000 (inside container)
3. Start the RabbitMQ consumer in a background thread
4. Export Swagger UI at `http://localhost/aux/docs` (via nginx)

### Option 2: Local Development (Manual)

**Prerequisites:**
- Python 3.10+
- RabbitMQ running
- DBMS API running

**Setup:**

```bash
cd report_worker

# Create virtual environment (optional)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt


# Run the service
gunicorn -w 1 --threads 4 -b 0.0.0.0:5000 app:create_app()
```

---

## Configuration

The service is configured via **environment variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_URL` | `amqp://guest:guest@rabbitmq:5672/%2F` | RabbitMQ connection URL (amqp format) |
| `DBMS_API_BASE_URL` | `http://dbms-api:8000/api` | Base URL for DBMS API calls (e.g., nutrition endpoint) |
| `DBMS_API_KEY` | *(empty)* | API key for authentication with DBMS API (sent as `dbms-api-key` header) |
| `FLASK_ENV` | `production` | Flask environment (`production` or `development`) |

### In Docker Compose

Environment variables are set in `docker-compose.yml` under `aux-service`:

```yaml
aux-service:
  environment:
    - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/%2F
    - DBMS_API_BASE_URL=http://dbms-api:8000/api
    - DBMS_API_KEY=admin-secret-key
```

### In Local Development

Set variables before running:

```bash
export RABBITMQ_URL="amqp://guest:guest@localhost:5672/%2F"
export DBMS_API_BASE_URL="http://localhost:8000/api"
export DBMS_API_KEY="admin-secret-key"
```

---

## Running the Service

### Via Docker Compose

```bash
# Start all services including aux-service
docker compose up -d

# View logs
docker compose logs -f aux-service

# Stop
docker compose down
```


## Testing

### Unit & Integration Tests

The service includes comprehensive tests in `tests/test_worker.py`.

**Run all tests:**

```bash
cd report_worker

# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

**Test categories:**

- **Storage tests** — Job creation, retrieval, updates
- **Worker tests** — Nutrition calculation, PDF generation, comparison logic
- **API endpoint tests** — Job creation, status polling, download
- **RabbitMQ integration** — Event publishing and consumption (mocked in unit tests)

**Example test run:**

```bash
pytest tests/test_worker.py::test_calculate_totals -v
pytest tests/test_worker.py -k "test_compare" -v
```

### Running Tests with CI/CD

Tests are isolated and don't require external services (RabbitMQ/DBMS mocked). Safe to run in CI pipelines:

```bash
pytest tests/ --tb=short
```

### Test Configuration

Tests use `conftest.py` to:
- Mock RabbitMQ connections
- Reset in-memory storage between tests
- Set default environment variables

No external services required for unit tests.

---

## API Usage Examples

### 1. Create a Report

**Request:**
```bash
curl -X POST http://localhost:5000/reports/ \
  -H "Content-Type: application/json" \
  -d '{"recipe_ids": [1, 2, 3]}'
```

**Response (HTTP 202 Accepted):**
```json
{
  "id": 1,
  "recipe_ids": [1, 2, 3],
  "status": "pending",
  "total_calories": null,
  "total_carbs": null,
  "total_protein": null,
  "total_fat": null,
  "comparison_json": null,
  "pdf_path": null,
  "error_message": null,
  "created_at": "2026-05-13T10:30:00+00:00",
  "finished_at": null
}
```

### 2. Check Job Status

**Request:**
```bash
curl -X GET http://localhost:5000/reports/1/
```

**Response (HTTP 200 OK, when done):**
```json
{
  "id": 1,
  "recipe_ids": [1, 2, 3],
  "status": "done",
  "total_calories": 2500.0,
  "total_carbs": 275.0,
  "total_protein": 150.0,
  "total_fat": 85.0,
  "comparison_json": "{\"calories\": {...}, ...}",
  "pdf_path": "/app/pdfs/report-1.pdf",
  "error_message": null,
  "created_at": "2026-05-13T10:30:00+00:00",
  "finished_at": "2026-05-13T10:35:30+00:00"
}
```

### 3. Download Report

**Request:**
```bash
curl -X GET http://localhost:5000/reports/1/download/ \
  -o report-1.pdf
```

**Response:** PDF file (HTTP 200 OK) or 409 Conflict if not ready

---

## Troubleshooting

### RabbitMQ Connection Failed

**Symptom:** Logs show `[worker] failed to connect to RabbitMQ`

**Solution:**
- Verify `RABBITMQ_URL` is correct and RabbitMQ is running
- Check Docker network connectivity (if using Docker Compose, service names should resolve)
- Ensure `rabbitmq` service is healthy: `docker compose ps rabbitmq`

### DBMS API Unreachable

**Symptom:** Job status is `failed` with error "Failed to fetch nutrition..."

**Solution:**
- Verify `DBMS_API_BASE_URL` points to a running DBMS API
- Check API key: `DBMS_API_KEY` must match the key expected by DBMS API
- Test connectivity: `curl -H "dbms-api-key: <key>" http://dbms-api:8000/api/recipes/1/nutrition/`

### PDF Not Generated

**Symptom:** Status is `done` but `pdf_path` is null

**Solution:**
- Check disk space in the container (mount point for `pdfs/` directory)
- Verify write permissions on `/app/pdfs/` directory
- Check error logs for exceptions during PDF generation

---

## Deployment Notes

### As a Microservice

This service is designed to be:

- **Stateless** (job state is transient; backed by DBMS API for persistence)
- **Scalable** (RabbitMQ consumer can be replicated; jobs are assigned by queue)
- **Resilient** (failed jobs are retried; events are durable in RabbitMQ)
- **Isolated** (no direct database access; communicates only via DBMS API)


## File Structure

```
report_worker/
├── app.py                 # Flask API endpoints
├── worker.py              # RabbitMQ consumer & business logic
├── storage.py             # Thread-safe job store
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container build configuration
├── .coveragerc            # Code coverage settings
├── tests/
│   ├── conftest.py        # Pytest fixtures & setup
│   └── test_worker.py     # Comprehensive test suite
├── static/
│   └── schema/
│       └── swagger.yaml   # OpenAPI specification
└── pdfs/                  # Generated PDF reports (runtime directory)
```

---

## Further Documentation

- **OpenAPI Spec:** `static/schema/swagger.yaml` (also available at `/docs/`)
- **Main DBMS API:** See `../dbms/README.md`
- **Docker Compose:** See `../docker-compose.yml` for full stack configuration

