"""Claude API ATS resume optimizer — up to 3 rewrite passes."""
import json
import anthropic
from loguru import logger
from src import config
from src.phase2_resume.scorer import calculate_ats_score

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

ATS_OPTIMIZER_SYSTEM = """
You are an expert ATS resume optimizer. Rewrite the provided resume section to:
1. Mirror exact keywords from the job description (verbatim where natural)
2. Quantify achievements wherever possible
3. Use action verbs that match the JD's language
4. Keep all facts true — never invent experience

Output ONLY the rewritten resume text. No commentary.
"""

ATS_OPTIMIZER_USER = """
JOB DESCRIPTION:
{job_description}

CURRENT RESUME SECTION:
{resume_section}

TARGET ATS SCORE: 85+
Current ATS score: {current_score}
Gaps: {gaps}

Rewrite to close the gaps.
"""

MAX_PASSES = 3


def optimize_resume(resume_text: str, job: dict) -> tuple[str, int]:
    """
    Run up to MAX_PASSES rewrite attempts.
    Returns (final_resume_text, final_ats_score).
    """
    job_description = job.get("description", "")
    current_text = resume_text
    current_score, missing = calculate_ats_score(current_text, job_description)

    logger.info(f"ATS optimization start — job {job['id']}, initial score {current_score}")

    for pass_num in range(1, MAX_PASSES + 1):
        if current_score >= config.ATS_TARGET_SCORE:
            logger.info(f"Target reached at pass {pass_num - 1}: score {current_score}")
            break

        logger.info(f"Pass {pass_num}/{MAX_PASSES} — current score {current_score}, gaps: {missing[:10]}")

        prompt = ATS_OPTIMIZER_USER.format(
            job_description=job_description,
            resume_section=current_text,
            current_score=current_score,
            gaps=", ".join(missing[:20]),
        )
        response = _client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=2000,
            system=ATS_OPTIMIZER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        rewritten = response.content[0].text.strip()
        new_score, missing = calculate_ats_score(rewritten, job_description)

        if new_score >= current_score:
            current_text = rewritten
            current_score = new_score
        else:
            logger.warning(f"Pass {pass_num} made score worse ({new_score} < {current_score}), keeping previous")

    logger.info(f"ATS optimization done — job {job['id']}, final score {current_score}")
    return current_text, current_score
