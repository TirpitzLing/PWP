"""Aux report service — Flask API.

Clients call this service directly (not the DBMS API) for report
creation, status polling, and PDF download.
"""

import json
import os
import threading

import pika
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

from storage import create_job, get_job
from worker import connect_and_consume

PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F"
)
EVENT_EXCHANGE = "report_events"
EVENT_ROUTING_KEY = "report.job.pending"


def _publish_job(job_id: int, recipe_ids: list[int]):
    """Push a job event to RabbitMQ."""
    payload = {
        "type": EVENT_ROUTING_KEY,
        "job_id": job_id,
        "recipe_ids": recipe_ids,
    }
    params = pika.URLParameters(RABBITMQ_URL)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.exchange_declare(
        exchange=EVENT_EXCHANGE, exchange_type="topic", durable=True
    )
    ch.basic_publish(
        exchange=EVENT_EXCHANGE,
        routing_key=EVENT_ROUTING_KEY,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    conn.close()


def create_app():
    app = Flask(__name__)
    CORS(app)

    os.makedirs(PDF_DIR, exist_ok=True)

    # ---------------------------------------------------------------
    # POST /reports/  — create a new report job
    # ---------------------------------------------------------------
    @app.route("/reports/", methods=["POST"])
    def create_report():
        body = request.get_json(silent=True)
        if not body or "recipe_ids" not in body:
            return jsonify({"error": "Missing recipe_ids"}), 400

        recipe_ids = body["recipe_ids"]
        if not isinstance(recipe_ids, list) or not all(
            isinstance(r, int) for r in recipe_ids
        ):
            return jsonify({"error": "recipe_ids must be a list of ints"}), 400

        wait = request.args.get("wait", "").lower() == "true"

        job = create_job(recipe_ids)
        _publish_job(job["id"], recipe_ids)

        if not wait:
            return (
                jsonify(job),
                202,
                {"Location": f"/reports/{job['id']}/"},
            )

        # Block until the worker finishes
        import time as _time
        job_id = job["id"]
        for _ in range(60):  # 30s timeout
            _time.sleep(0.5)
            current = get_job(job_id)
            if current["status"] == "done":
                return jsonify(current)
            if current["status"] == "failed":
                return (
                    jsonify(current),
                    500,
                )
        return jsonify({"error": "Timeout"}), 504

    # ---------------------------------------------------------------
    # GET /reports/<id>/  — get job status & results
    # ---------------------------------------------------------------
    @app.route("/reports/<int:job_id>/", methods=["GET"])
    def report_status(job_id):
        job = get_job(job_id)
        if job is None:
            return jsonify({"error": "Not found"}), 404
        return jsonify(job)

    # ---------------------------------------------------------------
    # GET /reports/<id>/download/  — download the generated PDF
    # ---------------------------------------------------------------
    @app.route("/reports/<int:job_id>/download/", methods=["GET"])
    def report_download(job_id):
        job = get_job(job_id)
        if job is None:
            return jsonify({"error": "Not found"}), 404
        if job["status"] != "done":
            return jsonify({"error": "Report not ready yet"}), 409
        path = job.get("pdf_path")
        if not path or not os.path.isfile(path):
            return jsonify({"error": "PDF file not found"}), 404
        return send_file(
            path,
            as_attachment=True,
            download_name=os.path.basename(path),
            mimetype="application/pdf",
        )

    # ---------------------------------------------------------------
    # Swagger UI at /docs/
    # ---------------------------------------------------------------
    swagger_url = "/docs"
    api_url = "/static/schema/swagger.yaml"
    swagger_blueprint = get_swaggerui_blueprint(
        swagger_url,
        api_url,
        config={"app_name": "DBMS Report Service"},
    )
    app.register_blueprint(swagger_blueprint, url_prefix=swagger_url)

    # ---------------------------------------------------------------
    # Start the RabbitMQ consumer in a background thread
    # ---------------------------------------------------------------
    if not app.config.get("TESTING"):
        def _start_worker():
            print("[aux] starting RabbitMQ consumer thread")
            connect_and_consume()

        worker_thread = threading.Thread(
            target=_start_worker, daemon=True
        )
        worker_thread.start()

    return app
