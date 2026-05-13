"""RabbitMQ consumer — fetches nutrition from DBMS API, generates PDF."""

import base64
import json
import os
import time

import pika
import requests

import storage

# ---------------------------------------------------------------------------
API_BASE = os.getenv("DBMS_API_BASE_URL", "http://dbms-api:8000/api").rstrip(
    "/"
)

API_KEY = os.getenv("DBMS_API_KEY", "")

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F"
)

EVENT_EXCHANGE = "report_events"
EVENT_ROUTING_KEY = "report.job.pending"
QUEUE_NAME = "report_jobs"

STANDARD_INTAKE = {
    "calories": 350.0,
    "carbs": 40.0,
    "protein": 22.0,
    "fat": 12.0,
}

PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _headers():
    return {
        "Content-Type": "application/json",
        "dbms-api-key": API_KEY,
    }


def _fetch_nutrition(recipe_id: int) -> dict:
    url = f"{API_BASE}/recipes/{recipe_id}/nutrition/"
    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return {
        "calories": round(float(data.get("total_calories", 0)), 2),
        "carbs": round(float(data.get("total_carbs", 0)), 2),
        "protein": round(float(data.get("total_protein", 0)), 2),
        "fat": round(float(data.get("total_fat", 0)), 2),
    }


def _fetch_recipe_title(recipe_id: int) -> str:
    url = f"{API_BASE}/recipes/{recipe_id}/"
    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json().get("title", f"Recipe {recipe_id}")


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------


def calculate_totals(recipe_ids: list[int]) -> dict:
    """Sum nutrition data across *recipe_ids* by calling the DBMS API.

    :param recipe_ids: list of recipe IDs to fetch nutrition for
    :returns: dict with keys ``calories``, ``carbs``, ``protein``, ``fat``
    :raises requests.HTTPError: if the DBMS API returns a non-2xx status
    """
    totals = {"calories": 0.0, "carbs": 0.0, "protein": 0.0, "fat": 0.0}
    for rid in recipe_ids:
        nt = _fetch_nutrition(rid)
        for k in totals:
            totals[k] = round(totals[k] + nt[k], 2)
    return totals


def compare_to_standard(totals: dict) -> dict:
    """Compare nutrition *totals* against ``STANDARD_INTAKE``.

    :param totals: dict with ``calories``, ``carbs``, ``protein``, ``fat``
    :returns: dict keyed by nutrient, each containing ``total``,
        ``standard``, ``difference``, and ``percent``
    """
    result = {}
    for nutrient, std in STANDARD_INTAKE.items():
        actual = totals.get(nutrient, 0.0)
        result[nutrient] = {
            "total": actual,
            "standard": std,
            "difference": round(actual - std, 2),
            "percent": round((actual / std) * 100, 2) if std else 0,
        }
    return result


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_bytes(
    job_id: int, titles: list[str], totals: dict, comparison: dict
) -> bytes:
    """Generate a minimal PDF report without external libraries.

    :param job_id: report job identifier
    :param titles: recipe title strings to list in the report
    :param totals: dict with ``calories``, ``carbs``, ``protein``, ``fat``
    :param comparison: result of :func:`compare_to_standard`
    :returns: raw PDF bytes (PDF 1.4)
    """
    lines = [
        "Nutrition Report",
        f"Job: {job_id}",
        "",
        "Recipes:",
    ]
    for t in titles:
        lines.append(f"  - {t}")
    lines += [
        "",
        "--- Totals ---",
        f"Calories : {totals['calories']}",
        f"Carbs    : {totals['carbs']} g",
        f"Protein  : {totals['protein']} g",
        f"Fat      : {totals['fat']} g",
        "",
        "--- vs Standard Daily Intake ---",
    ]
    for nutrient, data in comparison.items():
        diff = data["difference"]
        sign = "+" if diff > 0 else ""
        lines.append(
            f"{nutrient.capitalize():12s}  "
            f"{data['total']} / {data['standard']}  "
            f"({sign}{diff})  {data['percent']}%"
        )

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
# Job processing
# ---------------------------------------------------------------------------


def process_job(job_id: int, recipe_ids: list[int]):
    """Fetch nutrition from DBMS API, generate PDF, update *job_id* in storage.

    :param job_id: report job ID in the local store
    :param recipe_ids: recipe IDs to include in the report
    :raises Exception: any failure is caught internally; the job is
        marked ``failed`` in storage rather than propagating the error
    """

    storage.update_job(job_id, status="running")

    try:
        titles = [_fetch_recipe_title(rid) for rid in recipe_ids]
        totals = calculate_totals(recipe_ids)
        comparison = compare_to_standard(totals)
        pdf = build_pdf_bytes(job_id, titles, totals, comparison)

        os.makedirs(PDF_DIR, exist_ok=True)
        pdf_path = os.path.join(PDF_DIR, f"report-{job_id}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf)

        storage.update_job(
            job_id,
            status="done",
            total_calories=totals["calories"],
            total_carbs=totals["carbs"],
            total_protein=totals["protein"],
            total_fat=totals["fat"],
            comparison_json=json.dumps(comparison),
            pdf_path=pdf_path,
        )
        print(f"[worker] job {job_id} done")

    except Exception as exc:
        print(f"[worker] job {job_id} failed: {exc}")
        storage.update_job(job_id, status="failed", error_message=str(exc))


# ---------------------------------------------------------------------------
# RabbitMQ consumer
# ---------------------------------------------------------------------------


def handle_message(ch, method, properties, body):
    """RabbitMQ delivery callback — decode *body* and call :func:`process_job`.

    :param ch: Pika channel
    :param method: Pika deliver method frame
    :param properties: message properties
    :param body: raw message body (JSON bytes)
    """
    event = json.loads(body.decode())
    print(f"[worker] received: {event}")

    if event.get("type") != EVENT_ROUTING_KEY:
        ch.basic_ack(method.delivery_tag)
        return

    job_id = event["job_id"]
    recipe_ids = event.get("recipe_ids", [])

    process_job(job_id, recipe_ids)
    ch.basic_ack(method.delivery_tag)


def connect_with_retry(retries=10, delay=3):
    """Connect to RabbitMQ, retrying on failure.

    :param retries: maximum number of attempts
    :param delay: seconds to wait between attempts
    :returns: ``pika.BlockingConnection``
    :raises RuntimeError: if all attempts fail
    """
    for attempt in range(1, retries + 1):
        try:
            return pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        except Exception as exc:
            print(f"[RabbitMQ] connect failed ({attempt}/{retries}): {exc}")
            time.sleep(delay)
    raise RuntimeError("Cannot connect to RabbitMQ")


def connect_and_consume():
    """Blocking call — meant to run in a background thread."""
    print(f"[worker] API: {API_BASE}  RabbitMQ: {RABBITMQ_URL}")

    conn = connect_with_retry()
    ch = conn.channel()

    ch.exchange_declare(
        exchange=EVENT_EXCHANGE, exchange_type="topic", durable=True
    )
    ch.queue_declare(queue=QUEUE_NAME, durable=True)
    ch.queue_bind(
        exchange=EVENT_EXCHANGE,
        queue=QUEUE_NAME,
        routing_key=EVENT_ROUTING_KEY,
    )
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_message)

    print("[worker] started — waiting for report jobs")
    ch.start_consuming()
