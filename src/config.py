"""Central config loader — all env access goes through here. Zero paid services."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_REQUIRED = [
    "OPENAI_API_KEY",
    "GMAIL_ADDRESS",
    "GMAIL_APP_PASSWORD",
    "REPORT_EMAIL_TO",
]


def _get(key: str, default=None) -> str | None:
    return os.environ.get(key, default)


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val


def validate():
    """Call once at startup. Raises EnvironmentError on first missing required var."""
    for key in _REQUIRED:
        _require(key)


# ── OpenAI (ChatGPT) ─────────────────────────────────────────────────────────
# Get your key at: https://platform.openai.com/api-keys
OPENAI_API_KEY: str = _get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"   # fast, cheap, supports vision — $0.15/1M input tokens
OPENAI_MAX_TOKENS = 1000

# ── Gmail SMTP (free) ────────────────────────────────────────────────────────
# App Password setup: myaccount.google.com → Security → 2-Step → App passwords
GMAIL_ADDRESS: str = _get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD: str = _get("GMAIL_APP_PASSWORD", "")
REPORT_EMAIL_TO: str = _get("REPORT_EMAIL_TO", "")

# ── JobSpy scraper (free, no API key needed) ─────────────────────────────────
JOB_LOCATION: str = _get("JOB_LOCATION", "Pune, India")
JOB_KEYWORD: str = _get("JOB_KEYWORD", "software engineer")
JOB_RESULTS_WANTED: int = int(_get("JOB_RESULTS_WANTED", "50"))
JOB_HOURS_OLD: int = int(_get("JOB_HOURS_OLD", "168"))   # 168h = last 7 days

# ── Playwright ───────────────────────────────────────────────────────────────
HEADLESS: bool = _get("HEADLESS", "true").lower() == "true"

# ── Pipeline tuning ──────────────────────────────────────────────────────────
COMPATIBILITY_THRESHOLD: int = int(_get("COMPATIBILITY_THRESHOLD", "75"))
MAX_JOBS_TO_SCORE: int = int(_get("MAX_JOBS_TO_SCORE", "20"))   # cap per run to save API quota
ATS_TARGET_SCORE: int = int(_get("ATS_TARGET_SCORE", "85"))
REPORT_EVERY_N_JOBS: int = int(_get("REPORT_EVERY_N_JOBS", "10"))

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RESUME_BASE = DATA_DIR / "resume_base.pdf"
TAILORED_DIR = DATA_DIR / "tailored"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
JOBS_QUEUE_FILE = DATA_DIR / "jobs_queue.json"
RESULTS_FILE = DATA_DIR / "results.json"
