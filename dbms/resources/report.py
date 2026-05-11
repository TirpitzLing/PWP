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
            recipe = Recipe.query.get(recipe_id)
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
            publish_report_job(job.id, queue_name="report")
        except RuntimeError as exc:
            raise ServiceUnavailable(description=str(exc)) from exc

        return Response(
            status=202,
            headers={
                "Location": url_for(
                    "api.reportitem", user=user, report_job_id=job.id
                )
            },
        )


class ReportItem(Resource):
    """Resource for report job status and metadata."""

    @api_key_required
    def get(self, user, report_job_id):
        """Return status information for a report job."""
        job = ReportJob.query.get_or_404(report_job_id)

        if request.current_user.id != user.id or job.user_id != user.id:
            raise Forbidden(
                description="You can only access your own report jobs."
            )

        return job.serialize()


class ReportDownload(Resource):
    """Resource for downloading a completed nutrition report."""

    @api_key_required
    def get(self, user, report_job_id):
        """Download the generated report PDF."""
        job = ReportJob.query.get_or_404(report_job_id)

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
