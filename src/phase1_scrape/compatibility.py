"""Claude API compatibility scoring — returns jobs with score >= threshold."""
import json
import anthropic
from loguru import logger
from src import config

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

COMPATIBILITY_SYSTEM = """
You are a professional career advisor. Given a job description and a candidate profile,
output ONLY a JSON object: {"score": <int 0-100>, "reasons": ["...", "..."], "gaps": ["..."]}
No preamble. No markdown fences.
"""

COMPATIBILITY_USER = """
JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
{candidate_profile}

Score the compatibility. Be strict: 75+ means genuinely strong match.
"""


def _score_one(job: dict, candidate_profile: str) -> dict:
    prompt = COMPATIBILITY_USER.format(
        job_description=job.get("description", ""),
        candidate_profile=candidate_profile,
    )
    response = _client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        system=COMPATIBILITY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    raw = raw.strip("```json").strip("```").strip()
    return json.loads(raw)


def score_jobs(
    jobs: list[dict],
    candidate_profile: str,
    threshold: int = config.COMPATIBILITY_THRESHOLD,
) -> list[dict]:
    """Score all jobs and return those meeting the threshold, with score attached."""
    qualified = []
    for job in jobs:
        try:
            result = _score_one(job, candidate_profile)
            score = result.get("score", 0)
            job["compatibility_score"] = score
            job["compatibility_reasons"] = result.get("reasons", [])
            job["compatibility_gaps"] = result.get("gaps", [])
            logger.info(f"Job '{job['title']}' @ {job['company']} — score {score}")
            if score >= threshold:
                qualified.append(job)
        except Exception as e:
            logger.error(f"Scoring failed for job {job.get('id')}: {e}")
            job["compatibility_score"] = 0

    logger.info(f"Compatibility filter: {len(qualified)}/{len(jobs)} jobs qualified (>= {threshold})")
    return qualified
