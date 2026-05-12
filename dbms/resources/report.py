"""API resources for nutrition report jobs."""

import os
from datetime import datetime, timezone

from flask import Response, request, send_file, url_for
from flask_restful import Resource
from jsonschema import ValidationError, validate
from werkzeug.exceptions import (
    BadRequest,
    Conflict,
    Forbidden,
    NotFound,
    ServiceUnavailable,
    UnsupportedMediaType,
)

from dbms.auth import api_key_required
from dbms.extensions import db
from dbms.models import ReportJob, Recipe
from dbms.utils import publish_report_job


class Report(Resource):
    """Resource for creating nutrition report jobs."""

    @api_key_required
    def post(self, user):
        """Create a report job for selected recipe ids."""
        if request.current_user.id != user.id:
            raise Forbidden(
                description="You can only create reports for your own account."
            )

        if not request.json:
            raise UnsupportedMediaType(
                description="Request payload must be JSON."
            )

        try:
            validate(request.json, ReportJob.json_schema())
        except ValidationError as exc:
            raise BadRequest(description=str(exc)) from exc

        recipe_ids = request.json["recipe_ids"]

        for recipe_id in recipe_ids:
            recipe = db.session.get(Recipe, recipe_id)
            if recipe is None:
                raise NotFound(description=f"Recipe {recipe_id} not found.")
            if recipe.created_by != user.id:
                raise Forbidden(
                    description="All recipe ids must belong to the user."
                )

        job = ReportJob(
            user_id=user.id,
            recipe_ids="[]",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        job.deserialize({"recipe_ids": recipe_ids})
        db.session.add(job)
        db.session.commit()
        try:
            publish_report_job(job.id, user.id, recipe_ids)
        except RuntimeError as exc:
            raise ServiceUnavailable(description=str(exc)) from exc

        return Response(
            status=202,
            headers={
                "Location": url_for(
                    "api.reportstatus", user=user, report_job_id=job.id
                )
            },
        )


class ReportStatus(Resource):
    """Resource for report job status and metadata."""

    @api_key_required
    def get(self, user, report_job_id):
        """Return status information for a report job."""
        job = db.session.get(ReportJob, report_job_id)
        if job is None:
            raise NotFound(
                description=f"Report job {report_job_id} not found."
            )

        if request.current_user.id != user.id or job.user_id != user.id:
            raise Forbidden(
                description="You can only access your own report jobs."
            )

        return job.serialize()

    def put(self, user, report_job_id):
        """Called by the report worker to submit job results.

        Auth: accepts either the worker API key (service-to-service) or a
        regular user API key (with ownership check).
        """
        import base64

        from flask import current_app

        job = db.session.get(ReportJob, report_job_id)
        if job is None:
            raise NotFound(
                description=f"Report job {report_job_id} not found."
            )

        # Auth: worker key bypasses user ownership check
        worker_key = current_app.config.get("WORKER_API_KEY", "")
        api_key = request.headers.get("dbms-api-key", "")

        is_worker = bool(api_key and api_key == worker_key)
        if not is_worker:
            from dbms.auth import authenticate_user_by_key

            current_user = authenticate_user_by_key(api_key)
            if (
                current_user is None
                or current_user.id != user.id
                or job.user_id != user.id
            ):
                raise Forbidden(description="Access denied.")

        if not request.json:
            raise UnsupportedMediaType(
                description="Request payload must be JSON."
            )

        status = request.json.get("status", "done")
        job.status = status
        job.finished_at = datetime.now(timezone.utc)

        if status == "failed":
            job.error_message = request.json.get(
                "error_message", "Unknown error"
            )
        else:
            job.total_calories = float(
                request.json.get("total_calories", 0.0)
            )
            job.total_carbs = float(
                request.json.get("total_carbs", 0.0)
            )
            job.total_protein = float(
                request.json.get("total_protein", 0.0)
            )
            job.total_fat = float(
                request.json.get("total_fat", 0.0)
            )
            job.comparison_json = request.json.get("comparison_json", "{}")

            pdf_b64 = request.json.get("pdf_base64")
            filename = request.json.get(
                "filename", f"report-{report_job_id}.pdf"
            )

            if pdf_b64:
                output_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "instance", "reports",
                )
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, filename)
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(pdf_b64))
                job.output_file_path = output_path

        db.session.commit()
        return Response(status=204)


class ReportDownload(Resource):
    """Resource for downloading a completed nutrition report."""

    @api_key_required
    def get(self, user, report_job_id):
        """Download the generated report PDF."""
        job = db.session.get(ReportJob, report_job_id)
        if job is None:
            raise NotFound(
                description=f"Report job {report_job_id} not found."
            )

        if request.current_user.id != user.id or job.user_id != user.id:
            raise Forbidden(
                description="You can only access your own report jobs."
            )

        if job.status != "done":
            raise Conflict(description="Report is not ready yet.")

        if not job.output_file_path or not os.path.exists(
            job.output_file_path
        ):
            raise NotFound(description="Generated report file was not found.")

        return send_file(
            job.output_file_path,
            as_attachment=True,
            download_name=os.path.basename(job.output_file_path),
        )
