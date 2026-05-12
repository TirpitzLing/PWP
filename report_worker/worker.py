"""Standalone nutrition report worker.

Communicates with the DBMS API exclusively via HTTP; has zero knowledge of the
API's database or ORM.  Receives job events from RabbitMQ and posts results
back to the API.
"""

import base64
import json
import os
import time
from datetime import datetime, timezone

import pika
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv(
    "API_BASE_URL", "http://dbms-api:8000/api"
).rstrip("/")

WORKER_API_KEY = os.getenv(
    "WORKER_API_KEY", ""
)

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F"
)

EVENT_BUS_EXCHANGE = "report_events"
EVENT_BUS_ROUTING_KEY = "report.job.pending"
REPORT_QUEUE = "report_jobs"

STANDARD_INTAKE = {
    "calories": 700.0,
    "carbs": 80.0,
    "protein": 45.0,
    "fat": 25.0,
}

# ---------------------------------------------------------------------------
# HTTP helpers (the ONLY way this worker touches the API)
# ---------------------------------------------------------------------------


def _api_headers():
    return {
        "Content-Type": "application/json",
        "dbms-api-key": WORKER_API_KEY,
    }


def _fetch_nutrition(recipe_id: int) -> dict[str, float]:
    """Call GET /api/recipes/{id}/nutrition/."""
    url = f"{API_BASE_URL}/recipes/{recipe_id}/nutrition/"
    resp = requests.get(url, headers=_api_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return {
        "calories": round(float(data.get("total_calories", 0)), 2),
        "carbs": round(float(data.get("total_carbs", 0)), 2),
        "protein": round(float(data.get("total_protein", 0)), 2),
        "fat": round(float(data.get("total_fat", 0)), 2),
    }


def _submit_result(
    user_id: int,
    job_id: int,
    *,
    status: str = "done",
    totals: dict | None = None,
    comparison: dict | None = None,
    pdf_base64: str | None = None,
    filename: str = "",
    error_message: str | None = None,
):
    """Call PUT /api/users/{user}/reports/{job}/ to post job results."""
    url = f"{API_BASE_URL}/users/{user_id}/reports/{job_id}/"
    body: dict = {"status": status}

    if status == "failed":
        body["error_message"] = error_message or "Unknown error"
    else:
        body.update(
            {
                "total_calories": totals.get("calories", 0.0),
                "total_carbs": totals.get("carbs", 0.0),
                "total_protein": totals.get("protein", 0.0),
                "total_fat": totals.get("fat", 0.0),
                "comparison_json": json.dumps(comparison),
                "pdf_base64": pdf_base64 or "",
                "filename": filename or f"report-{job_id}.pdf",
            }
        )

    resp = requests.put(url, json=body, headers=_api_headers(), timeout=30)
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Business logic (pure functions — testable without network)
# ---------------------------------------------------------------------------


def calculate_totals(
    recipe_ids: list[int],
) -> dict[str, float]:
    """Fetch nutrition for each recipe via API and sum the totals."""
    totals: dict[str, float] = {
        "calories": 0.0,
        "carbs": 0.0,
        "protein": 0.0,
        "fat": 0.0,
    }
    for rid in recipe_ids:
        nt = _fetch_nutrition(rid)
        for k in totals:
            totals[k] = round(totals[k] + nt[k], 2)
    return totals


def compare_to_standard(
    totals: dict[str, float],
) -> dict:
    """Compare nutrition totals against standard daily intake values."""
    result = {}
    for nutrient, standard in STANDARD_INTAKE.items():
        actual = totals.get(nutrient, 0.0)
        result[nutrient] = {
            "total": actual,
            "standard": standard,
            "difference": round(actual - standard, 2),
            "percent": (
                round((actual / standard) * 100, 2) if standard else 0
            ),
        }
    return result


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_bytes(
    job_id: int, user_id: int, recipe_titles: list[str], totals: dict
) -> bytes:
    """Generate a minimal PDF report without external libraries."""
    lines = [
        "Nutrition Report",
        f"Job: {job_id}",
        f"User: {user_id}",
        "",
    ]
    for title in recipe_titles:
        lines.append(f"- {title}")
    lines += [
        "",
        f"Calories: {totals['calories']}",
        f"Carbs: {totals['carbs']}",
        f"Protein: {totals['protein']}",
        f"Fat: {totals['fat']}",
    ]

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
    offsets: list[int] = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
        + b"startxref\n"
        + f"{xref}\n".encode()
        + b"%%EOF\n"
    )
    return bytes(pdf)


