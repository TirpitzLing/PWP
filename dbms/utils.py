"""
Utility functions for the DBMS API.
"""

import json
import os

import pika
from flask import request
from werkzeug.exceptions import BadRequest


def get_pagination_args(default_limit=10, default_offset=0):
    """
    Safely extract and validate 'limit' and 'offset' from query parameters.
    Raises a 400 BadRequest if the parameters are non-integers or negative.
    """
    raw_limit = request.args.get("limit")
    raw_offset = request.args.get("offset")

    try:
        limit = int(raw_limit) if raw_limit is not None else default_limit
        offset = int(raw_offset) if raw_offset is not None else default_offset
    except ValueError as exc:
        # "?limit=abc": 400
        raise BadRequest(
            description="Query parameters 'limit' and 'offset' must be valid integers."
        ) from exc

    if limit < 0 or offset < 0:
        # for negative params, avoiding 500
        raise BadRequest(
            description="Query parameters 'limit' and 'offset' cannot be negative."
        )

    return limit, offset


def publish_report_job(job_id, queue_name="report_jobs"):
    """Publish a report job id to a RabbitMQ queue."""
    rabbitmq_url = os.getenv(
        "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F"
    )

    try:
        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps({"job_id": job_id}),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to publish report job to queue '{queue_name}': {exc}"
        ) from exc
