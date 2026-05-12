"""Keyword / location / type / salary filtering before Claude scoring."""
import re
from loguru import logger

# Tweak these defaults or pass overrides to filter_jobs()
DEFAULT_CRITERIA = {
    "title_keywords": ["software", "engineer", "developer", "backend", "frontend", "fullstack", "python", "java"],
    "exclude_title_keywords": ["manager", "director", "vp", "intern"],
    "locations": [],          # empty = accept all
    "job_types": ["FULLTIME", "full-time", "full_time", ""],
    "min_salary": None,       # int in USD/INR; None = skip check
    "exclude_companies": [],
}


def _matches_title(title: str, criteria: dict) -> bool:
    low = title.lower()
    include = criteria.get("title_keywords", [])
    exclude = criteria.get("exclude_title_keywords", [])
    if include and not any(kw.lower() in low for kw in include):
        return False
    if any(kw.lower() in low for kw in exclude):
        return False
    return True


def _matches_location(location: str, criteria: dict) -> bool:
    allowed = criteria.get("locations", [])
    if not allowed:
        return True
    low = location.lower()
    return any(loc.lower() in low for loc in allowed)


def _matches_job_type(job_type: str, criteria: dict) -> bool:
    allowed = [t.lower() for t in criteria.get("job_types", [])]
    if not allowed or "" in allowed:
        return True
    return job_type.lower() in allowed


def _extract_salary_number(salary_str: str) -> int | None:
    nums = re.findall(r"[\d,]+", salary_str.replace(",", ""))
    return int(nums[0]) if nums else None


def filter_jobs(jobs: list[dict], criteria: dict | None = None) -> list[dict]:
    """Return jobs that pass all hard criteria. Logs how many were dropped."""
    c = {**DEFAULT_CRITERIA, **(criteria or {})}
    passed, dropped = [], []

    for job in jobs:
        if job.get("company", "").lower() in [x.lower() for x in c.get("exclude_companies", [])]:
            dropped.append(job["id"])
            continue
        if not _matches_title(job.get("title", ""), c):
            dropped.append(job["id"])
            continue
        if not _matches_location(job.get("location", ""), c):
            dropped.append(job["id"])
            continue
        if not _matches_job_type(job.get("job_type", ""), c):
            dropped.append(job["id"])
            continue
        min_sal = c.get("min_salary")
        if min_sal and job.get("salary"):
            sal = _extract_salary_number(job["salary"])
            if sal and sal < min_sal:
                dropped.append(job["id"])
                continue
        passed.append(job)

    logger.info(f"Criteria filter: {len(passed)} passed, {len(dropped)} dropped")
    return passed
