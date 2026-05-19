"""Tests for ATS scorer and Gemini optimizer."""
import pytest
from unittest.mock import patch, MagicMock
from src.phase2_resume.scorer import calculate_ats_score
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
    "Built microservices. Strong testing skills. REST APIs, CI/CD pipelines."
)


# ── scorer tests ─────────────────────────────────────────────────────────────

def test_scorer_low_match():
    score, missing = calculate_ats_score(RESUME_LOW, JOB["description"])
    assert score < 50
    assert len(missing) > 0


def test_scorer_high_match():
    score, missing = calculate_ats_score(RESUME_HIGH, JOB["description"])
    assert score >= 60


def test_scorer_returns_list_of_missing():
    _, missing = calculate_ats_score(RESUME_LOW, JOB["description"])
    assert isinstance(missing, list)
    assert "python" in missing or "fastapi" in missing or "docker" in missing


def test_scorer_empty_jd():
    score, missing = calculate_ats_score(RESUME_HIGH, "")
    assert score == 50   # default when no keywords
    assert missing == []


# ── Gemini optimizer tests ───────────────────────────────────────────────────

def _mock_gemini(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


def test_optimizer_returns_improved_text():
    with patch("src.phase2_resume.ats_optimizer._model") as mock_model:
        mock_model.generate_content.return_value = _mock_gemini(RESUME_HIGH)
        result_text, result_score = optimize_resume(RESUME_LOW, JOB)

    assert isinstance(result_text, str)
    assert len(result_text) > 0
    assert isinstance(result_score, int)
    assert result_score >= 0


def test_optimizer_does_not_downgrade():
    """If Gemini returns worse text, keep the original."""
    with patch("src.phase2_resume.ats_optimizer._model") as mock_model:
        mock_model.generate_content.return_value = _mock_gemini("I once coded a bit.")
        result_text, result_score = optimize_resume(RESUME_HIGH, JOB)

    # Score must be at least as good as RESUME_HIGH's original score
    original_score, _ = calculate_ats_score(RESUME_HIGH, JOB["description"])
    assert result_score >= calculate_ats_score("I once coded a bit.", JOB["description"])[0]


def test_optimizer_handles_api_error():
    with patch("src.phase2_resume.ats_optimizer._model") as mock_model:
        mock_model.generate_content.side_effect = Exception("quota exceeded")
        result_text, result_score = optimize_resume(RESUME_LOW, JOB)

    # Should return original text unchanged on total failure
    assert result_text == RESUME_LOW


def test_optimizer_strips_markdown_fences():
    fenced = f"```\n{RESUME_HIGH}\n```"
    with patch("src.phase2_resume.ats_optimizer._model") as mock_model:
        mock_model.generate_content.return_value = _mock_gemini(fenced)
        result_text, _ = optimize_resume(RESUME_LOW, JOB)

    assert "```" not in result_text
