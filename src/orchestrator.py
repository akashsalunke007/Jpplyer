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

CANDIDATE_PROFILE = """
Name: Soni Kori
Current role: System Engineer at Infosys (Sep 2025 – Apr 2026)
Total experience: ~1 year (6+ months professional + 5 months internship at CDAC)

Education:
  - Master of Computer Applications (MCA), Banasthali Vidyapeeth, CGPA 7.1, Graduated 2025
  - Bachelor of Science, Banasthali Vidyapeeth, CGPA 8.4

Technical Skills:
  Languages:          Java, Python, JavaScript
  Backend Frameworks: Spring Boot, Flask (REST API development)
  Frontend:           HTML5, CSS3, JavaScript (ES6+), Dynamic Content Rendering
  Databases:          MySQL, PostgreSQL (Joins, Indexing, Query Optimization, Schema Design)
  Tools & Platforms:  Git, GitHub, Postman, Unix/Linux, VS Code
  Concepts:           Data Structures & Algorithms, OOP, MVC Architecture, SDLC, Agile/Scrum
  Data / ML:          Python ML libraries, Scikit-learn, Pandas, Content-Based Filtering

Professional Experience:
  - System Engineer, Infosys, Bangalore (Sep 2025 – Apr 2026)
    * Developed scalable web application features using Python and full-stack practices
    * Implemented RESTful APIs and integrated with frontend components
    * Participated in Agile/Scrum sprints — planning, standups, requirement analysis
    * Wrote clean MVC-pattern code improving team velocity during code reviews
  - Full Stack Developer Intern, CDAC, New Delhi (Jan 2025 – May 2025)
    * Built full-stack apps with Spring Boot backend and HTML/CSS/JS frontend
    * Designed RESTful APIs for CRUD operations with JSON data exchange
    * Engineered PostgreSQL schemas and optimized SQL queries
    * Maintained Git/GitHub version control with structured branching

Key Projects:
  - Infymart: Full-stack e-commerce app (Flask, MySQL, HTML5, CSS3, JavaScript)
    * Product catalog, user auth, shopping cart, order management
    * RESTful Flask APIs with MVC pattern, normalized MySQL schema
  - Movie Recommender System (Python, Scikit-learn, Pandas)
    * Content-based filtering engine with cosine similarity scoring
    * Feature engineering and data preprocessing pipeline

Certifications:
  - Data Structures and Algorithms using Java
  - Advanced Unix
  - Advanced Python Concepts
  - Web Application Development using Flask

Location: India (open to Bangalore, Pune, Delhi, Remote)
Preferred: Full-time, Software Engineer / Full Stack Developer / Backend Developer roles
"""

CANDIDATE_DATA = {
    "full_name": "Soni Kori",
    "first_name": "Soni",
    "last_name": "Kori",
    "email": "sonikori9999@gmail.com",
    "phone": "+919634961848",
    "linkedin": "https://linkedin.com/in/soni-kori-8b074a22a",
    "github": "",
    "location": "India",
    "city": "Bangalore",
    "state": "Karnataka",
    "country": "India",
    "years_experience": "1",
    "current_title": "System Engineer",
    "current_company": "Infosys",
    "education": "Master of Computer Applications (MCA), Banasthali Vidyapeeth, 2025",
    "degree": "MCA",
    "university": "Banasthali Vidyapeeth",
    "graduation_year": "2025",
    "notice_period": "Immediately available",
    "expected_salary": "5 LPA",
    "skills": "Java, Python, JavaScript, Spring Boot, Flask, HTML5, CSS3, MySQL, PostgreSQL, Git, Agile",
    "cover_letter": (
        "I am excited to apply for this position. I am a Full Stack Developer with an MCA degree "
        "and professional experience at Infosys building scalable web applications using Python, "
        "Java, Spring Boot, and Flask. I have hands-on expertise in RESTful API development, "
        "PostgreSQL/MySQL database design, and Agile development practices. I have delivered "
        "full-stack projects end-to-end, including an e-commerce platform and a machine learning "
        "recommendation system. I am eager to contribute my backend and full-stack capabilities "
        "to a product-driven team and grow as a software engineer."
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
    raw_jobs = scrape_jobs(platforms=["linkedin", "indeed"])
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
    parser.add_argument("--dry-run", action="store_true", help="No submissions, no Telegram/email")
    args = parser.parse_args()

    asyncio.run(main(args.phase, args.dry_run))
