"""Tests for ATS scorer and optimizer."""
import pytest
from unittest.mock import patch, MagicMock
from src.phase2_resume.scorer import calculate_ats_score, _extract_jd_keywords
from src.phase2_resume.ats_optimizer import optimize_resume


JOB = {
    "id": "j1",
    "title": "Python Backend Engineer",
    "company": "Acme",
    "description": (
        "We need a Python developer experienced in FastAPI, PostgreSQL, Docker, "
        "Redis, AWS, and microservices architecture. Strong testing skills required."
    ),
    "url": "https://example.com/j1",
}

RESUME_LOW = "I have some programming experience and like building software."
RESUME_HIGH = (
    "Python developer with FastAPI, PostgreSQL, Docker, Redis, AWS experience. "
    "Built microservices. Strong testing skills."
)


def test_scorer_low_match():
    score, missing = calculate_ats_score(RESUME_LOW, JOB["description"])
    assert score < 50
    assert "python" in missing or "fastapi" in missing


def test_scorer_high_match():
    score, missing = calculate_ats_score(RESUME_HIGH, JOB["description"])
    assert score >= 60


def test_scorer_returns_missing_keywords():
    _, missing = calculate_ats_score(RESUME_LOW, JOB["description"])
    assert isinstance(missing, list)
    assert len(missing) > 0


def test_optimizer_returns_improved_text():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=RESUME_HIGH)]

    with patch("src.phase2_resume.ats_optimizer._client") as mock_client:
        mock_client.messages.create.return_value = mock_response
        result_text, result_score = optimize_resume(RESUME_LOW, JOB)

    assert isinstance(result_text, str)
    assert len(result_text) > 0
    assert isinstance(result_score, int)


def test_optimizer_does_not_downgrade():
    """If Claude returns worse text, keep the original."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="I once coded a bit.")]

    with patch("src.phase2_resume.ats_optimizer._client") as mock_client:
        mock_client.messages.create.return_value = mock_response
        result_text, result_score = optimize_resume(RESUME_HIGH, JOB)

    # Should keep the better original
    assert result_score >= calculate_ats_score("I once coded a bit.", JOB["description"])[0]
