"""Main pipeline loop — entry point for the job application automation system."""
import asyncio
import argparse
import json
from loguru import logger
from src import config
from src.phase1_scrape.apify_client import scrape_jobs
from src.phase1_scrape.criteria_filter import filter_jobs
from src.phase1_scrape.compatibility import score_jobs
from src.phase2_resume.storage import (
    load_base_resume_text, save_tailored_resume, tailored_exists, tailored_path
)
from src.phase2_resume.ats_optimizer import optimize_resume
from src.phase3_apply.browser import apply_to_job, HumanCheckRequired, FormFieldNotFound
from src.phase3_apply.result_logger import log_result, count_applied
from src.phase4_report.report_generator import generate_report
from src.phase4_report.email_sender import send_report
from src.notifications.sms import notify_error, notify_human_check
from src.notifications.email_alert import send_error_email, send_human_check_email


# ── Candidate profile & data ─────────────────────────────────────────────────
# Fill these with your actual details before running.
CANDIDATE_PROFILE = """
Name: [Your Name]
Current role: Software Engineer, 4 years experience
Skills: Python, FastAPI, Django, PostgreSQL, Redis, AWS (EC2/S3/Lambda), Docker, Kubernetes, Git
Education: B.E. Computer Engineering
Location: Pune, India
Preferred: Full-time, backend/fullstack roles, 12–20 LPA
"""

CANDIDATE_DATA = {
    "full_name": "[Your Name]",
    "email": "[your@email.com]",
    "phone": "[+91XXXXXXXXXX]",
    "linkedin": "https://linkedin.com/in/yourprofile",
    "github": "https://github.com/yourusername",
    "location": "Pune, India",
    "years_experience": "4",
    "current_title": "Software Engineer",
    "notice_period": "30 days",
    "expected_salary": "15 LPA",
    "cover_letter": (
        "I am excited to apply for this position. "
        "My background in Python and backend engineering aligns well with your requirements."
    ),
}
# ─────────────────────────────────────────────────────────────────────────────


def _run_phase_with_retry(job: dict, phase_name: str, phase_fn, *args, **kwargs):
    """Run phase_fn with up to 2 retries. Handles HumanCheckRequired specially."""
    for attempt in range(1, 3):
        try:
            return phase_fn(job, *args, **kwargs)
        except HumanCheckRequired:
            logger.warning(f"Human check on job {job['id']} — notifying and skipping")
            log_result(job, "needs_human")
            notify_human_check(job["id"], job.get("url", ""))
            send_human_check_email(job)
            return None
        except Exception as e:
            logger.error(f"[{phase_name}] job {job['id']} attempt {attempt} failed: {e}")
            if attempt == 2:
                log_result(job, "failed", error=str(e))
                notify_error(job["id"], phase_name, str(e))
                send_error_email(job, phase_name, e)
            else:
                import time; time.sleep(2)
    return None


async def _apply_async(job: dict, ats_score: int) -> None:
    resume = tailored_path(job["id"])
    try:
        await apply_to_job(job, resume, CANDIDATE_DATA)
        log_result(job, "applied", ats_score=ats_score)
    except HumanCheckRequired:
        log_result(job, "needs_human")
        notify_human_check(job["id"], job.get("url", ""))
        send_human_check_email(job)
    except (FormFieldNotFound, Exception) as e:
        logger.error(f"Apply failed for job {job['id']}: {e}")
        for attempt in range(1, 3):
            try:
                await apply_to_job(job, resume, CANDIDATE_DATA)
                log_result(job, "applied", ats_score=ats_score)
                return
            except Exception as retry_e:
                if attempt == 2:
                    log_result(job, "failed", ats_score=ats_score, error=str(retry_e))
                    notify_error(job["id"], "apply", str(retry_e))
                    send_error_email(job, "apply", retry_e)


