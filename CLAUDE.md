# Job Application Automation — CLAUDE.md

> Project context, architecture, conventions, and agentic workflow for Claude Code.
> Keep this file under 200 lines. Document what Claude gets wrong, not obvious things.

---

## Project overview

An end-to-end automated job application pipeline:

1. **Scrape** relevant job listings from LinkedIn / Indeed via Apify actors
2. **Score** each job for compatibility against the user's profile (≥ 75% threshold)
3. **Tailor** the resume per job using ATS keyword optimization (target ≥ 85% ATS score)
4. **Apply** by automating browser form-filling and resume upload via Playwright
5. **Notify** via SMS (Twilio) and email (Gmail/SendGrid) on errors or human-check gates
6. **Report** a batch summary every 10 jobs applied

---

## Repository structure

```
job-auto-apply/
├── CLAUDE.md                  ← this file (always read first)
├── .env.example               ← required env vars (never commit .env)
├── tasks/
│   ├── todo.md                ← current task queue
│   └── lessons.md             ← mistakes + rules learned (update after every correction)
├── src/
│   ├── phase1_scrape/
│   │   ├── apify_client.py    ← Apify API wrapper
│   │   ├── criteria_filter.py ← keyword/location/type filtering
│   │   └── compatibility.py   ← Claude API scoring logic
│   ├── phase2_resume/
│   │   ├── ats_optimizer.py   ← Claude API ATS rewriter (up to 3 passes)
│   │   ├── scorer.py          ← ATS simulation scorer
│   │   └── storage.py         ← save/load base + tailored resumes
│   ├── phase3_apply/
│   │   ├── browser.py         ← Playwright automation (open, fill, upload, submit)
│   │   ├── form_detector.py   ← AI field detection + mapping
│   │   └── result_logger.py   ← log applied/failed/skipped with timestamps
│   ├── phase4_report/
│   │   ├── report_generator.py ← HTML + CSV batch report (every 10 jobs)
│   │   └── email_sender.py    ← Gmail/SendGrid dispatch
│   ├── notifications/
│   │   ├── sms.py             ← Twilio SMS alert
│   │   └── email_alert.py     ← error email with stack trace
│   ├── orchestrator.py        ← main pipeline loop (entry point)
│   └── config.py              ← loads .env, validates required vars
├── data/
│   ├── resume_base.pdf        ← master resume (never modified in place)
│   ├── tailored/              ← job-specific resumes (job_id.pdf)
│   ├── jobs_queue.json        ← qualified jobs awaiting processing
│   └── results.json           ← running log of all outcomes
├── tests/
│   ├── test_compatibility.py
│   ├── test_ats_optimizer.py
│   └── test_browser.py
└── requirements.txt
```

---

## Required environment variables

```bash
# Apify
APIFY_API_TOKEN=

# Anthropic (Claude API)
ANTHROPIC_API_KEY=

# Twilio (SMS alerts)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
ALERT_TO_NUMBER=          # your phone number with country code

# Email (choose one)
SENDGRID_API_KEY=
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=       # use App Password, not account password
REPORT_EMAIL_TO=          # where batch reports are sent

# Playwright
HEADLESS=true             # set false for local debugging
```

**Rule:** Never read `.env` directly. Always use `src/config.py` which validates all vars at startup and raises `EnvironmentError` with the missing key name.

---

## Common commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run full pipeline
python src/orchestrator.py

# Run a single phase (for testing)
python src/orchestrator.py --phase scrape
python src/orchestrator.py --phase score
python src/orchestrator.py --phase resume
python src/orchestrator.py --phase apply

# Run tests
pytest tests/ -v

# Dry run (no submissions, no Twilio/email)
python src/orchestrator.py --dry-run
```

---

## Architecture and data flow

```
orchestrator.py
│
├─ Phase 1: Scrape & filter
│   ├─ apify_client.py        → runs actor, returns raw job list
│   ├─ criteria_filter.py     → applies title/location/type/salary filters
│   └─ compatibility.py       → Claude API scores each JD vs profile (0-100)
│                               → writes qualified jobs (≥75) to jobs_queue.json
│
├─ Phase 2: Resume tailoring (loop over queue)
│   ├─ storage.py             → loads resume_base.pdf for each job
│   ├─ ats_optimizer.py       → Claude API rewrites bullets/skills (up to 3 passes)
│   ├─ scorer.py              → simulates ATS score after each pass
│   └─ storage.py             → saves tailored PDF as data/tailored/{job_id}.pdf
│
├─ Phase 3: Apply (loop continues)
│   ├─ browser.py             → opens job URL with Playwright
│   ├─ form_detector.py       → Claude Vision identifies and maps fields
│   ├─ browser.py             → fills fields, uploads tailored PDF, submits
│   └─ result_logger.py       → appends {job_id, status, timestamp} to results.json
│
├─ Phase 4: Report (every 10 jobs)
│   ├─ report_generator.py    → builds HTML summary + CSV from results.json
│   └─ email_sender.py        → sends report to REPORT_EMAIL_TO
│
└─ Error handler (any phase)
    ├─ result_logger.py       → logs error with job_id + traceback
    ├─ sms.py                 → Twilio SMS to ALERT_TO_NUMBER
    ├─ email_alert.py         → detailed error email
    └─ orchestrator.py        → retries up to 2x, then marks failed + continues
```

---

## Claude API prompts reference

### Compatibility scoring (`compatibility.py`)

```python
COMPATIBILITY_SYSTEM = """
You are a professional career advisor. Given a job description and a candidate profile,
output ONLY a JSON object: {"score": <int 0-100>, "reasons": ["...", "..."], "gaps": ["..."]}
No preamble. No markdown fences.
"""

