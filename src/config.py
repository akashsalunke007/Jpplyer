"""Central config loader — all env access goes through here."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_REQUIRED = [
    "APIFY_API_TOKEN",
    "ANTHROPIC_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "ALERT_TO_NUMBER",
    "REPORT_EMAIL_TO",
]

_OPTIONAL_EMAIL = ["SENDGRID_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]


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
    if not _get("SENDGRID_API_KEY") and not (_get("GMAIL_ADDRESS") and _get("GMAIL_APP_PASSWORD")):
        raise EnvironmentError(
            "Missing email config: set either SENDGRID_API_KEY or both GMAIL_ADDRESS + GMAIL_APP_PASSWORD"
        )


# --- Apify ---
APIFY_API_TOKEN: str = _get("APIFY_API_TOKEN", "")

# --- Anthropic ---
ANTHROPIC_API_KEY: str = _get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 1000

# --- Twilio ---
TWILIO_ACCOUNT_SID: str = _get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = _get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER: str = _get("TWILIO_FROM_NUMBER", "")
ALERT_TO_NUMBER: str = _get("ALERT_TO_NUMBER", "")

# --- Email ---
SENDGRID_API_KEY: str = _get("SENDGRID_API_KEY", "")
GMAIL_ADDRESS: str = _get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD: str = _get("GMAIL_APP_PASSWORD", "")
REPORT_EMAIL_TO: str = _get("REPORT_EMAIL_TO", "")

# --- Playwright ---
HEADLESS: bool = _get("HEADLESS", "true").lower() == "true"

# --- Pipeline tuning ---
COMPATIBILITY_THRESHOLD: int = int(_get("COMPATIBILITY_THRESHOLD", "75"))
ATS_TARGET_SCORE: int = int(_get("ATS_TARGET_SCORE", "85"))
REPORT_EVERY_N_JOBS: int = int(_get("REPORT_EVERY_N_JOBS", "10"))
MAX_PAGES_TO_FETCH: int = int(_get("MAX_PAGES_TO_FETCH", "3"))
JOB_LOCATION: str = _get("JOB_LOCATION", "pune")
JOB_COUNTRY: str = _get("JOB_COUNTRY", "india")
JOB_KEYWORD: str = _get("JOB_KEYWORD", "software engineer")

# --- Paths ---
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RESUME_BASE = DATA_DIR / "resume_base.pdf"
TAILORED_DIR = DATA_DIR / "tailored"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
JOBS_QUEUE_FILE = DATA_DIR / "jobs_queue.json"
RESULTS_FILE = DATA_DIR / "results.json"
