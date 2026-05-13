"""Shared fixtures and setup for aux service tests."""

import os
import sys

# Ensure the report_worker package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Prevent worker from trying to connect to real RabbitMQ
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")
os.environ.setdefault("DBMS_API_BASE_URL", "http://localhost:8000/api")
os.environ.setdefault("DBMS_API_KEY", "test-key")