# ---------------------------------------------------------------------------
# Job processing (single job)
# ---------------------------------------------------------------------------


def process_job(job_id: int, user_id: int, recipe_ids: list[int]):
    """Fetch nutrition, generate PDF, and submit results back to the API."""
    print(
        f"[worker] processing job {job_id} "
        f"user={user_id} recipes={recipe_ids}"
    )

    # Fetch titles from the API
    recipe_titles: list[str] = []
    for rid in recipe_ids:
        try:
            url = f"{API_BASE_URL}/recipes/{rid}/"
            resp = requests.get(
                url, headers=_api_headers(), timeout=15
            )
            resp.raise_for_status()
            recipe_titles.append(
                resp.json().get("title", f"Recipe {rid}")
            )
        except Exception as exc:
            print(f"[worker] warning: could not fetch recipe {rid}: {exc}")
            recipe_titles.append(f"Recipe {rid}")

    totals = calculate_totals(recipe_ids)
    comparison = compare_to_standard(totals)
    pdf = build_pdf_bytes(job_id, user_id, recipe_titles, totals)
    pdf_b64 = base64.b64encode(pdf).decode("ascii")

    _submit_result(
        user_id,
        job_id,
        status="done",
        totals=totals,
        comparison=comparison,
        pdf_base64=pdf_b64,
        filename=f"report-{job_id}.pdf",
    )
    print(f"[worker] job {job_id} completed")


# ---------------------------------------------------------------------------
# RabbitMQ consumer
# ---------------------------------------------------------------------------


def handle_message(ch, method, properties, body):
    """Process one incoming RabbitMQ message."""
    event = json.loads(body.decode())
    print(f"[worker] received: {event}")

    if event.get("type") != EVENT_BUS_ROUTING_KEY:
        ch.basic_ack(method.delivery_tag)
        return

    job_id = event["job_id"]
    user_id = event["user_id"]
    recipe_ids = event.get("recipe_ids", [])

    try:
        process_job(job_id, user_id, recipe_ids)
        ch.basic_ack(method.delivery_tag)
    except Exception as exc:
        print(f"[worker] job {job_id} failed: {exc}")
        try:
            _submit_result(
                user_id,
                job_id,
                status="failed",
                error_message=str(exc),
            )
        except Exception as submit_exc:
            print(
                f"[worker] could not submit failure for job {job_id}: "
                f"{submit_exc}"
            )
        ch.basic_nack(method.delivery_tag, requeue=False)


def connect_with_retry(
    url: str, retries: int = 10, delay: int = 3
) -> pika.BlockingConnection:
    """Retry connecting to RabbitMQ until it becomes available."""
    for attempt in range(1, retries + 1):
        try:
            return pika.BlockingConnection(pika.URLParameters(url))
        except Exception as exc:
            print(
                f"[RabbitMQ] connect failed "
                f"({attempt}/{retries}): {exc}"
            )
            time.sleep(delay)
    raise RuntimeError("Cannot connect to RabbitMQ")


def run_worker():
    """Entry point: connect to RabbitMQ and start consuming."""
    print(
        f"[worker] API base: {API_BASE_URL}  "
        f"RabbitMQ: {RABBITMQ_URL}"
    )

    conn = connect_with_retry(RABBITMQ_URL)
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
        queue=REPORT_QUEUE, on_message_callback=handle_message
    )

    print("[worker] started — waiting for report jobs")
    ch.start_consuming()


if __name__ == "__main__":
    run_worker()
