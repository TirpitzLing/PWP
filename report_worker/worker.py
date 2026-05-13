"""RabbitMQ consumer — fetches nutrition from DBMS API, generates PDF."""

import base64
import json
import logging
import os
import textwrap
import time

import pika
import requests

import storage

# Set up logging so output appears in Docker/gunicorn logs
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

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


def compare_to_standard(totals: dict, cooked_dish_count: int = 1) -> dict:
    """Compare nutrition *totals* against scaled ``STANDARD_INTAKE``.

    :param totals: dict with ``calories``, ``carbs``, ``protein``, ``fat``
    :param cooked_dish_count: number of cooked dishes represented by totals
    :returns: dict keyed by nutrient, each containing ``total``,
        ``standard``, ``difference``, and ``percent``
    """
    scaled_count = max(int(cooked_dish_count), 0)
    result = {}
    for nutrient, std in STANDARD_INTAKE.items():
        std_total = round(std * scaled_count, 2)
        actual = totals.get(nutrient, 0.0)
        result[nutrient] = {
            "total": actual,
            "standard": std_total,
            "difference": round(actual - std_total, 2),
            "percent": (
                round((actual / std_total) * 100, 2) if std_total else 0
            ),
        }
    return result


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generate_ai_suggestion(comparison: dict) -> str:
    """Generate a concise summary based on comparison to standard intake.

    If the environment variable `GOOGLE_AI_API_KEY` is set, attempt to
    call Google Generative API (text-bison). On any failure or when the
    key is absent, fall back to the local rule-based summary.
    """
    # Try LLM first (non-blocking fallback)
    try:
        logger.info("Attempting Google Generative AI summary...")
        llm = _call_google_generative_for_summary(comparison)
        if llm:
            logger.info("Successfully received LLM summary")
            return llm
        else:
            logger.info("LLM returned None, falling back to local")
    except Exception:
        # Log error then fall back to local logic
        import traceback

        logger.error("LLM call failed:\n%s", traceback.format_exc())

    low = []
    high = []
    balanced = []

    for nutrient, data in comparison.items():
        pct = float(data.get("percent", 0))
        if pct < 90:
            low.append((nutrient, pct))
        elif pct > 110:
            high.append((nutrient, pct))
        else:
            balanced.append((nutrient, pct))

    parts = []
    if high:
        top_high = max(high, key=lambda x: x[1])
        parts.append(
            f"Highest excess is {top_high[0]} at {top_high[1]}% of standard intake; consider reducing that nutrient first."
        )
    if low:
        top_low = min(low, key=lambda x: x[1])
        parts.append(
            f"Most lacking is {top_low[0]} at {top_low[1]}% of standard intake; increase foods rich in it."
        )
    if balanced:
        names = ", ".join(n.capitalize() for n, _ in balanced[:2])
        parts.append(f"Within reasonable range: {names}.")

    if not parts:
        return "All nutrients are close to standard intake. Keep your current pattern."
    return " ".join(parts)


