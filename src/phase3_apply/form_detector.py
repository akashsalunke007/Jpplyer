"""AI-assisted form field detection and mapping."""
import json
import base64
from pathlib import Path
import anthropic
from loguru import logger
from src import config

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

FORM_DETECTOR_SYSTEM = """
You are a browser automation assistant. Analyze the provided page screenshot or HTML.
Output ONLY a JSON array of field mappings:
[{"field_label": "...", "selector": "...", "value": "...", "type": "text|select|file|textarea"}]
No preamble. No markdown.
"""

FORM_DETECTOR_USER_HTML = """
PAGE HTML (truncated to form sections):
{html}

CANDIDATE DATA:
{candidate_data}

Map all visible form fields to candidate data. Use CSS selectors.
"""

FORM_DETECTOR_USER_SCREENSHOT = """
CANDIDATE DATA:
{candidate_data}

Identify all form fields in this screenshot and map them to candidate data values.
Use best-guess CSS selectors based on visible labels.
"""


def detect_fields_from_html(html: str, candidate_data: dict) -> list[dict]:
    """Use Claude to map form fields from page HTML."""
    # Truncate HTML to keep prompt manageable
    truncated = html[:6000] if len(html) > 6000 else html
    prompt = FORM_DETECTOR_USER_HTML.format(
        html=truncated,
        candidate_data=json.dumps(candidate_data, indent=2),
    )
    return _call_claude_text(prompt)


def detect_fields_from_screenshot(screenshot_path: Path, candidate_data: dict) -> list[dict]:
    """Use Claude Vision to map form fields from a page screenshot."""
    image_data = base64.b64encode(screenshot_path.read_bytes()).decode("utf-8")
    response = _client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        system=FORM_DETECTOR_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": FORM_DETECTOR_USER_SCREENSHOT.format(
                            candidate_data=json.dumps(candidate_data, indent=2)
                        ),
                    },
                ],
            }
        ],
    )
    return _parse_response(response.content[0].text)


def _call_claude_text(prompt: str) -> list[dict]:
    response = _client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        system=FORM_DETECTOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_response(response.content[0].text)


def _parse_response(text: str) -> list[dict]:
    text = text.strip().strip("```json").strip("```").strip()
    try:
        fields = json.loads(text)
        return fields if isinstance(fields, list) else []
    except json.JSONDecodeError as e:
        logger.error(f"Form detector JSON parse error: {e} — raw: {text[:200]}")
        return []
