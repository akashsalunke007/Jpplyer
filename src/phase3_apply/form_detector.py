"""OpenAI-powered form field detection and mapping."""
import json
import re
import base64
from pathlib import Path
from openai import OpenAI
from loguru import logger
from src import config

_client = OpenAI(api_key=config.OPENAI_API_KEY)

_SYSTEM = (
    "You are a browser automation assistant. "
    "Output ONLY a valid JSON array of field mappings — no preamble, no markdown fences:\n"
    '[{"field_label":"...","selector":"...","value":"...","type":"text|select|file|textarea"}]'
)

_HTML_PROMPT = """
PAGE HTML (form sections only):
{html}

CANDIDATE DATA:
{candidate_data}

Map every visible form field to the candidate data. Use CSS selectors.
Output only the JSON array.
"""

_SCREENSHOT_PROMPT = """
CANDIDATE DATA:
{candidate_data}

Identify all form fields visible in this screenshot and map them to the candidate data.
Guess CSS selectors from the visible labels (e.g. input[name='email'], #first_name).
Output only the JSON array.
"""


def _parse(text: str) -> list[dict]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError as e:
        logger.error(f"Form detector JSON parse error: {e} — raw: {text[:200]}")
        return []


def detect_fields_from_html(html: str, candidate_data: dict) -> list[dict]:
    """Send page HTML to OpenAI and return mapped form fields."""
    try:
        response = _client.chat.completions.create(
            model=config.OPENAI_MODEL,
            max_tokens=config.OPENAI_MAX_TOKENS,
            temperature=0.0,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _HTML_PROMPT.format(
                    html=html[:6000],
                    candidate_data=json.dumps(candidate_data, indent=2),
                )},
            ],
        )
        return _parse(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"HTML form detection failed: {e}")
        return []


def detect_fields_from_screenshot(screenshot_path: Path, candidate_data: dict) -> list[dict]:
    """Send a page screenshot to OpenAI Vision and return mapped form fields."""
    image_b64 = base64.b64encode(screenshot_path.read_bytes()).decode("utf-8")
    try:
        response = _client.chat.completions.create(
            model=config.OPENAI_MODEL,
            max_tokens=config.OPENAI_MAX_TOKENS,
            temperature=0.0,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": _SCREENSHOT_PROMPT.format(
                        candidate_data=json.dumps(candidate_data, indent=2),
                    )},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                        "detail": "low",
                    }},
                ]},
            ],
        )
        return _parse(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Screenshot form detection failed: {e}")
        return []
