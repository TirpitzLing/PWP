"""Comprehensive tests for the aux report service (storage, worker, app)."""

import json
import os
import sys
import threading
import time as _time_module
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import storage
import worker
import app as app_module
from app import create_app


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _clear_storage():
    for key in list(storage._jobs.keys()):
        del storage._jobs[key]
    storage._next_id = 1


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def sample_totals():
    return {"calories": 800.0, "carbs": 90.0, "protein": 50.0, "fat": 30.0}


@pytest.fixture
def sample_comparison():
    return {
        "calories": {
            "total": 800.0,
            "standard": 700.0,
            "difference": 100.0,
            "percent": 114.29,
        },
        "carbs": {
            "total": 90.0,
            "standard": 80.0,
            "difference": 10.0,
            "percent": 112.5,
        },
        "protein": {
            "total": 50.0,
            "standard": 45.0,
            "difference": 5.0,
            "percent": 111.11,
        },
        "fat": {
            "total": 30.0,
            "standard": 25.0,
            "difference": 5.0,
            "percent": 120.0,
        },
    }


# ============================================================================
# storage.py
# ============================================================================


class TestStorage:
    def test_create_job(self):
        job = storage.create_job([1, 2, 3])
        assert job["id"] == 1
        assert job["recipe_ids"] == [1, 2, 3]
        assert job["status"] == "pending"
        assert job["total_calories"] is None
        assert job["created_at"] is not None
        assert job["finished_at"] is None
        assert job["error_message"] is None
        assert job["pdf_path"] is None

    def test_create_job_increments_ids(self):
        j1 = storage.create_job([1])
        j2 = storage.create_job([2])
        assert j1["id"] == 1
        assert j2["id"] == 2

    def test_get_job_exists(self):
        storage.create_job([1])
        job = storage.get_job(1)
        assert job is not None
        assert job["id"] == 1
        assert job is not storage._jobs[1]

    def test_get_job_missing(self):
        assert storage.get_job(999) is None

    def test_update_job_status_running(self):
        storage.create_job([1])
        storage.update_job(1, status="running")
        assert storage.get_job(1)["status"] == "running"

    def test_update_job_done_sets_finished_at(self):
        storage.create_job([1])
        storage.update_job(1, status="done")
        job = storage.get_job(1)
        assert job["status"] == "done"
        assert job["finished_at"] is not None

    def test_update_job_failed_sets_error(self):
        storage.create_job([1])
        storage.update_job(1, status="failed", error_message="boom")
        job = storage.get_job(1)
        assert job["status"] == "failed"
        assert job["error_message"] == "boom"
        assert job["finished_at"] is not None

    def test_update_job_all_fields(self):
        storage.create_job([1])
        storage.update_job(
            1,
            status="done",
            total_calories=500.0,
            total_carbs=60.0,
            total_protein=35.0,
            total_fat=20.0,
            comparison_json='{"k":"v"}',
            pdf_path="/tmp/t.pdf",
        )
        job = storage.get_job(1)
        assert job["total_calories"] == 500.0
        assert job["total_carbs"] == 60.0
        assert job["comparison_json"] == '{"k":"v"}'
        assert job["pdf_path"] == "/tmp/t.pdf"

    def test_update_job_missing_does_nothing(self):
        storage.update_job(999, status="done")
        assert storage.get_job(999) is None

    def test_update_job_partial_fields(self):
        """Only specified fields are updated."""
        storage.create_job([1])
        storage.update_job(1, total_calories=42.0)
        job = storage.get_job(1)
        assert job["total_calories"] == 42.0
        assert job["status"] == "pending"  # unchanged
        assert job["total_carbs"] is None  # unchanged


# ============================================================================
# worker.py — _escape_pdf_text
# ============================================================================


class TestEscapePdfText:
    def test_no_special(self):
        assert worker._escape_pdf_text("hello") == "hello"

    def test_backslash(self):
        assert worker._escape_pdf_text(r"a\b") == r"a\\b"

    def test_parens(self):
        assert worker._escape_pdf_text("a(b)c") == r"a\(b\)c"

    def test_combined(self):
        assert worker._escape_pdf_text(r"a\b(c)") == r"a\\b\(c\)"


# ============================================================================
# worker.py — build_pdf_bytes
# ============================================================================


