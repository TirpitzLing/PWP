"""Background worker for nutrition report generation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pika

from dbms import create_app
from dbms.extensions import db
from dbms.models import ReportJob, Recipe

STANDARD_INTAKE = {
    "calories": 700.0,
    "carbs": 80.0,
    "protein": 45.0,
    "fat": 25.0,
}


def _escape_pdf_text(text: str) -> str:
    """Escape text so it is safe to write inside a PDF text stream."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf_bytes(lines: list[str]) -> bytes:
    """Build a minimal single-page PDF document from text lines."""
    content_lines = ["BT", "/F1 12 Tf", "14 TL", "50 800 Td"]

    for index, line in enumerate(lines):
        safe_line = _escape_pdf_text(line)
        if index == 0:
            content_lines.append(f"({safe_line}) Tj")
        else:
            content_lines.append("T*")
            content_lines.append(f"({safe_line}) Tj")

    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1")

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        )
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        b"<< /Length "
        + str(len(content)).encode("ascii")
        + b" >>\nstream\n"
        + content
        + b"\nendstream"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            b"trailer\n"
            + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
            + b"startxref\n"
            + f"{xref_offset}\n".encode("ascii")
            + b"%%EOF\n"
        )
    )

    return bytes(pdf)


def _calculate_recipe_totals(recipe: Recipe) -> dict[str, float]:
    """Calculate nutrition totals for a single recipe."""
    totals = {"calories": 0.0, "carbs": 0.0, "protein": 0.0, "fat": 0.0}

    for assoc in recipe.ingredients:
        ingredient = assoc.ingredient
        ratio = (assoc.amount or 0.0) / 100.0

        if ingredient.calories is not None:
            totals["calories"] += ingredient.calories * ratio
        if ingredient.carbs is not None:
            totals["carbs"] += ingredient.carbs * ratio
        if ingredient.protein is not None:
            totals["protein"] += ingredient.protein * ratio
        if ingredient.fat is not None:
            totals["fat"] += ingredient.fat * ratio

    return {key: round(value, 2) for key, value in totals.items()}


def calculate_totals(recipes: list[Recipe]) -> dict[str, float]:
    """Calculate nutrition totals for a collection of recipes."""
    totals = {"calories": 0.0, "carbs": 0.0, "protein": 0.0, "fat": 0.0}

    for recipe in recipes:
        recipe_totals = _calculate_recipe_totals(recipe)
        for key in totals:
            totals[key] += recipe_totals[key]

    return {key: round(value, 2) for key, value in totals.items()}


def compare_to_standard(
    totals: dict[str, float],
) -> dict[str, dict[str, float]]:
    """Compare calculated totals against the standard intake baseline."""
    comparison = {}

    for key, standard_value in STANDARD_INTAKE.items():
        total_value = totals.get(key, 0.0)
        comparison[key] = {
            "total": round(total_value, 2),
            "standard": round(standard_value, 2),
            "difference": round(total_value - standard_value, 2),
            "percent": (
                round((total_value / standard_value) * 100, 2)
                if standard_value
                else 0.0
            ),
        }

    return comparison


def _build_report_lines(job: ReportJob, recipes: list[Recipe]) -> list[str]:
    """Build the text content that will be written to the PDF."""
    totals = calculate_totals(recipes)
    comparison = compare_to_standard(totals)

    lines = [
        "Nutrition Report",
        f"Report Job ID: {job.id}",
        f"User ID: {job.user_id}",
        f"Created At: {job.created_at.isoformat()}",
        "",
        "Selected Recipes:",
    ]

    for recipe in recipes:
        lines.append(f"- {recipe.id}: {recipe.title}")

    lines.extend(
        [
            "",
            "Total Nutrition:",
            f"Calories: {totals['calories']}",
            f"Carbs: {totals['carbs']}",
            f"Protein: {totals['protein']}",
            f"Fat: {totals['fat']}",
            "",
            "Comparison to Standard Intake:",
        ]
    )

    for key in ("calories", "carbs", "protein", "fat"):
        item = comparison[key]
        lines.append(
            f"{key.title()}: total={item['total']} standard={item['standard']} "
            f"difference={item['difference']} percent={item['percent']}%"
        )

    return lines


def _render_pdf(job: ReportJob, recipes: list[Recipe], output_path: str) -> None:
    """Render the PDF file for a completed job."""
    lines = _build_report_lines(job, recipes)
    pdf_bytes = _build_pdf_bytes(lines)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(pdf_bytes)


def _load_recipes(recipe_ids: list[int]) -> list[Recipe]:
    """Load the recipes referenced by the job."""
    recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all()
    recipe_map = {recipe.id: recipe for recipe in recipes}
    ordered_recipes = []

    for recipe_id in recipe_ids:
        recipe = recipe_map.get(recipe_id)
        if recipe is None:
            raise ValueError(f"Recipe {recipe_id} not found.")
        ordered_recipes.append(recipe)

    return ordered_recipes


def process_job(job: ReportJob, instance_path: str) -> ReportJob:
    """Process a single pending report job."""
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.session.commit()

    try:
        recipe_ids = json.loads(job.recipe_ids or "[]")
        recipes = _load_recipes(recipe_ids)
        output_path = os.path.join(
            instance_path, "reports", f"report-{job.id}.pdf"
        )
        _render_pdf(job, recipes, output_path)

        totals = calculate_totals(recipes)
        comparison = compare_to_standard(totals)
        job.total_calories = totals["calories"]
        job.total_carbs = totals["carbs"]
        job.total_protein = totals["protein"]
        job.total_fat = totals["fat"]
        job.comparison_json = json.dumps(comparison)
        job.output_file_path = output_path
        job.status = "done"
        job.finished_at = datetime.now(timezone.utc)
        job.error_message = None
        db.session.commit()
    except Exception as exc:  # pragma: no cover - defensive background failure
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()

    return job


def handle_report_job(ch, method, properties, body, instance_path: str):
    """Handle a single RabbitMQ message from the report_jobs queue."""
    job = None

    try:
        payload = json.loads(body.decode("utf-8"))
        job_id = payload["job_id"]
        job = ReportJob.query.get(job_id)

        if job is None:
            raise ValueError(f"Report job {job_id} not found.")

        process_job(job, instance_path)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:  # pragma: no cover - defensive consumer failure
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            db.session.commit()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def run_worker(poll_interval: int = 5) -> None:
    """Consume report jobs from the RabbitMQ report_jobs queue."""
    del poll_interval

    app = create_app()
    rabbitmq_url = os.getenv(
        "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F"
    )

    with app.app_context():
        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue="report_jobs", durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue="report_jobs",
            on_message_callback=lambda ch, method, properties, body: handle_report_job(
                ch, method, properties, body, app.instance_path
            ),
        )
        channel.start_consuming()


if __name__ == "__main__":
    run_worker()
