"""Apify API wrapper — runs job scraper actors and returns raw job list."""
import json
from typing import Any
from apify_client import ApifyClient
from loguru import logger
from src import config

_ACTORS = {
    "linkedin": "curious_coder/linkedin-jobs-scraper",
    "indeed": "curious_coder/indeed-scraper",
}

_DEFAULT_LINKEDIN_INPUT = {
    "countryName": config.JOB_COUNTRY,
    "locationName": config.JOB_LOCATION,
    "includeKeyword": config.JOB_KEYWORD,
    "jobType": "FULLTIME",
    "datePosted": "week",
    "pagesToFetch": config.MAX_PAGES_TO_FETCH,
}


def _normalise_linkedin(item: dict) -> dict:
    return {
        "id": item.get("id") or item.get("jobId") or str(hash(item.get("url", ""))),
        "title": item.get("title", ""),
        "company": item.get("companyName", ""),
        "location": item.get("location", ""),
        "description": item.get("descriptionText") or item.get("description", ""),
        "url": item.get("applyUrl") or item.get("url", ""),
        "salary": item.get("salary", ""),
        "job_type": item.get("jobType", ""),
        "source": "linkedin",
    }


def _normalise_indeed(item: dict) -> dict:
    return {
        "id": item.get("id") or str(hash(item.get("url", ""))),
        "title": item.get("positionName", ""),
        "company": item.get("company", ""),
        "location": item.get("location", ""),
        "description": item.get("description", ""),
        "url": item.get("url", ""),
        "salary": item.get("salary", ""),
        "job_type": item.get("jobType", ""),
        "source": "indeed",
    }


def scrape_jobs(
    platform: str = "linkedin",
    actor_input: dict[str, Any] | None = None,
    proxy_config: dict | None = None,
) -> list[dict]:
    """Run the Apify actor and return a normalised list of job dicts."""
    client = ApifyClient(config.APIFY_API_TOKEN)
    actor_id = _ACTORS.get(platform, _ACTORS["linkedin"])
    run_input = actor_input or _DEFAULT_LINKEDIN_INPUT.copy()

    if proxy_config:
        run_input["proxyConfig"] = proxy_config
    else:
        run_input["proxyConfig"] = {"useApifyProxy": True, "apifyProxyGroups": ["DATACENTER"]}

    logger.info(f"Starting Apify actor '{actor_id}' for platform={platform}")
    run = client.actor(actor_id).call(run_input=run_input)
    logger.info(f"Actor run finished: {run['status']} — dataset {run['defaultDatasetId']}")

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    logger.info(f"Fetched {len(items)} raw jobs from {platform}")

    normaliser = _normalise_linkedin if platform == "linkedin" else _normalise_indeed
    jobs = [normaliser(item) for item in items if item.get("title")]
    return jobs