def _call_google_generative_for_summary(comparison: dict) -> str | None:
    """Call Google Generative API to produce a human-friendly summary.

    Requires `GOOGLE_AI_API_KEY` in the environment. Returns `None` on
    any error so callers can fall back to the local generator.
    """
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        logger.info("GOOGLE_AI_API_KEY not set, skipping LLM call")
        return None

    logger.debug("GOOGLE_AI_API_KEY is set, proceeding with LLM call")

    # Build a compact prompt describing the comparison table
    parts = [
        "Please produce a short actionable summary for a user based on these nutritional comparisons:"
    ]
    for nutrient, data in comparison.items():
        parts.append(
            f"{nutrient}: total={data.get('total')} standard={data.get('standard')} diff={data.get('difference')} pct={data.get('percent')}%"
        )
    prompt = "\n".join(parts)

    url = "https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generateText"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {"prompt": {"text": prompt}, "temperature": 0.2}

    try:
        logger.info("Sending request to Google Generative API (text-bison-001)")
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        logger.debug("Response status: %s", resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        logger.debug("Response JSON: %s", data)
        # Prefer common fields; be tolerant of different response shapes
        if isinstance(data, dict):
            candidates = data.get("candidates") or []
            if candidates and isinstance(candidates, list):
                out = candidates[0].get("output") or candidates[0].get("content")
                if out:
                    logger.info("Successfully extracted LLM output from response")
                    return out.strip()
            # Older/simpler shapes
            out = data.get("output") or data.get("text")
            if out:
                logger.info("Successfully extracted LLM output from flat response")
                return out.strip()
        logger.warning("No output field found in response")
        return None
    except Exception as exc:
        logger.error("LLM request failed: %s", str(exc))
        return None


def build_pdf_bytes(job_id: int, titles: list[str], totals: dict, comparison: dict) -> bytes:
    """Generate a minimal PDF report (bytes) from provided data.

    Kept lightweight to avoid external PDF deps in test environments.
    """
    # Count dishes in order of first appearance.
    dish_counts = {}
    dish_order = []
    for title in titles:
        if title not in dish_counts:
            dish_counts[title] = 0
            dish_order.append(title)
        dish_counts[title] += 1

    lines = [
        "Nutrition Report",
        "",
        "Weekly Cooked Recipes",
    ]

    recipe_header = f"{'No':<3} {'Dish':<30} {'Times':>5}"
    lines.append(recipe_header)
    lines.append("-" * len(recipe_header))

    if not dish_order:
        lines.append(f"{1:<3d} {'No recipes recorded':<30s} {0:>5d}")
    else:
        for idx, title in enumerate(dish_order, start=1):
            lines.append(
                f"{idx:<3d} {title[:30]:<30s} {dish_counts[title]:>5d}"
            )

    lines += [
        "",
        "Total Nutrition",
    ]

    total_header = f"{'Nutrient':<12} {'Total':>10}"
    lines.append(total_header)
    lines.append("-" * len(total_header))
    lines += [
        f"{'Calories':<12} {totals['calories']:>10.2f}",
        f"{'Carbs (g)':<12} {totals['carbs']:>10.2f}",
        f"{'Protein (g)':<12} {totals['protein']:>10.2f}",
        f"{'Fat (g)':<12} {totals['fat']:>10.2f}",
        "",
        "vs Standard Intake",
    ]

    cmp_header = f"{'Nutrient':<12} {'Total':>10} {'Standard':>10} {'Diff':>10} {'Ratio':>8}"
    lines.append(cmp_header)
    lines.append("-" * len(cmp_header))

    for nutrient, data in comparison.items():
        diff = float(data["difference"])
        diff_text = f"{diff:+.2f}" if diff != 0 else "0.00"
        lines.append(
            f"{nutrient.capitalize():12s} "
            f"{float(data['total']):>10.2f} "
            f"{float(data['standard']):>10.2f} "
            f"{diff_text:>10s} "
            f"{float(data['percent']):>7.2f}%"
        )

    suggestion = generate_ai_suggestion(comparison)
    wrapped_suggestion = textwrap.wrap(suggestion, width=78) or [""]
    lines += [
        "",
        "Summary",
    ]
    lines.extend(wrapped_suggestion)

    # Keep text inside page bounds by creating multiple pages when needed.
    max_lines_per_page = 48
    pages = [
        lines[i : i + max_lines_per_page]
        for i in range(0, len(lines), max_lines_per_page)
    ]

    page_streams = []
    for page_lines in pages:
        content_lines = ["BT", "/F1 11 Tf", "13 TL", "50 800 Td"]
        for i, line in enumerate(page_lines):
            safe = _escape_pdf_text(line)
            if i == 0:
                content_lines.append(f"({safe}) Tj")
            else:
                content_lines.append("T*")
                content_lines.append(f"({safe}) Tj")
        content_lines.append("ET")
        page_streams.append("\n".join(content_lines).encode("latin-1"))

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    kids = []
    first_page_obj = 4
    for i, content in enumerate(page_streams):
        page_obj_num = first_page_obj + (i * 2)
        content_obj_num = page_obj_num + 1
        kids.append(f"{page_obj_num} 0 R")

        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_num} 0 R >>"
            ).encode("latin-1")
        )
        objects.append(
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        )

    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    ).encode("latin-1")

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
        comparison = compare_to_standard(totals, len(recipe_ids))
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
        logger.info("Job %d completed successfully", job_id)

    except Exception as exc:
        logger.error("Job %d failed: %s", job_id, str(exc))
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
    logger.info("Received event: %s", event)

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
            logger.warning("RabbitMQ connect failed (%d/%d): %s", attempt, retries, str(exc))
            time.sleep(delay)
    raise RuntimeError("Cannot connect to RabbitMQ")


def connect_and_consume():
    """Blocking call — meant to run in a background thread."""
    logger.info("Starting RabbitMQ consumer (API: %s, RabbitMQ: %s)", API_BASE, RABBITMQ_URL)

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

    logger.info("Consumer started — waiting for report jobs on %s", EVENT_ROUTING_KEY)
    ch.start_consuming()
