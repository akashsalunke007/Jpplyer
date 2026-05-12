"""Tests for result_logger, form_detector parsing, and browser helpers."""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from src.phase3_apply.result_logger import log_result, get_results, count_applied
from src.phase3_apply.form_detector import _parse_response

JOB = {
    "id": "test_job_001",
    "title": "Software Engineer",
    "company": "TestCo",
    "url": "https://example.com/apply",
    "compatibility_score": 82,
}


@pytest.fixture(autouse=True)
def reset_results(tmp_path, monkeypatch):
    """Use a temp results file for each test."""
    results_file = tmp_path / "results.json"
    results_file.write_text("[]")
    monkeypatch.setattr("src.phase3_apply.result_logger.config.RESULTS_FILE", results_file)
    monkeypatch.setattr("src.phase3_apply.result_logger.config.RESULTS_FILE", results_file)


def test_log_result_appends():
    log_result(JOB, "applied", ats_score=88)
    records = get_results()
    assert len(records) == 1
    assert records[0]["status"] == "applied"
    assert records[0]["ats_score"] == 88
    assert records[0]["job_id"] == "test_job_001"


def test_log_result_multiple():
    log_result(JOB, "applied", ats_score=88)
    log_result({**JOB, "id": "test_job_002"}, "failed", error="timeout")
    records = get_results()
    assert len(records) == 2


def test_count_applied():
    log_result(JOB, "applied")
    log_result({**JOB, "id": "j2"}, "failed")
    log_result({**JOB, "id": "j3"}, "needs_human")
    assert count_applied() == 3


def test_parse_response_valid():
    raw = '[{"field_label": "Name", "selector": "#name", "value": "John", "type": "text"}]'
    result = _parse_response(raw)
    assert len(result) == 1
    assert result[0]["selector"] == "#name"


def test_parse_response_with_fences():
    raw = '```json\n[{"field_label": "Email", "selector": "#email", "value": "a@b.com", "type": "text"}]\n```'
    result = _parse_response(raw)
    assert len(result) == 1


def test_parse_response_invalid_json():
    result = _parse_response("not json at all")
    assert result == []


def test_parse_response_non_list():
    result = _parse_response('{"field_label": "x"}')
    assert result == []
