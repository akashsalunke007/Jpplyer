"""OpenAI ATS resume optimizer — up to 3 rewrite passes."""
import re
import time
from openai import OpenAI, RateLimitError
from loguru import logger
from src import config
from src.phase2_resume.scorer import calculate_ats_score

_client = OpenAI(api_key=config.OPENAI_API_KEY)

ATS_SYSTEM = """
You are an expert ATS resume optimizer. Rewrite the provided resume to:
1. Mirror exact keywords from the job description (verbatim where natural)
2. Quantify achievements wherever possible
3. Use action verbs that match the JD's language
4. Keep all facts true — never invent experience

Output ONLY the rewritten resume text. No commentary. No markdown fences.
"""

ATS_USER = """
JOB DESCRIPTION:
{job_description}

CURRENT RESUME:
{resume_section}

TARGET ATS SCORE: 85+
Current ATS score: {current_score}
Missing keywords to add naturally: {gaps}

Rewrite the resume to close these gaps.
"""

MAX_PASSES = 3


def _generate(prompt_user: str) -> str:
    for attempt in range(1, 4):
        try:
            response = _client.chat.completions.create(
                model=config.OPENAI_MODEL,
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": ATS_SYSTEM},
                    {"role": "user", "content": prompt_user},
                ],
            )
            return response.choices[0].message.content.strip()
        except RateLimitError:
            if attempt < 3:
                wait = 20 * attempt
                logger.info(f"Rate limit — waiting {wait}s (attempt {attempt}/3)...")
                time.sleep(wait)
            else:
                raise


def optimize_resume(resume_text: str, job: dict) -> tuple[str, int]:
    """
    Run up to MAX_PASSES OpenAI rewrite attempts.
    Returns (final_resume_text, final_ats_score).
    """
    job_description = job.get("description", "")
    current_text = resume_text
    current_score, missing = calculate_ats_score(current_text, job_description)

    logger.info(f"ATS start — job {job['id']}, initial score {current_score}")

    for pass_num in range(1, MAX_PASSES + 1):
        if current_score >= config.ATS_TARGET_SCORE:
            logger.info(f"Target {config.ATS_TARGET_SCORE} reached before pass {pass_num}")
            break

        logger.info(f"Pass {pass_num}/{MAX_PASSES} — score {current_score}, top gaps: {missing[:8]}")

        prompt = ATS_USER.format(
            job_description=job_description[:3000],
            resume_section=current_text,
            current_score=current_score,
            gaps=", ".join(missing[:20]),
        )

        try:
            rewritten = _generate(prompt)
            rewritten = re.sub(r"^```[a-z]*\n?", "", rewritten).strip("` \n")

            new_score, new_missing = calculate_ats_score(rewritten, job_description)
            if new_score >= current_score:
                current_text = rewritten
                current_score = new_score
                missing = new_missing
            else:
                logger.warning(f"Pass {pass_num} regressed ({new_score} < {current_score}) — keeping previous")
        except Exception as e:
            logger.error(f"OpenAI ATS pass {pass_num} failed: {e}")
            break

    logger.info(f"ATS done — job {job['id']}, final score {current_score}")
    return current_text, current_score