class TestBuildPdfBytes:
    def test_valid_pdf(self, sample_totals, sample_comparison):
        pdf = worker.build_pdf_bytes(
            1, ["Recipe A", "Recipe B"], sample_totals, sample_comparison
        )
        assert isinstance(pdf, bytes)
        assert pdf.startswith(b"%PDF-1.4")
        assert b"%%EOF" in pdf
        assert b"Nutrition Report" in pdf
        assert b"Recipe A" in pdf
        assert b"Recipe B" in pdf
        assert b"vs Standard" in pdf
        assert b"114.29%" in pdf

    def test_single_recipe(self, sample_totals, sample_comparison):
        pdf = worker.build_pdf_bytes(
            2, ["Only"], sample_totals, sample_comparison
        )
        assert b"Only" in pdf

    def test_no_titles(self, sample_totals, sample_comparison):
        pdf = worker.build_pdf_bytes(3, [], sample_totals, sample_comparison)
        assert isinstance(pdf, bytes)
        assert pdf.startswith(b"%PDF-1.4")


# ============================================================================
# worker.py — compare_to_standard
# ============================================================================


class TestCompareToStandard:
    def test_basic(self):
        totals = {"calories": 350.0, "carbs": 40.0, "protein": 22.5, "fat": 12.5}
        result = worker.compare_to_standard(totals)
        assert result["calories"]["total"] == 350.0
        assert result["calories"]["standard"] == 700.0
        assert result["calories"]["difference"] == -350.0
        assert result["calories"]["percent"] == 50.0

    def test_zero(self):
        totals = {"calories": 0.0, "carbs": 0.0, "protein": 0.0, "fat": 0.0}
        result = worker.compare_to_standard(totals)
        assert result["calories"]["percent"] == 0.0

    def test_exceeds(self):
        totals = {"calories": 1400.0, "carbs": 160.0, "protein": 90.0, "fat": 50.0}
        result = worker.compare_to_standard(totals)
        assert result["calories"]["difference"] == 700.0
        assert result["calories"]["percent"] == 200.0

    def test_four_keys(self):
        totals = {"calories": 1, "carbs": 2, "protein": 3, "fat": 4}
        result = worker.compare_to_standard(totals)
        assert set(result.keys()) == {"calories", "carbs", "protein", "fat"}


# ============================================================================
# worker.py — process_job (mocked)
# ============================================================================


class TestProcessJob:
    def test_success(self, tmp_path):
        worker.PDF_DIR = str(tmp_path)
        storage.create_job([1, 2])

        def _title(rid):
            return {1: "A", 2: "B"}[rid]

        def _nutrition(rid):
            return {
                1: {"calories": 500, "carbs": 60, "protein": 25, "fat": 20},
                2: {"calories": 200, "carbs": 20, "protein": 10, "fat": 5},
            }[rid]

        with (
            patch.object(worker, "_fetch_recipe_title", _title),
            patch.object(worker, "_fetch_nutrition", _nutrition),
        ):
            worker.process_job(1, [1, 2])

        job = storage.get_job(1)
        assert job["status"] == "done"
        assert job["total_calories"] == 700.0
        assert job["total_protein"] == 35.0
        assert os.path.isfile(job["pdf_path"])

    def test_failure(self, tmp_path):
        worker.PDF_DIR = str(tmp_path)
        storage.create_job([1])

        with patch.object(
            worker, "_fetch_recipe_title", side_effect=RuntimeError("down")
        ):
            worker.process_job(1, [1])

        job = storage.get_job(1)
        assert job["status"] == "failed"
        assert "down" in job["error_message"]


# ============================================================================
# worker.py — HTTP helpers (mocked)
# ============================================================================


class TestFetchNutrition:
    def test_parsed(self):
        mock = MagicMock()
        mock.json.return_value = {
            "total_calories": 300,
            "total_carbs": 40,
            "total_protein": 25,
            "total_fat": 15,
        }
        with patch.object(worker.requests, "get", return_value=mock):
            r = worker._fetch_nutrition(1)
        assert r == {"calories": 300.0, "carbs": 40.0, "protein": 25.0, "fat": 15.0}

    def test_defaults(self):
        mock = MagicMock()
        mock.json.return_value = {"total_calories": 100}
        with patch.object(worker.requests, "get", return_value=mock):
            r = worker._fetch_nutrition(1)
        assert r["calories"] == 100.0
        assert r["carbs"] == 0.0


