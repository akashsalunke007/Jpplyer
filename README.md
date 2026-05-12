# Jpplyer — Automated Job Application Pipeline

An end-to-end Python pipeline that scrapes job listings, scores them for compatibility, tailors your resume per job using ATS optimization, applies automatically via Playwright browser automation, and notifies you by SMS and email throughout.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [How Each Phase Works](#how-each-phase-works)
  - [Phase 1 — Scrape & Filter](#phase-1--scrape--filter)
  - [Phase 2 — Resume Tailoring](#phase-2--resume-tailoring)
  - [Phase 3 — Apply](#phase-3--apply)
  - [Phase 4 — Reporting](#phase-4--reporting)
  - [Error Notifications](#error-notifications)
- [Running Tests](#running-tests)
- [Customising Criteria](#customising-criteria)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)

---

## Overview

```
Apify scraper → criteria filter → Claude compatibility score (≥ 75%)
    → Claude ATS resume rewrite (target ≥ 85%)
        → Playwright form-fill & submit
            → SMS + email on any error
                → HTML/CSV batch report every 10 jobs
```

---

## Architecture

```
orchestrator.py
│
├─ Phase 1: Scrape & filter
│   ├─ apify_client.py        runs LinkedIn/Indeed actor, returns raw job list
│   ├─ criteria_filter.py     keyword / location / type / salary hard filters
│   └─ compatibility.py       Claude API scores each JD vs your profile (0–100)
│                              writes qualified jobs (≥ 75) to data/jobs_queue.json
│
├─ Phase 2: Resume tailoring  (per job)
│   ├─ storage.py             reads data/resume_base.pdf (read-only)
│   ├─ ats_optimizer.py       Claude API rewrites resume (up to 3 passes)
│   ├─ scorer.py              simulates ATS score after each pass
│   └─ storage.py             saves tailored PDF to data/tailored/{job_id}.pdf
│
├─ Phase 3: Apply             (per job)
│   ├─ browser.py             opens job URL with Playwright
│   ├─ form_detector.py       Claude detects & maps form fields (HTML or screenshot)
│   ├─ browser.py             fills fields, uploads PDF, submits
│   └─ result_logger.py       appends {job_id, status, timestamp} to results.json
│
├─ Phase 4: Report            (every 10 jobs)
│   ├─ report_generator.py    builds HTML summary + CSV from results.json
│   └─ email_sender.py        sends report to REPORT_EMAIL_TO
│
└─ Error handler              (any phase)
    ├─ result_logger.py       logs error with job_id + traceback
    ├─ sms.py                 Twilio SMS to ALERT_TO_NUMBER
    ├─ email_alert.py         detailed error email with stack trace
    └─ orchestrator.py        retries up to 2×, then marks failed + continues
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| pip | latest |
| Chromium (via Playwright) | installed separately — see below |

**External service accounts required:**

| Service | Used for | Free tier? |
|---|---|---|
| [Apify](https://apify.com) | Job scraping actors | Yes (limited runs) |
| [Anthropic](https://console.anthropic.com) | Claude API (scoring + ATS) | Pay-per-token |
| [Twilio](https://twilio.com) | SMS error alerts | Free trial (verified numbers only) |
| SendGrid **or** Gmail | Email reports + error alerts | Free (SendGrid 100/day; Gmail with App Password) |

---

## Installation

```bash
# 1. Clone / download the project
cd Jpplyer

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright's Chromium browser
playwright install chromium
```

---

## Configuration

### Step 1 — Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in every value:

```bash
# ── Apify ───────────────────────────────────────────────
APIFY_API_TOKEN=your_apify_token_here

# ── Anthropic (Claude API) ──────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...

# ── Twilio (SMS alerts) ─────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1415XXXXXXX          # your Twilio number
ALERT_TO_NUMBER=+919876543210            # YOUR phone (with country code)

# ── Email — choose ONE of the two options below ─────────

# Option A: SendGrid (recommended)
SENDGRID_API_KEY=SG.xxxxxxxxxxxx
GMAIL_ADDRESS=you@gmail.com             # used as the From address

# Option B: Gmail SMTP
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-char App Password (NOT account password)

# Both options need this:
REPORT_EMAIL_TO=you@gmail.com           # where batch reports are sent

# ── Playwright ──────────────────────────────────────────
HEADLESS=true                           # set false for visual debugging

# ── Pipeline tuning (optional) ──────────────────────────
COMPATIBILITY_THRESHOLD=75
ATS_TARGET_SCORE=85
REPORT_EVERY_N_JOBS=10
MAX_PAGES_TO_FETCH=3
JOB_LOCATION=pune
JOB_COUNTRY=india
JOB_KEYWORD=software engineer
```

> **Gmail App Password** — requires 2FA enabled on your Google account.  
> Go to: Google Account → Security → 2-Step Verification → App passwords.

> **Twilio free trial** — can only send SMS to verified numbers. Upgrade to a paid account for production use.

### Step 2 — Add your base resume

Place your resume as:
```
data/resume_base.pdf
```

This file is **never modified**. All tailored versions are written to `data/tailored/{job_id}.pdf`.

### Step 3 — Edit your candidate profile

Open [`src/orchestrator.py`](src/orchestrator.py) and fill in your details in the two blocks near the top:

```python
CANDIDATE_PROFILE = """
Name: Your Name
Current role: Software Engineer, 4 years experience
Skills: Python, FastAPI, Django, PostgreSQL, Redis, AWS, Docker, Kubernetes
Education: B.E. Computer Engineering
Location: Pune, India
Preferred: Full-time, backend/fullstack roles, 12–20 LPA
"""

CANDIDATE_DATA = {
    "full_name": "Your Name",
    "email": "you@email.com",
    "phone": "+91XXXXXXXXXX",
    "linkedin": "https://linkedin.com/in/yourprofile",
    "github": "https://github.com/yourusername",
    "location": "Pune, India",
    "years_experience": "4",
    "current_title": "Software Engineer",
    "notice_period": "30 days",
    "expected_salary": "15 LPA",
    "cover_letter": "...",
}
```

---

## Project Structure

```
Jpplyer/
├── .env.example                    environment variable template
├── .env                            your secrets (never commit this)
├── requirements.txt                Python dependencies
├── README.md
├── CLAUDE.md                       project spec for Claude Code
│
├── src/
│   ├── config.py                   central env loader — all config access goes here
│   ├── orchestrator.py             main pipeline entry point
│   │
│   ├── phase1_scrape/
│   │   ├── apify_client.py         Apify actor runner + response normaliser
│   │   ├── criteria_filter.py      hard keyword/location/type/salary filters
│   │   └── compatibility.py        Claude API job–profile compatibility scorer
│   │
│   ├── phase2_resume/
│   │   ├── storage.py              read base PDF (pdfplumber), write tailored PDF (reportlab)
│   │   ├── ats_optimizer.py        Claude API ATS rewriter — up to 3 passes
│   │   └── scorer.py               keyword-overlap ATS simulation scorer
│   │
│   ├── phase3_apply/
│   │   ├── browser.py              async Playwright automation (fill, upload, submit)
│   │   ├── form_detector.py        Claude Vision / HTML form field mapper
│   │   └── result_logger.py        append-only JSON outcome logger
│   │
│   ├── phase4_report/
│   │   ├── report_generator.py     HTML + CSV batch report builder
│   │   └── email_sender.py         SendGrid / Gmail report dispatcher
│   │
│   └── notifications/
│       ├── sms.py                  Twilio SMS error alerts
│       └── email_alert.py          error + human-check emails with stack trace
│
├── data/
│   ├── resume_base.pdf             YOUR base resume (add this manually — read-only)
│   ├── tailored/                   auto-generated per-job PDFs
│   ├── screenshots/                before/after screenshots per application
│   ├── jobs_queue.json             qualified jobs written after Phase 1
│   └── results.json                running log of all outcomes
│
├── tests/
│   ├── test_compatibility.py       criteria filter + Claude scoring tests
│   ├── test_ats_optimizer.py       ATS scorer + optimizer tests
│   └── test_browser.py            result logger + form detector parse tests
│
└── tasks/
    ├── todo.md                     setup checklist + future enhancements
    └── lessons.md                  bugs fixed + rules learned
```

---

## Usage

### Full pipeline run
```bash
python src/orchestrator.py
```
Runs all 4 phases in sequence: scrape → resume → apply → final report.

### Dry run (no submissions, no Twilio/email)
```bash
python src/orchestrator.py --dry-run
```
Runs Phases 1 and 2, then prints what would be applied without submitting anything.

### Run a single phase
```bash
python src/orchestrator.py --phase scrape    # scrape + filter + score → writes jobs_queue.json
python src/orchestrator.py --phase resume    # tailor resumes for jobs already in queue
python src/orchestrator.py --phase apply     # apply to jobs in queue (resumes must exist)
```

### Run tests
```bash
pytest tests/ -v
```

---

## How Each Phase Works

### Phase 1 — Scrape & Filter

**`apify_client.py`** calls the Apify actor (default: `curious_coder/linkedin-jobs-scraper`) with your location, keyword, and job type. Results are normalised into a consistent schema.

**`criteria_filter.py`** drops jobs that don't match hard rules (title keywords, excluded words like "manager"/"intern", location, job type). Configure `DEFAULT_CRITERIA` or pass overrides.

**`compatibility.py`** sends each remaining job description + your `CANDIDATE_PROFILE` to Claude API. Claude returns a 0–100 compatibility score. Only jobs scoring **≥ 75** (configurable via `COMPATIBILITY_THRESHOLD`) advance to the queue.

Qualified jobs are written to `data/jobs_queue.json`.

---

### Phase 2 — Resume Tailoring

For each job in the queue:

1. **`storage.py`** extracts text from `data/resume_base.pdf` using `pdfplumber`.
2. **`scorer.py`** calculates the current ATS score (keyword overlap between resume and JD).
3. **`ats_optimizer.py`** sends the resume + JD gaps to Claude API for rewriting. Runs up to **3 passes** until the ATS score reaches ≥ 85 (configurable via `ATS_TARGET_SCORE`). If a pass makes the score worse, it is discarded.
4. **`storage.py`** writes the final tailored resume to `data/tailored/{job_id}.pdf`.

If a tailored PDF already exists for a job, the phase is skipped (idempotent — safe to re-run).

---

### Phase 3 — Apply

For each job:

1. **`browser.py`** opens the job URL in Playwright (Chromium, headless by default).
2. The page is checked for CAPTCHA / login walls. If detected, the job is marked `needs_human`, you receive an SMS + email, and the pipeline moves on.
3. **`form_detector.py`** sends the page HTML to Claude API to detect and map form fields to your `CANDIDATE_DATA`. Falls back to a screenshot-based Claude Vision pass if HTML detection finds nothing.
4. All fields are filled. File inputs receive the path to the tailored PDF.
5. Required fields are verified before the submit button is clicked.
6. Screenshots are saved: `data/screenshots/{job_id}_before.png` and `{job_id}_after.png`.
7. Outcome (`applied` / `failed` / `needs_human`) is appended to `data/results.json`.

**Retry policy:** failed phases retry up to 2 times before being marked `failed`. The pipeline continues regardless — no job blocks another.

---

### Phase 4 — Reporting

A report is generated and emailed after every **10 jobs** processed (configurable via `REPORT_EVERY_N_JOBS`), and once more at the end of each pipeline run.

**Report contents:**
- Summary: applied / failed / needs-human counts, average ATS and compatibility scores
- Detail table: title, company, scores, status, URL, timestamp
- Attached CSV with the same data

**Email subject format:**
```
Job Application Report — Batch 1 (2026-05-12)
```

---

### Error Notifications

Every error in any phase triggers **both** of:

| Channel | Content |
|---|---|
| **SMS (Twilio)** | Job ID, phase name, short error summary (≤ 200 chars) |
| **Email** | Full HTML email with job details + Python traceback |

**Human-check gate** (CAPTCHA, login wall):
- Job is marked `needs_human` in results.json
- SMS sent immediately: "Human check needed — [Job ID] — [URL]"
- Email sent with job details and direct link
- Pipeline skips to next job — no retries

No `.env` values are ever included in error messages or logs.

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Single file
pytest tests/test_compatibility.py -v
pytest tests/test_ats_optimizer.py -v
pytest tests/test_browser.py -v
```

All external calls (Apify, Claude API, Twilio) are mocked — tests run without any API keys.

---

## Customising Criteria

Edit `DEFAULT_CRITERIA` in [`src/phase1_scrape/criteria_filter.py`](src/phase1_scrape/criteria_filter.py):

```python
DEFAULT_CRITERIA = {
    "title_keywords": ["software", "engineer", "developer", "backend", "python"],
    "exclude_title_keywords": ["manager", "director", "vp", "intern"],
    "locations": [],              # empty = accept all locations
    "job_types": ["FULLTIME"],
    "min_salary": None,           # e.g. 1000000 for ₹10 LPA
    "exclude_companies": [],      # e.g. ["Infosys", "TCS"]
}
```

To target a different city or role, update your `.env`:
```bash
JOB_LOCATION=bangalore
JOB_KEYWORD=backend engineer
```

To use the paid LinkedIn actor or Indeed, change the `platform` argument in [`src/orchestrator.py`](src/orchestrator.py):
```python
raw_jobs = scrape_jobs(platform="indeed")
```

---

## Known Limitations

- **LinkedIn login wall** — LinkedIn may require login for some job listings. The pipeline detects this and sends a human-check alert instead of failing silently.
- **React/SPA forms** — Uses `page.type(delay=50)` instead of `page.fill()` to trigger `onChange` events. Some highly custom SPAs may still need manual intervention.
- **Headless detection** — Some job sites detect headless Chrome. Set `HEADLESS=false` in `.env` as a workaround, or extend `browser.py` with a stealth plugin.
- **Twilio free trial** — Only sends SMS to verified numbers. Upgrade to a paid account for production.
- **PDF formatting** — The ATS optimizer works on extracted text and regenerates a clean PDF via reportlab. Complex original PDF layouts (columns, tables, graphics) are simplified to plain text layout in the tailored version.
- **pdfplumber bullet characters** — Non-standard bullet glyphs are normalised to `•` automatically.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `EnvironmentError: Missing required environment variable: X` | Add the missing key to your `.env` file |
| `FileNotFoundError: Base resume not found` | Place your resume at `data/resume_base.pdf` |
| `No qualified jobs in queue` | Lower `COMPATIBILITY_THRESHOLD` in `.env`, or broaden `JOB_KEYWORD` |
| SMS not received | Check Twilio free trial limits; ensure `ALERT_TO_NUMBER` is verified |
| Email not sent | Check SendGrid API key or Gmail App Password; ensure 2FA is enabled for Gmail |
| Playwright TimeoutError | Set `HEADLESS=false` to watch the browser; the site may need a login or has changed its layout |
| ATS score never reaches 85 | Lower `ATS_TARGET_SCORE` in `.env`, or enrich your base resume with more keywords |
| `json.JSONDecodeError` from Claude | Usually a transient API issue — the pipeline retries automatically |
