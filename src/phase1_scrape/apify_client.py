"""
Job scraper using JobSpy — completely free, no API key required.
Scrapes LinkedIn, Indeed, and Glassdoor directly.

JobSpy docs: https://github.com/Bunsly/JobSpy
"""
from loguru import logger
from src import config


def _normalise(row: dict) -> dict:
    """Convert a JobSpy result row into the pipeline's standard job schema."""
    job_id = str(row.get("id") or row.get("job_url_direct") or hash(row.get("job_url", "")))
    return {
        "id": job_id,
        "title": str(row.get("title", "")),
        "company": str(row.get("company", "")),
        "location": str(row.get("location", "")),
        "description": str(row.get("description") or ""),
        "url": str(row.get("job_url") or row.get("job_url_direct") or ""),
        "salary": _format_salary(row),
        "job_type": str(row.get("job_type") or ""),
        "source": str(row.get("site") or "unknown"),
        "date_posted": str(row.get("date_posted") or ""),
    }


def _format_salary(row: dict) -> str:
    lo = row.get("min_amount")
    hi = row.get("max_amount")
    currency = row.get("currency", "")
    interval = row.get("interval", "")
    if lo and hi:
        return f"{currency}{lo}–{hi} {interval}".strip()
    if lo:
        return f"{currency}{lo}+ {interval}".strip()
    return ""


def scrape_jobs(
    platforms: list[str] | None = None,
    keyword: str | None = None,
    location: str | None = None,
    results_wanted: int | None = None,
    hours_old: int | None = None,
) -> list[dict]:
    """
    Scrape jobs from LinkedIn, Indeed, and/or Glassdoor — no API key needed.

    Args:
        platforms:      list of sites to scrape, e.g. ["linkedin", "indeed"]
                        defaults to ["linkedin", "indeed"]
        keyword:        search term (default from config)
        location:       location string (default from config)
        results_wanted: max results per site (default from config)
        hours_old:      only jobs posted within this many hours (default 168 = 7 days)
    """
    from jobspy import scrape_jobs as _jobspy_scrape   # lazy import — not needed for tests

    sites = platforms or ["linkedin", "indeed"]
    kw = keyword or config.JOB_KEYWORD
    loc = location or config.JOB_LOCATION
    n = results_wanted or config.JOB_RESULTS_WANTED
    h = hours_old or config.JOB_HOURS_OLD

    logger.info(f"Scraping jobs: sites={sites}, keyword='{kw}', location='{loc}', max={n}")

    try:
        df = _jobspy_scrape(
            site_name=sites,
            search_term=kw,
            location=loc,
            results_wanted=n,
            hours_old=h,
            country_indeed="India",   # for Indeed localisation
            linkedin_fetch_description=True,  # fetch full JD (slower but needed for ATS)
        )
    except Exception as e:
        logger.error(f"JobSpy scrape failed: {e}")
        return []

    if df is None or df.empty:
        logger.warning("JobSpy returned no results")
        return []

    jobs = [_normalise(row) for row in df.to_dict("records") if row.get("title")]
    # Drop duplicates by URL
    seen, unique = set(), []
    for j in jobs:
        key = j["url"] or j["id"]
        if key not in seen:
            seen.add(key)
            unique.append(j)

    logger.info(f"Scraped {len(unique)} unique jobs from {sites}")
    return unique
