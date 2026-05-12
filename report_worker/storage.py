"""Thread-safe in-memory job store for the aux report service."""

import threading
from datetime import datetime, timezone
from typing import Optional


_lock = threading.Lock()
_jobs: dict[int, dict] = {}
_next_id = 1


def create_job(recipe_ids: list[int]) -> dict:
    """Create a new pending job.  Returns the job dict."""
    global _next_id
    with _lock:
        job_id = _next_id
        _next_id += 1
        _jobs[job_id] = {
            "id": job_id,
            "recipe_ids": recipe_ids,
            "status": "pending",
            "total_calories": None,
            "total_carbs": None,
            "total_protein": None,
            "total_fat": None,
            "comparison_json": None,
            "pdf_path": None,
            "error_message": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }
        return dict(_jobs[job_id])


def get_job(job_id: int) -> Optional[dict]:
    """Return a copy of the job, or None."""
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def update_job(
    job_id: int,
    *,
    status: Optional[str] = None,
    total_calories: Optional[float] = None,
    total_carbs: Optional[float] = None,
    total_protein: Optional[float] = None,
    total_fat: Optional[float] = None,
    comparison_json: Optional[str] = None,
    pdf_path: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """Update fields on an existing job."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        if status is not None:
            job["status"] = status
        if total_calories is not None:
            job["total_calories"] = total_calories
        if total_carbs is not None:
            job["total_carbs"] = total_carbs
        if total_protein is not None:
            job["total_protein"] = total_protein
        if total_fat is not None:
            job["total_fat"] = total_fat
        if comparison_json is not None:
            job["comparison_json"] = comparison_json
        if pdf_path is not None:
            job["pdf_path"] = pdf_path
        if error_message is not None:
            job["error_message"] = error_message
        if status == "done" or status == "failed":
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