def _maybe_send_report(batch_counter: list[int]) -> None:
    """Increment counter and send report every REPORT_EVERY_N_JOBS."""
    batch_counter[0] += 1
    if batch_counter[0] % config.REPORT_EVERY_N_JOBS == 0:
        batch_num = batch_counter[0] // config.REPORT_EVERY_N_JOBS
        logger.info(f"Generating batch report {batch_num}")
        try:
            html, csv_data = generate_report(batch_num)
            send_report(html, csv_data, batch_num)
        except Exception as e:
            logger.error(f"Report generation/send failed: {e}")


# ── Phase runners ─────────────────────────────────────────────────────────────

def phase_scrape() -> list[dict]:
    logger.info("=== Phase 1: Scrape ===")
    raw_jobs = scrape_jobs(platform="linkedin")
    filtered = filter_jobs(raw_jobs)
    qualified = score_jobs(filtered, CANDIDATE_PROFILE)
    config.JOBS_QUEUE_FILE.write_text(json.dumps(qualified, indent=2))
    logger.info(f"Queue written: {len(qualified)} jobs → {config.JOBS_QUEUE_FILE}")
    return qualified


def phase_resume(jobs: list[dict]) -> dict[str, int]:
    """Returns {job_id: ats_score}."""
    logger.info("=== Phase 2: Resume tailoring ===")
    base_text = load_base_resume_text()
    scores = {}
    for job in jobs:
        job_id = job["id"]
        if tailored_exists(job_id):
            logger.info(f"Tailored resume already exists for {job_id}, skipping")
            scores[job_id] = job.get("ats_score", 0)
            continue
        try:
            tailored_text, ats_score = optimize_resume(base_text, job)
            save_tailored_resume(job_id, tailored_text)
            scores[job_id] = ats_score
        except Exception as e:
            logger.error(f"Resume tailoring failed for {job_id}: {e}")
            notify_error(job_id, "resume", str(e))
            send_error_email(job, "resume", e)
            scores[job_id] = 0
    return scores


async def phase_apply(jobs: list[dict], ats_scores: dict[str, int]) -> None:
    logger.info("=== Phase 3: Apply ===")
    batch_counter = [0]
    for job in jobs:
        ats_score = ats_scores.get(job["id"], 0)
        await _apply_async(job, ats_score)
        _maybe_send_report(batch_counter)


def load_queue() -> list[dict]:
    if config.JOBS_QUEUE_FILE.exists():
        try:
            return json.loads(config.JOBS_QUEUE_FILE.read_text())
        except json.JSONDecodeError:
            return []
    return []


# ── Entry point ───────────────────────────────────────────────────────────────

async def main(phase: str | None, dry_run: bool) -> None:
    if not dry_run:
        config.validate()

    if phase in (None, "scrape"):
        jobs = phase_scrape()
    else:
        jobs = load_queue()

    if not jobs:
        logger.warning("No qualified jobs in queue. Exiting.")
        return

    if phase in (None, "resume"):
        ats_scores = phase_resume(jobs)
    else:
        ats_scores = {j["id"]: j.get("ats_score", 0) for j in jobs}

    if dry_run:
        logger.info(f"Dry run: would apply to {len(jobs)} jobs")
        for j in jobs:
            logger.info(f"  {j['title']} @ {j['company']} — score {j.get('compatibility_score')}, ATS {ats_scores.get(j['id'], 0)}")
        return

    if phase in (None, "apply"):
        await phase_apply(jobs, ats_scores)

    # Final report at end of run regardless of count
    try:
        total = count_applied()
        batch_num = max(1, total // config.REPORT_EVERY_N_JOBS + 1)
        html, csv_data = generate_report(batch_num)
        send_report(html, csv_data, batch_num)
    except Exception as e:
        logger.error(f"Final report failed: {e}")

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job application automation pipeline")
    parser.add_argument("--phase", choices=["scrape", "score", "resume", "apply"], default=None)
    parser.add_argument("--dry-run", action="store_true", help="No submissions, no Twilio/email")
    args = parser.parse_args()

    asyncio.run(main(args.phase, args.dry_run))
