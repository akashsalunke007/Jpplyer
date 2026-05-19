"""OpenAI compatibility scoring — returns jobs with score >= threshold."""
import json
import re
import time
from openai import OpenAI, RateLimitError
from loguru import logger
from src import config

_client = OpenAI(api_key=config.OPENAI_API_KEY)

COMPATIBILITY_SYSTEM = """
You are a professional career advisor. Given a job description and a candidate profile,
output ONLY a JSON object with no preamble and no markdown fences:
{"score": <int 0-100>, "reasons": ["...", "..."], "gaps": ["..."]}
Be strict: 75+ means genuinely strong match.
"""

COMPATIBILITY_USER = """
JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
{candidate_profile}
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _score_one(job: dict, candidate_profile: str) -> dict:
    for attempt in range(1, 4):
        try:
            response = _client.chat.completions.create(
                model=config.OPENAI_MODEL,
                max_tokens=config.OPENAI_MAX_TOKENS,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": COMPATIBILITY_SYSTEM},
                    {"role": "user", "content": COMPATIBILITY_USER.format(
                        job_description=job.get("description", "")[:3000],
                        candidate_profile=candidate_profile,
                    )},
                ],
            )
            raw = _strip_fences(response.choices[0].message.content)
            return json.loads(raw)
        except RateLimitError:
            if attempt < 3:
                wait = 20 * attempt
                logger.info(f"Rate limit — waiting {wait}s (attempt {attempt}/3)...")
                time.sleep(wait)
            else:
                raise


def score_jobs(
    jobs: list[dict],
    candidate_profile: str,
    threshold: int = config.COMPATIBILITY_THRESHOLD,
) -> list[dict]:
    """Score jobs via OpenAI and return those meeting the threshold.
    Caps at MAX_JOBS_TO_SCORE per run to manage API usage.
    """
    batch = jobs[:config.MAX_JOBS_TO_SCORE]
    if len(jobs) > config.MAX_JOBS_TO_SCORE:
        logger.info(f"Capping scoring at {config.MAX_JOBS_TO_SCORE} jobs (set MAX_JOBS_TO_SCORE to change)")

    qualified = []
    for job in batch:
        try:
            result = _score_one(job, candidate_profile)
            score = result.get("score", 0)
            job["compatibility_score"] = score
            job["compatibility_reasons"] = result.get("reasons", [])
            job["compatibility_gaps"] = result.get("gaps", [])
            logger.info(f"'{job['title']}' @ {job['company']} — score {score}")
            if score >= threshold:
                qualified.append(job)
        except Exception as e:
            logger.error(f"Scoring failed for job {job.get('id')}: {e}")
            job["compatibility_score"] = 0

    logger.info(f"Compatibility filter: {len(qualified)}/{len(batch)} qualified (>= {threshold})")
    return qualified