class TestFetchRecipeTitle:
    def test_ok(self):
        mock = MagicMock()
        mock.json.return_value = {"title": "T"}
        with patch.object(worker.requests, "get", return_value=mock):
            assert worker._fetch_recipe_title(1) == "T"

    def test_fallback(self):
        mock = MagicMock()
        mock.json.return_value = {}
        with patch.object(worker.requests, "get", return_value=mock):
            assert worker._fetch_recipe_title(42) == "Recipe 42"


# ============================================================================
# worker.py — calculate_totals
# ============================================================================


class TestCalculateTotals:
    def test_sums(self):
        vals = iter(
            [
                {"calories": 100, "carbs": 10, "protein": 5, "fat": 2},
                {"calories": 200, "carbs": 20, "protein": 10, "fat": 4},
            ]
        )
        with patch.object(worker, "_fetch_nutrition", lambda _rid: next(vals)):
            r = worker.calculate_totals([1, 2])
        assert r == {"calories": 300.0, "carbs": 30.0, "protein": 15.0, "fat": 6.0}

    def test_empty(self):
        assert worker.calculate_totals([]) == {
            "calories": 0.0, "carbs": 0.0, "protein": 0.0, "fat": 0.0
        }


# ============================================================================
# worker.py — connect_with_retry
# ============================================================================


class TestConnectWithRetry:
    def test_first_success(self):
        mock = MagicMock()
        with patch.object(
            worker.pika, "BlockingConnection", return_value=mock
        ):
            assert worker.connect_with_retry(retries=3, delay=0) is mock

    def test_all_fail(self):
        with patch.object(
            worker.pika,
            "BlockingConnection",
            side_effect=RuntimeError("no"),
        ):
            with pytest.raises(RuntimeError, match="Cannot connect"):
                worker.connect_with_retry(retries=2, delay=0)


# ============================================================================
# worker.py — handle_message
# ============================================================================


class TestHandleMessage:
    def test_valid(self):
        storage.create_job([1])
        ch = MagicMock()
        body = json.dumps(
            {"type": "report.job.pending", "job_id": 1, "recipe_ids": [1]}
        ).encode()

        def _fake(job_id, recipe_ids):
            storage.update_job(job_id, status="done")

        with patch.object(worker, "process_job", _fake):
            worker.handle_message(ch, MagicMock(), MagicMock(), body)

        ch.basic_ack.assert_called_once()

    def test_wrong_type(self):
        ch = MagicMock()
        body = json.dumps({"type": "other", "job_id": 1}).encode()
        worker.handle_message(ch, MagicMock(), MagicMock(), body)
        ch.basic_ack.assert_called_once()

    def test_process_failure_caught(self):
        """process_job catches HTTP errors and marks job as failed."""
        storage.create_job([1])
        ch = MagicMock()
        body = json.dumps(
            {"type": "report.job.pending", "job_id": 1, "recipe_ids": [1]}
        ).encode()

        # Make the real process_job fail by mocking its HTTP helper
        with patch.object(
            worker,
            "_fetch_recipe_title",
            side_effect=RuntimeError("down"),
        ):
            worker.handle_message(ch, MagicMock(), MagicMock(), body)

        ch.basic_ack.assert_called_once()
        assert storage.get_job(1)["status"] == "failed"


# ============================================================================
# worker.py — _headers
# ============================================================================


class TestConnectAndConsume:
    def test_sets_up_and_starts(self):
        """connect_and_consume sets up exchange/queue and starts consuming."""
        mock_conn = MagicMock()
        mock_ch = MagicMock()
        mock_conn.channel.return_value = mock_ch

        with (
            patch.object(worker, "connect_with_retry", return_value=mock_conn),
            patch.object(mock_ch, "start_consuming") as _consume,
        ):
            worker.connect_and_consume()

        mock_ch.exchange_declare.assert_called_once()
        mock_ch.queue_declare.assert_called_once()
        mock_ch.queue_bind.assert_called_once()
        mock_ch.basic_qos.assert_called_once_with(prefetch_count=1)
        mock_ch.basic_consume.assert_called_once()
        _consume.assert_called_once()


class TestHeaders:
    def test_format(self):
        h = worker._headers()
        assert h["Content-Type"] == "application/json"
        assert "dbms-api-key" in h


# ============================================================================
# app.py — _publish_job
# ============================================================================


