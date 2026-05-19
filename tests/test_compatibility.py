"""Tests for criteria_filter and Gemini compatibility scoring."""
import pytest
from unittest.mock import patch, MagicMock
from src.phase1_scrape.criteria_filter import filter_jobs
from src.phase1_scrape.compatibility import score_jobs

SAMPLE_JOBS = [
    {
        "id": "j1", "title": "Senior Python Developer", "company": "Acme",
        "location": "Pune, India", "description": "Python, Django, REST APIs",
        "url": "https://x.com/j1", "salary": "", "job_type": "FULLTIME", "source": "linkedin",
    },
    {
        "id": "j2", "title": "Marketing Manager", "company": "Corp",
        "location": "Mumbai", "description": "Marketing campaigns",
        "url": "https://x.com/j2", "salary": "", "job_type": "FULLTIME", "source": "linkedin",
    },
    {
        "id": "j3", "title": "React Frontend Engineer", "company": "Startup",
        "location": "Pune, India", "description": "React, TypeScript",
        "url": "https://x.com/j3", "salary": "", "job_type": "PARTTIME", "source": "indeed",
    },
]


# ── criteria_filter tests ─────────────────────────────────────────────────────

def test_filter_passes_matching_jobs():
    result = filter_jobs(SAMPLE_JOBS)
    assert any(j["id"] == "j1" for j in result)


def test_filter_drops_excluded_title():
    result = filter_jobs(SAMPLE_JOBS)
    assert all(j["id"] != "j2" for j in result)


def test_filter_custom_location():
    result = filter_jobs(SAMPLE_JOBS, criteria={"locations": ["pune"]})
    assert all("pune" in j["location"].lower() for j in result)


def test_filter_excludes_company():
    result = filter_jobs(SAMPLE_JOBS, criteria={"exclude_companies": ["Acme"]})
    assert all(j["id"] != "j1" for j in result)


def test_filter_empty_input():
    assert filter_jobs([]) == []


# ── Gemini compatibility scoring tests ───────────────────────────────────────

def _mock_gemini_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


def test_score_jobs_qualifies_high_score():
    with patch("src.phase1_scrape.compatibility._model") as mock_model:
        mock_model.generate_content.return_value = _mock_gemini_response(
            '{"score": 82, "reasons": ["strong Python match"], "gaps": []}'
        )
        qualified = score_jobs(SAMPLE_JOBS[:1], "test profile", threshold=75)

    assert len(qualified) == 1
    assert qualified[0]["compatibility_score"] == 82


def test_score_jobs_excludes_low_score():
    with patch("src.phase1_scrape.compatibility._model") as mock_model:
        mock_model.generate_content.return_value = _mock_gemini_response(
            '{"score": 50, "reasons": [], "gaps": ["no Python"]}'
        )
        qualified = score_jobs(SAMPLE_JOBS[:1], "test profile", threshold=75)

    assert len(qualified) == 0


def test_score_jobs_handles_api_error_gracefully():
    with patch("src.phase1_scrape.compatibility._model") as mock_model:
        mock_model.generate_content.side_effect = Exception("API error")
        qualified = score_jobs(SAMPLE_JOBS[:1], "test profile", threshold=75)

    assert len(qualified) == 0
    assert SAMPLE_JOBS[0]["compatibility_score"] == 0


def test_score_jobs_strips_markdown_fences():
    with patch("src.phase1_scrape.compatibility._model") as mock_model:
        mock_model.generate_content.return_value = _mock_gemini_response(
            '```json\n{"score": 80, "reasons": [], "gaps": []}\n```'
        )
        qualified = score_jobs(SAMPLE_JOBS[:1], "test profile", threshold=75)

    assert len(qualified) == 1
