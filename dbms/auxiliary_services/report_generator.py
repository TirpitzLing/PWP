"""Background worker for nutrition report generation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import time
import pika
from flask import current_app

from dbms import create_app
from dbms.extensions import db
from dbms.models import ReportJob, Recipe

STANDARD_INTAKE = {
    "calories": 350.0,
    "carbs": 30.0,
    "protein": 20.0,
    "fat": 12.0,
}

EVENT_BUS_EXCHANGE = "report_events"
EVENT_BUS_ROUTING_KEY = "report.job.pending"
REPORT_QUEUE = "report_jobs"

# ---------------------------
# PDF generation (unchanged)
# ---------------------------


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf_bytes(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 12 Tf", "14 TL", "50 800 Td"]

    for i, line in enumerate(lines):
        safe = _escape_pdf_text(line)
        if i == 0:
            content_lines.append(f"({safe}) Tj")
        else:
            content_lines.append("T*")
            content_lines.append(f"({safe}) Tj")

    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)+1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")

    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())

    pdf.extend(
        b"trailer\n"
        + f"<< /Size {len(objects)+1} /Root 1 0 R >>\n".encode()
        + b"startxref\n"
        + f"{xref}\n".encode()
        + b"%%EOF\n"
    )

    return bytes(pdf)


# ---------------------------
# Business logic
# ---------------------------


def _fetch_recipe_nutrition(client, recipe_id: int) -> dict[str, float]:
    resp = client.get(f"/api/recipes/{recipe_id}/nutrition/")

    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch nutrition for recipe {recipe_id}: "
            f"HTTP {resp.status_code}"
        )

    payload = resp.get_json(silent=True) or {}
    return {
        "calories": round(float(payload.get("total_calories") or 0.0), 2),
        "carbs": round(float(payload.get("total_carbs") or 0.0), 2),
        "protein": round(float(payload.get("total_protein") or 0.0), 2),
        "fat": round(float(payload.get("total_fat") or 0.0), 2),
    }


def calculate_totals(recipe_ids: list[int], client) -> dict[str, float]:
    totals = {"calories": 0.0, "carbs": 0.0, "protein": 0.0, "fat": 0.0}

    for recipe_id in recipe_ids:
        rt = _fetch_recipe_nutrition(client, recipe_id)
        for k in totals:
            totals[k] += rt[k]

    return {k: round(v, 2) for k, v in totals.items()}


def compare_to_standard(
    totals: dict[str, float], recipe_count: int
) -> dict[str, dict[str, float]]:
    result = {}

    multiplier = max(recipe_count, 1)

    for k, std in STANDARD_INTAKE.items():
        val = totals.get(k, 0.0)
        scaled_std = round(std * multiplier, 2)
        result[k] = {
            "total": val,
            "standard": scaled_std,
            "difference": round(val - scaled_std, 2),
            "percent": round((val / scaled_std) * 100, 2) if scaled_std else 0,
        }

    return result


def build_recommendation(comparison: dict[str, dict[str, float]]) -> str:
    calories = comparison["calories"]
    diff = calories["difference"]
    pct = calories["percent"]

    if 90 <= pct <= 110:
        return "Good condition: intake is close to the target range."
    if diff > 0:
        return "Intake is high: consider adding exercise to deplete excess calories."
    return "Intake is low: consider taking a bit more nutrition."


# ---------------------------
# Core job processing
# ---------------------------


def process_job(job: ReportJob, instance_path: str):
    print(f"Processing report job {job.id} for user {job.user_id}")
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.session.commit()

    try:
        recipe_ids = json.loads(job.recipe_ids or "[]")
        recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all()

        recipe_map = {r.id: r for r in recipes}
        ordered = [recipe_map[rid] for rid in recipe_ids if rid in recipe_map]

        output_path = Path(instance_path) / "reports" / f"report-{job.id}.pdf"

        with current_app.test_client() as client:
            totals = calculate_totals([r.id for r in ordered], client)
        comparison = compare_to_standard(totals, len(ordered))
        recommendation = build_recommendation(comparison)

        lines = [
            "Nutrition Report",
            f"User: {job.user.username if job.user else job.user_id}",
            "",
        ]

        for r in ordered:
            lines.append(f"- {r.title}")

        lines += [
            "",
            f"Calories: {totals['calories']}",
            f"Carbs: {totals['carbs']}",
            f"Protein: {totals['protein']}",
            f"Fat: {totals['fat']}",
            "",
            f"Comparison Summary:",
            (
                "Calories -> total "
                f"{comparison['calories']['total']}, standard "
                f"{comparison['calories']['standard']}, diff: "
                f"{comparison['calories']['difference']}"
            ),
            (
                "Carbs -> total "
                f"{comparison['carbs']['total']}, standard "
                f"{comparison['carbs']['standard']}, diff: "
                f"{comparison['carbs']['difference']}"
            ),
            (
                "Protein -> total "
                f"{comparison['protein']['total']}, standard "
                f"{comparison['protein']['standard']}, diff "
                f"{comparison['protein']['difference']}"
            ),
            (
                "Fat -> total "
                f"{comparison['fat']['total']}, standard "
                f"{comparison['fat']['standard']}, diff: "
                f"{comparison['fat']['difference']}"
            ),
            "",
            f"Suggestion: {recommendation}",
        ]

        pdf = _build_pdf_bytes(lines)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf)

        job.total_calories = totals["calories"]
        job.total_carbs = totals["carbs"]
        job.total_protein = totals["protein"]
        job.total_fat = totals["fat"]
        job.comparison_json = json.dumps(comparison)
        job.output_file_path = str(output_path)
        job.status = "done"
        job.finished_at = datetime.now(timezone.utc)
        job.error_message = None

        db.session.commit()

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        raise


def process_pending_jobs_once(instance_path: str) -> int:
    """Process currently pending jobs once before starting event consumption."""
    pending_jobs = (
        ReportJob.query.filter_by(status="pending")
        .order_by(ReportJob.created_at.asc())
        .all()
    )

    processed = 0
    for job in pending_jobs:
        process_job(job, instance_path)
        processed += 1

    return processed


# ---------------------------
# RabbitMQ consumer (event-driven)
# ---------------------------


def handle_message(ch, method, properties, body, app):
    job = None
    print("[worker] received message:", body.decode())
    try:
        event = json.loads(body.decode())

        if event.get("type") != EVENT_BUS_ROUTING_KEY:
            ch.basic_ack(method.delivery_tag)
            return

        job_id = event["job_id"]
        # Use Session.get() to avoid SQLAlchemy legacy Query.get() warning
        job = db.session.get(ReportJob, job_id)

        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status != "pending":
            # Duplicate/stale events are acknowledged and ignored.
            ch.basic_ack(method.delivery_tag)
            return

        process_job(job, app.instance_path)
        print(f"Processing report job {job_id}")
        ch.basic_ack(method.delivery_tag)

    except Exception as e:
        print(f"[worker] failed to process job {job_id}: {e}")
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.session.commit()

        ch.basic_nack(method.delivery_tag, requeue=False)


def connect_with_retry(url, retries=10, delay=3):

    for i in range(retries):

        try:

            return pika.BlockingConnection(pika.URLParameters(url))

        except Exception as e:

            print(f"[RabbitMQ] connect failed ({i+1}/{retries}): {e}")

            time.sleep(delay)

    raise RuntimeError("Cannot connect to RabbitMQ")


def run_worker():
    app = create_app()
    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")

    with app.app_context():
        # Log instance path and DB file presence for debugging shared-volume issues
        db_path = os.path.join(app.instance_path, "dbms.db")
        print(f"[worker] app.instance_path: {app.instance_path}")
        print(f"[worker] db file: {db_path} exists={os.path.exists(db_path)}")

        process_pending_jobs_once(app.instance_path)

        conn = connect_with_retry(url)
        ch = conn.channel()

        ch.exchange_declare(
            exchange=EVENT_BUS_EXCHANGE,
            exchange_type="topic",
            durable=True,
        )
        ch.queue_declare(queue=REPORT_QUEUE, durable=True)
        ch.queue_bind(
            exchange=EVENT_BUS_EXCHANGE,
            queue=REPORT_QUEUE,
            routing_key=EVENT_BUS_ROUTING_KEY,
        )
        ch.basic_qos(prefetch_count=1)

        ch.basic_consume(
            queue=REPORT_QUEUE,
            on_message_callback=lambda c, m, p, b: handle_message(
                c, m, p, b, app
            ),
        )

        print("report worker started")
        ch.start_consuming()


if __name__ == "__main__":
    run_worker()
