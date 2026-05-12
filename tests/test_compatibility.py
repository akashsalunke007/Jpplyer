"""Tests for criteria_filter and compatibility scoring."""
import pytest
from unittest.mock import patch, MagicMock
from src.phase1_scrape.criteria_filter import filter_jobs, DEFAULT_CRITERIA
from src.phase1_scrape.compatibility import score_jobs

SAMPLE_JOBS = [
    {
        "id": "j1", "title": "Senior Python Developer", "company": "Acme",
        "location": "Pune", "description": "Python, Django, REST APIs", "url": "https://x.com/j1",
        "salary": "", "job_type": "FULLTIME", "source": "linkedin",
    },
    {
        "id": "j2", "title": "Marketing Manager", "company": "Corp",
        "location": "Mumbai", "description": "Marketing campaigns", "url": "https://x.com/j2",
        "salary": "", "job_type": "FULLTIME", "source": "linkedin",
    },
    {
        "id": "j3", "title": "React Frontend Engineer", "company": "Startup",
        "location": "Pune", "description": "React, TypeScript", "url": "https://x.com/j3",
        "salary": "", "job_type": "PARTTIME", "source": "linkedin",
    },
]


def test_filter_passes_matching_jobs():
    result = filter_jobs(SAMPLE_JOBS)
    ids = [j["id"] for j in result]
    assert "j1" in ids


def test_filter_drops_excluded_title():
    result = filter_jobs(SAMPLE_JOBS)
    ids = [j["id"] for j in result]
    assert "j2" not in ids


def test_filter_custom_location():
    result = filter_jobs(SAMPLE_JOBS, criteria={"locations": ["pune"]})
    ids = [j["id"] for j in result]
    assert all(j["location"].lower() == "pune" for j in result)


def test_filter_excludes_company():
    result = filter_jobs(SAMPLE_JOBS, criteria={"exclude_companies": ["Acme"]})
    ids = [j["id"] for j in result]
    assert "j1" not in ids


def test_score_jobs_filters_by_threshold():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"score": 80, "reasons": ["good match"], "gaps": []}')]

    with patch("src.phase1_scrape.compatibility._client") as mock_client:
        mock_client.messages.create.return_value = mock_response
        qualified = score_jobs(SAMPLE_JOBS[:1], "test profile", threshold=75)

    assert len(qualified) == 1
    assert qualified[0]["compatibility_score"] == 80


def test_score_jobs_excludes_low_score():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"score": 50, "reasons": [], "gaps": ["no match"]}')]

    with patch("src.phase1_scrape.compatibility._client") as mock_client:
        mock_client.messages.create.return_value = mock_response
        qualified = score_jobs(SAMPLE_JOBS[:1], "test profile", threshold=75)

    assert len(qualified) == 0