COMPATIBILITY_USER = """
JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
{candidate_profile}

Score the compatibility. Be strict: 75+ means genuinely strong match.
"""
```

### ATS optimizer (`ats_optimizer.py`)

```python
ATS_OPTIMIZER_SYSTEM = """
You are an expert ATS resume optimizer. Rewrite the provided resume section to:
1. Mirror exact keywords from the job description (verbatim where natural)
2. Quantify achievements wherever possible
3. Use action verbs that match the JD's language
4. Keep all facts true — never invent experience

Output ONLY the rewritten resume text. No commentary.
"""

ATS_OPTIMIZER_USER = """
JOB DESCRIPTION:
{job_description}

CURRENT RESUME SECTION:
{resume_section}

TARGET ATS SCORE: 85+
Current ATS score: {current_score}
Gaps: {gaps}

Rewrite to close the gaps.
"""
```

### Form field detection (`form_detector.py`)

```python
FORM_DETECTOR_SYSTEM = """
You are a browser automation assistant. Analyze the provided page screenshot or HTML.
Output ONLY a JSON array of field mappings:
[{"field_label": "...", "selector": "...", "value": "...", "type": "text|select|file|textarea"}]
No preamble. No markdown.
"""
```

---

## Error handling rules

- **Every phase** must be wrapped in `try/except`. Never let an exception bubble up to terminate the whole pipeline.
- On error: log → SMS → email → retry (max 2) → mark failed → continue to next job.
- The pipeline must complete all jobs even if some fail.
- **Human-check gate** (captcha, login wall): pause job, log as `status: needs_human`, send SMS immediately, skip to next job. Do not retry automatically.
- Never expose `.env` values in error messages or logs.

```python
# Correct error handling pattern
def run_phase(job, phase_fn):
    for attempt in range(1, 3):
        try:
            return phase_fn(job)
        except HumanCheckRequired:
            notify_human_check(job)
            return {"status": "needs_human"}
        except Exception as e:
            log_error(job["id"], e, attempt)
            if attempt == 2:
                notify_error(job, e)
                return {"status": "failed", "error": str(e)}
```

---

## Resume storage rules

- `data/resume_base.pdf` is **read-only**. Never modify or overwrite it.
- Each tailored resume is saved as `data/tailored/{job_id}.pdf` before applying.
- If a tailored resume for a job_id already exists, skip re-generation (idempotent).
- The ATS optimizer works on extracted text sections, not the PDF directly. Use `pdfplumber` to extract, modify text, then `reportlab` or `fpdf2` to regenerate PDF.

---

## Browser automation rules

- Always wait for `networkidle` before interacting with a page.
- Use `page.wait_for_selector(selector, timeout=10000)` — never `time.sleep()`.
- Screenshot every page state before and after submission: save to `data/screenshots/{job_id}_before.png` and `{job_id}_after.png`.
- If a field selector is not found after 3 retries, raise `FormFieldNotFound` (triggers error handler).
- Never click "Submit" without first verifying all required fields are filled.

---

## Apify actors to use

| Platform  | Actor ID                                      | Notes                        |
|-----------|-----------------------------------------------|------------------------------|
| LinkedIn  | `curious_coder/linkedin-jobs-scraper`         | Free, no login, public jobs  |
| LinkedIn  | `fetchclub/linkedin-jobs-scraper`             | $19.99/mo, better results    |
| Indeed    | `orgupdate/indeed-jobs-scraper`               | Pay-per-result               |
| Indeed    | `curious_coder/indeed-scraper`                | Fixed monthly cost           |

Default input shape for LinkedIn actor:
```json
{
  "countryName": "india",
  "locationName": "pune",
  "includeKeyword": "software engineer",
  "jobType": "FULLTIME",
  "datePosted": "week",
  "pagesToFetch": 3
}
```

---

## Reporting spec

Every 10 jobs applied (success or failure), `report_generator.py` produces:

```
Subject: Job Application Report — Batch {N} ({date})

Summary:
  Applied:      X
  Failed:       Y
  Needs human:  Z
  Avg ATS score: N%

Details table:
  Job title | Company | Score | ATS% | Status | URL | Timestamp
```

Attach CSV with the same data. Send via `email_sender.py` to `REPORT_EMAIL_TO`.

---

## Coding conventions

- Python 3.11+. Use `async/await` with `asyncio` for Playwright calls.
- All Claude API calls use model `claude-sonnet-4-20250514`, `max_tokens=1000`.
- JSON responses from Claude: strip markdown fences before `json.loads()`.
- Use `loguru` for all logging (not `print`). Log level `INFO` for normal flow, `ERROR` for caught exceptions.
- One function = one responsibility. Functions over 40 lines should be split.
- After **any** correction or bug fix, update `tasks/lessons.md` with a rule that prevents recurrence.

---

## tasks/lessons.md format

```markdown
## Lesson {date}: {short title}
**What went wrong:** ...
**Root cause:** ...
**Rule added:** Never do X; always do Y instead.
```

---

## Known gotchas

- LinkedIn may block requests intermittently — use `datacenter` proxies in Apify, not residential (cheaper and usually sufficient).
- `pdfplumber` sometimes misreads bullet characters — normalize to `•` before ATS processing.
- Playwright's `fill()` does not trigger React `onChange` on some SPAs — use `type()` with `delay=50` instead.
- Gmail App Passwords require 2FA to be enabled on the account first.
- Twilio free trial only sends to verified numbers — upgrade to a paid account for production.
- Some job sites detect headless Chrome — set `HEADLESS=false` for those, or use `stealth` plugin.

---

## Plan mode rule

For any task involving ≥ 3 files or a new phase, enter plan mode first:
1. Read all relevant files.
2. Write a step-by-step implementation plan.
3. Get confirmation before writing any code.
4. After implementation, run `pytest tests/` and fix all failures before marking done.
