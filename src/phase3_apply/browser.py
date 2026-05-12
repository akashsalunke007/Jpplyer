"""Playwright async browser automation — open, fill, upload, submit."""
import asyncio
from pathlib import Path
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PWTimeout
from src import config
from src.phase3_apply.form_detector import detect_fields_from_html, detect_fields_from_screenshot


class HumanCheckRequired(Exception):
    """Raised when a CAPTCHA, login wall, or similar gate is detected."""


class FormFieldNotFound(Exception):
    """Raised when a required field selector cannot be located after retries."""


HUMAN_CHECK_SIGNALS = [
    "captcha", "robot", "verify you are human", "sign in to continue",
    "log in to apply", "please log in", "recaptcha",
]


async def _take_screenshot(page: Page, job_id: str, suffix: str) -> Path:
    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.SCREENSHOTS_DIR / f"{job_id}_{suffix}.png"
    await page.screenshot(path=str(dest), full_page=True)
    return dest


async def _detect_human_check(page: Page) -> bool:
    content = (await page.content()).lower()
    return any(signal in content for signal in HUMAN_CHECK_SIGNALS)


async def _fill_field(page: Page, field: dict, retries: int = 3) -> None:
    selector = field["selector"]
    value = field.get("value", "")
    field_type = field.get("type", "text")

    for attempt in range(1, retries + 1):
        try:
            await page.wait_for_selector(selector, timeout=10000)
            if field_type == "file":
                await page.set_input_files(selector, value)
            elif field_type == "select":
                await page.select_option(selector, label=value)
            elif field_type == "textarea":
                await page.fill(selector, value)
            else:
                # Use type() with delay for SPA compatibility (React onChange)
                await page.fill(selector, "")
                await page.type(selector, value, delay=50)
            return
        except PWTimeout:
            if attempt == retries:
                raise FormFieldNotFound(f"Selector not found after {retries} tries: {selector}")
            await asyncio.sleep(1)


async def apply_to_job(job: dict, resume_path: Path, candidate_data: dict) -> str:
    """
    Open the job URL, detect and fill the application form, upload resume, submit.
    Returns final page URL (for confirmation logging).
    Raises HumanCheckRequired or FormFieldNotFound on hard failures.
    """
    job_id = job["id"]
    url = job["url"]

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=config.HEADLESS)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            logger.info(f"Opening job URL: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)

            if await _detect_human_check(page):
                raise HumanCheckRequired(f"Human check detected on {url}")

            before_shot = await _take_screenshot(page, job_id, "before")

            # Try HTML-based detection first, fall back to screenshot
            html = await page.content()
            fields = detect_fields_from_html(html, candidate_data)
            if not fields:
                logger.info("HTML detection found no fields — trying screenshot")
                fields = detect_fields_from_screenshot(before_shot, candidate_data)

            if not fields:
                raise FormFieldNotFound("No fields detected by either method")

            # Inject resume path for file fields
            for field in fields:
                if field.get("type") == "file":
                    field["value"] = str(resume_path)

            # Fill all non-submit fields
            for field in fields:
                if field.get("type") not in ("submit",):
                    await _fill_field(page, field)

            # Verify required fields before submitting
            await _verify_required_fields(page)

            # Submit
            submit_sel = await _find_submit_button(page)
            await page.click(submit_sel)
            await page.wait_for_load_state("networkidle", timeout=15000)

            final_url = page.url
            await _take_screenshot(page, job_id, "after")
            logger.info(f"Submitted application for job {job_id}, landed on {final_url}")
            return final_url

        finally:
            await browser.close()


async def _verify_required_fields(page: Page) -> None:
    """Check that visible required inputs are not empty before submit."""
    required = await page.query_selector_all("input[required]:not([type='hidden']), textarea[required]")
    for el in required:
        val = await el.input_value()
        if not val.strip():
            label = await el.get_attribute("name") or await el.get_attribute("id") or "unknown"
            logger.warning(f"Required field '{label}' appears empty before submit")


async def _find_submit_button(page: Page) -> str:
    """Return selector for the most likely submit button."""
    candidates = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Submit')",
        "button:has-text('Apply')",
        "button:has-text('Send Application')",
        "[data-testid='submit']",
    ]
    for sel in candidates:
        el = await page.query_selector(sel)
        if el:
            return sel
    raise FormFieldNotFound("Could not find a submit button")
