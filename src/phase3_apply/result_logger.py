"""Append-only JSON log of all job outcomes."""
import json
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger
from src import config


def _load() -> list[dict]:
    if config.RESULTS_FILE.exists():
        try:
            return json.loads(config.RESULTS_FILE.read_text())
        except json.JSONDecodeError:
            return []
    return []


def _save(records: list[dict]) -> None:
    config.RESULTS_FILE.write_text(json.dumps(records, indent=2, default=str))


def log_result(job: dict, status: str, ats_score: int = 0, error: str = "") -> None:
    """Append an outcome record to results.json."""
    records = _load()
    record = {
        "job_id": job.get("id"),
        "title": job.get("title"),
        "company": job.get("company"),
        "url": job.get("url"),
        "compatibility_score": job.get("compatibility_score", 0),
        "ats_score": ats_score,
        "status": status,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    records.append(record)
    _save(records)
    logger.info(f"Logged result: {record['job_id']} → {status}")


def get_results() -> list[dict]:
    return _load()


def count_applied() -> int:
    return sum(1 for r in _load() if r["status"] in ("applied", "failed", "needs_human"))
