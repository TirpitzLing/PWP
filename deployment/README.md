# Monitor and Control System for Deployment
### A. Docker Engine (Container Level)
- Managed via the `restart: always` policy in `docker-compose.yml`. Docker acts as the primary process supervisor; if a container exits due to a critical failure, the Docker daemon automatically restarts it, ensuring zero manual intervention.
- **Active Health Monitoring**: Implemented Docker `healthcheck` to actively ping the internal API endpoint (`http://localhost:8000/api/recipes/`).

### B. Gunicorn Process Manager (Application Level)
- Master-Worker Architecture (`-w 4`).
- **Function**: Gunicorn acts as an internal monitor. The Master process continuously tracks the health of the 4 worker processes. If a worker dies, the Master immediately spawns a new one to maintain service continuity.

### C. Nginx Upstream Monitoring
- Reverse Proxy pass-through.
- **Function**: Nginx monitors the responsiveness of the backend API. It provides a buffer and manages connection timeouts, preventing a single slow request from locking the entire system.

### D. Logging & Visibility
- Docker command: `docker compose logs -f`
- **Function**: All service outputs (stdout/stderr) are aggregated by the Docker logging driver.