class TestPublishJob:
    def test_publishes_to_rabbitmq(self):
        mock_conn = MagicMock()
        mock_ch = MagicMock()

        with (
            patch.object(app_module.pika, "URLParameters", return_value="p"),
            patch.object(
                app_module.pika, "BlockingConnection", return_value=mock_conn
            ),
        ):
            mock_conn.channel.return_value = mock_ch
            app_module._publish_job(1, [1, 2])

        mock_ch.exchange_declare.assert_called_once()
        kwargs = mock_ch.basic_publish.call_args[1]
        assert kwargs["exchange"] == "report_events"
        assert kwargs["routing_key"] == "report.job.pending"

    def test_wait_timeout(self, client):
        """When the job never finishes, we get 504 after the wait loop exits."""
        with (
            patch.object(app_module, "_publish_job"),
            patch("time.sleep"),
        ):
            resp = client.post(
                "/reports/?wait=true",
                data=json.dumps({"recipe_ids": [1]}),
                content_type="application/json",
            )
        assert resp.status_code == 504


# ============================================================================
# app.py — Flask API
# ============================================================================


class TestAppCreateReport:
    def test_202(self, client):
        with patch("app._publish_job"):
            resp = client.post(
                "/reports/",
                data=json.dumps({"recipe_ids": [1, 2]}),
                content_type="application/json",
            )
        assert resp.status_code == 202
        assert resp.headers["Location"] == "/reports/1/"
        assert json.loads(resp.data)["status"] == "pending"

    def test_wait_done(self, client):
        def _finish():
            import time
            time.sleep(0.3)
            storage.update_job(1, status="done", total_calories=100.0)

        t = threading.Thread(target=_finish)
        t.start()
        with patch("app._publish_job"):
            resp = client.post(
                "/reports/?wait=true",
                data=json.dumps({"recipe_ids": [1]}),
                content_type="application/json",
            )
        t.join()
        assert resp.status_code == 200
        assert json.loads(resp.data)["status"] == "done"

    def test_wait_failed(self, client):
        def _fail():
            import time
            time.sleep(0.3)
            storage.update_job(1, status="failed", error_message="boom")

        t = threading.Thread(target=_fail)
        t.start()
        with patch("app._publish_job"):
            resp = client.post(
                "/reports/?wait=true",
                data=json.dumps({"recipe_ids": [1]}),
                content_type="application/json",
            )
        t.join()
        assert resp.status_code == 500

    def test_no_recipe_ids(self, client):
        with patch("app._publish_job"):
            assert (
                client.post(
                    "/reports/",
                    data=json.dumps({}),
                    content_type="application/json",
                ).status_code
                == 400
            )

    def test_not_a_list(self, client):
        with patch("app._publish_job"):
            assert (
                client.post(
                    "/reports/",
                    data=json.dumps({"recipe_ids": "nope"}),
                    content_type="application/json",
                ).status_code
                == 400
            )

    def test_non_int_ids(self, client):
        with patch("app._publish_job"):
            assert (
                client.post(
                    "/reports/",
                    data=json.dumps({"recipe_ids": ["a"]}),
                    content_type="application/json",
                ).status_code
                == 400
            )

    def test_no_body(self, client):
        with patch("app._publish_job"):
            assert client.post("/reports/").status_code == 400


class TestAppReportStatus:
    def test_200(self, client):
        storage.create_job([1])
        resp = client.get("/reports/1/")
        assert resp.status_code == 200
        assert json.loads(resp.data)["id"] == 1

    def test_404(self, client):
        assert client.get("/reports/999/").status_code == 404


class TestAppReportDownload:
    def test_200(self, client, tmp_path):
        p = tmp_path / "r.pdf"
        p.write_bytes(b"%PDF-1.4 fake")
        storage.create_job([1])
        storage.update_job(1, status="done", pdf_path=str(p))

        resp = client.get("/reports/1/download/")
        assert resp.status_code == 200
        assert b"fake" in resp.data

    def test_409_not_done(self, client):
        storage.create_job([1])
        assert client.get("/reports/1/download/").status_code == 409

    def test_404_missing(self, client):
        assert client.get("/reports/999/download/").status_code == 404

    def test_404_file_gone(self, client):
        storage.create_job([1])
        storage.update_job(1, status="done", pdf_path="/no/such.pdf")
        assert client.get("/reports/1/download/").status_code == 404
