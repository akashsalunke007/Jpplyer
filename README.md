# Jpplyer — Automated Job Application Pipeline

An end-to-end Python pipeline that scrapes job listings, scores them for compatibility, tailors your resume using ATS optimisation, applies automatically via browser automation, and sends you email notifications throughout.

---

## Tech Stack

| Component | Service | Notes |
|---|---|---|
| Job scraping | **JobSpy** (open-source, no API key) | Scrapes LinkedIn + Indeed directly |
| AI scoring & resume | **OpenAI GPT-4o-mini** | Fast, cheap — $0.15/1M input tokens |
| Form detection | **OpenAI Vision (GPT-4o-mini)** | Reads page screenshots to map fields |
| Email notifications & reports | **Gmail SMTP** | Free, 500 emails/day |
| Browser automation | **Playwright** (open-source) | Fills and submits job application forms |
| PDF processing | **pdfplumber + reportlab** (open-source) | Extracts and rewrites resume PDFs |

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [1. OpenAI API Key](#1-openai-api-key)
  - [2. Gmail App Password](#2-gmail-app-password)
  - [3. Base Resume](#3-base-resume)
  - [4. Candidate Profile](#4-candidate-profile)
  - [5. Full .env Reference](#5-full-env-reference)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [How Each Phase Works](#how-each-phase-works)
  - [Phase 1 — Scrape & Filter](#phase-1--scrape--filter)
  - [Phase 2 — Resume Tailoring](#phase-2--resume-tailoring)
  - [Phase 3 — Apply](#phase-3--apply)
  - [Phase 4 — Reporting](#phase-4--reporting)
  - [Email Notifications](#email-notifications)
- [Running Tests](#running-tests)
- [Customising Criteria](#customising-criteria)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)

---

## Overview

```
JobSpy (LinkedIn + Indeed)
    → criteria hard-filter (title / location / type)
        → GPT-4o-mini scores job vs your profile (≥ 75%)
            → GPT-4o-mini rewrites resume for ATS (target ≥ 85%)
                → Playwright fills form & submits application
                    → Gmail alert on any error or human-check gate
                        → Gmail batch report every 10 jobs
```

---

## Architecture

```
main.py  (entry point — always run from project root)
│
└─ src/orchestrator.py
    │
    ├─ Phase 1: Scrape & filter
    │   ├─ apify_client.py        JobSpy scrapes LinkedIn + Indeed (no API key)
    │   ├─ criteria_filter.py     keyword / location / type / salary hard filters
    │   └─ compatibility.py       GPT-4o-mini scores each JD vs your profile (0–100)
    │                              writes qualified jobs (≥ 75) to data/jobs_queue.json
    │
    ├─ Phase 2: Resume tailoring  (per job)
    │   ├─ storage.py             reads data/resume_base.pdf (read-only, pdfplumber)
    │   ├─ ats_optimizer.py       GPT-4o-mini rewrites resume (up to 3 passes)
    │   ├─ scorer.py              simulates ATS score after each pass
    │   └─ storage.py             saves tailored PDF → data/tailored/{job_id}.pdf
    │
    ├─ Phase 3: Apply             (per job)
    │   ├─ browser.py             opens job URL in Playwright (Chromium)
    │   ├─ form_detector.py       GPT-4o-mini Vision maps form fields to your data
    │   ├─ browser.py             fills fields, uploads tailored PDF, submits
    │   └─ result_logger.py       appends outcome to data/results.json
    │
    ├─ Phase 4: Report            (every 10 jobs)
    │   ├─ report_generator.py    builds HTML + CSV from results.json
    │   └─ email_sender.py        sends via Gmail SMTP
    │
    └─ Notifications              (any phase error)
        ├─ email_alert.py         error email with full traceback (Gmail)
        └─ orchestrator.py        retries up to 2×, marks failed, continues
```

---

## Prerequisites

- **Python 3.11+**
- An **OpenAI account** with API credits — [platform.openai.com](https://platform.openai.com)
- A **Gmail account** for email notifications and reports

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

---

### 1. OpenAI API Key

1. Go to **[platform.openai.com/api-keys](https://platform.openai.com/api-keys)**
2. Click **Create new secret key** → give it a name (e.g. `Jpplyer`)
3. Copy and paste into `.env`:

```bash
OPENAI_API_KEY=sk-proj-...
```

> **Model used:** `gpt-4o-mini` — supports text and vision, very cost-effective.  
> Typical cost per full run (20 jobs): **< $0.05** (5 cents).

---

### 2. Gmail App Password

Used to send all error alerts and batch reports.

1. Enable **2-Step Verification** on your Google account:
   `myaccount.google.com → Security → 2-Step Verification`
2. Go to **App passwords**:
   `myaccount.google.com → Security → 2-Step Verification → App passwords`
3. Select app: **Mail** | Select device: **Other** → name it `Jpplyer`
4. Copy the 16-character password into `.env`:

```bash
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # 16-char App Password
REPORT_EMAIL_TO=you@gmail.com            # where reports & alerts are delivered
```

> `REPORT_EMAIL_TO` can be the same as `GMAIL_ADDRESS` or a different inbox.

---

### 3. Base Resume

Place your resume PDF at:
```
data/resume_base.pdf
```

This file is **never modified**. Tailored versions are written to `data/tailored/{job_id}.pdf`.

---

### 4. Candidate Profile

Open [`src/orchestrator.py`](src/orchestrator.py) and update the two blocks near the top with your real details:

```python
CANDIDATE_PROFILE = """
Name: Soni Kori
Current role: System Engineer at Infosys (Sep 2025 – Apr 2026)
Total experience: ~1 year (6+ months professional + 5 months internship at CDAC)
Skills: Java, Python, JavaScript, Spring Boot, Flask, HTML5, CSS3, MySQL, PostgreSQL,
        Git, GitHub, Agile/Scrum, OOP, MVC, REST APIs, Scikit-learn, Pandas
Education: MCA, Banasthali Vidyapeeth, 2025
Location: Bangalore, India
Preferred: Full-time, Associate / Junior Software Engineer / Full Stack Developer roles
"""

CANDIDATE_DATA = {
    "full_name": "Soni Kori",
    "email": "sonikori9999@gmail.com",
    "phone": "+919634961848",
    "linkedin": "https://linkedin.com/in/soni-kori-8b074a22a",
    ...
}
```

> These are already filled with Soni Kori's details from the uploaded resume. Edit if needed.

---

### 5. Full `.env` Reference

```bash
# ── OpenAI ────────────────────────────────────────────────────
OPENAI_API_KEY=sk-proj-...

# ── Gmail SMTP ────────────────────────────────────────────────
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
REPORT_EMAIL_TO=you@gmail.com

# ── Job Search ────────────────────────────────────────────────
JOB_KEYWORD=Associate Software Engineer
JOB_LOCATION=Bangalore, India
JOB_RESULTS_WANTED=50
JOB_HOURS_OLD=168                  # jobs posted in last 7 days

# ── Playwright ────────────────────────────────────────────────
HEADLESS=false                     # false = visible browser window

# ── Pipeline Tuning ───────────────────────────────────────────
COMPATIBILITY_THRESHOLD=75         # min AI score to queue a job
ATS_TARGET_SCORE=85                # target ATS score before applying
REPORT_EVERY_N_JOBS=10             # email report every N jobs
MAX_JOBS_TO_SCORE=20               # max jobs sent to OpenAI per run
```

---

## Project Structure

```
Jpplyer/
├── main.py                         entry point — run: python main.py
├── .env.example                    environment variable template
├── .env                            your secrets — never commit this
├── requirements.txt                Python dependencies
├── README.md
├── CLAUDE.md                       project spec for Claude Code
│
├── src/
│   ├── config.py                   central env loader — all config goes here
│   ├── orchestrator.py             pipeline logic + CANDIDATE_PROFILE / CANDIDATE_DATA
│   │
│   ├── phase1_scrape/
│   │   ├── apify_client.py         JobSpy scraper (LinkedIn + Indeed, no API key)
│   │   ├── criteria_filter.py      hard keyword / location / type / salary filters
│   │   └── compatibility.py        GPT-4o-mini job–profile compatibility scorer
│   │
│   ├── phase2_resume/
│   │   ├── storage.py              read base PDF (pdfplumber), write tailored (reportlab)
│   │   ├── ats_optimizer.py        GPT-4o-mini ATS rewriter — up to 3 passes
│   │   └── scorer.py               keyword-overlap ATS simulation scorer
│   │
│   ├── phase3_apply/
│   │   ├── browser.py              async Playwright automation (fill, upload, submit)
│   │   ├── form_detector.py        GPT-4o-mini Vision / HTML form field mapper
│   │   └── result_logger.py        append-only JSON outcome logger
│   │
│   ├── phase4_report/
│   │   ├── report_generator.py     HTML + CSV batch report builder
│   │   └── email_sender.py         Gmail SMTP report dispatcher
│   │
│   └── notifications/
│       ├── email_alert.py          error + human-check emails (Gmail SMTP)
│       └── sms.py                  no-op stubs (kept for import compatibility)
│
├── data/
│   ├── resume_base.pdf             base resume — read-only, never modified
│   ├── tailored/                   auto-generated per-job PDFs
│   ├── screenshots/                before/after screenshots per application
│   ├── jobs_queue.json             qualified jobs written after Phase 1
│   └── results.json                running log of all outcomes
│
├── tests/
│   ├── test_compatibility.py       filter + OpenAI scoring tests (mocked)
│   ├── test_ats_optimizer.py       ATS scorer + OpenAI optimizer tests (mocked)
│   └── test_browser.py             result logger + form detector parse tests
│
└── tasks/
    ├── todo.md                     setup checklist + future enhancements
    └── lessons.md                  bugs fixed + rules learned
```

---

## Usage

### Full pipeline run
```bash
python main.py
```
Runs all 4 phases in sequence: scrape → tailor resume → apply → final report.

### Dry run — no submissions, no emails
```bash
python main.py --dry-run
```
Scrapes jobs and tailors resumes, then prints what would be applied without submitting anything or sending emails.

### Run a single phase
```bash
python main.py --phase scrape    # scrape + filter + score → writes jobs_queue.json
python main.py --phase resume    # tailor resumes for jobs already in queue
python main.py --phase apply     # apply to queued jobs (resumes must already exist)
```

### Run tests
```bash
pytest tests/ -v
```

---

## How Each Phase Works

### Phase 1 — Scrape & Filter

**`apify_client.py`** uses **JobSpy** to scrape LinkedIn and Indeed simultaneously — no API key, no cost. Results are deduplicated and normalised into a consistent schema.

**`criteria_filter.py`** drops jobs that fail hard rules: wrong title keywords, excluded words (e.g. "manager", "director"), wrong location, non-full-time. Configurable via `DEFAULT_CRITERIA`.

**`compatibility.py`** sends each job description + your `CANDIDATE_PROFILE` to **GPT-4o-mini**. The model returns a 0–100 compatibility score with reasons and gaps. Only jobs scoring **≥ 75** (configurable) advance to `data/jobs_queue.json`. Capped at `MAX_JOBS_TO_SCORE` per run to manage API spend.

---

### Phase 2 — Resume Tailoring

For each queued job:

1. `storage.py` extracts text from `data/resume_base.pdf` using `pdfplumber` (bullet chars normalised to `•`)
2. `scorer.py` calculates the current ATS score via keyword overlap with the JD
3. `ats_optimizer.py` sends resume + missing keywords to **GPT-4o-mini** for rewriting — up to **3 passes** until score ≥ 85. Passes that make the score worse are discarded
4. `storage.py` writes the tailored resume to `data/tailored/{job_id}.pdf`

Already-tailored jobs are skipped — safe to re-run without wasting API calls.

---

### Phase 3 — Apply

For each job:

1. Playwright opens the job URL in Chromium (`HEADLESS=false` shows the browser window)
2. Page is scanned for CAPTCHA / login walls → triggers a human-check email and skips to next job
3. **GPT-4o-mini** analyses the page HTML to detect and map form fields to your `CANDIDATE_DATA`. Falls back to GPT-4o-mini Vision on a screenshot if HTML detection finds nothing
4. All fields are filled; file inputs receive the path to the tailored PDF
5. Required fields are verified before clicking Submit
6. Screenshots saved: `data/screenshots/{job_id}_before.png` and `{job_id}_after.png`
7. Outcome (`applied` / `failed` / `needs_human`) logged to `data/results.json`

**Retry policy:** each job retries up to 2× before being marked `failed`. The pipeline always continues — one bad job never stops the rest.

---

### Phase 4 — Reporting

A report is generated and emailed after every **10 jobs** (configurable via `REPORT_EVERY_N_JOBS`) and once more at the very end of each run.

**Email subject:**
```
Job Application Report — Batch 1 (2026-05-19)
```

**Contains:**
- Summary: applied / failed / needs-human counts, avg ATS score, avg compatibility score
- Full detail table: title, company, scores, status, URL, timestamp
- Attached CSV with the same data

---

### Email Notifications

All alerts are sent from `GMAIL_ADDRESS` to `REPORT_EMAIL_TO` via Gmail SMTP.

| Trigger | Subject | Content |
|---|---|---|
| Any phase error | `[JobBot ERROR] {phase} failed — {title} @ {company}` | Job details + full Python traceback |
| CAPTCHA / login wall | `[JobBot] Human check needed — {title} @ {company}` | Job details + direct URL to complete manually |
| Batch report | `Job Application Report — Batch N (date)` | HTML summary + CSV attachment |

---

## Running Tests

All OpenAI calls are mocked — tests run fully offline with no API key needed.

```bash
# All tests
pytest tests/ -v

# Individual files
pytest tests/test_compatibility.py -v
pytest tests/test_ats_optimizer.py -v
pytest tests/test_browser.py -v
```

---

## Customising Criteria

Edit `DEFAULT_CRITERIA` in [`src/phase1_scrape/criteria_filter.py`](src/phase1_scrape/criteria_filter.py):

```python
DEFAULT_CRITERIA = {
    "title_keywords": [
        "software", "engineer", "developer", "full stack", "backend",
        "java", "python", "flask", "spring", "associate", "junior",
    ],
    "exclude_title_keywords": ["manager", "director", "vp", "lead", "intern"],
    "locations":              [],       # empty = accept all locations
    "job_types":              ["FULLTIME"],
    "min_salary":             None,     # e.g. 500000 for ₹5 LPA
    "exclude_companies":      [],       # e.g. ["Wipro", "HCL"]
}
```

Change search term, city, or volume via `.env`:

```bash
JOB_KEYWORD=Associate Software Engineer
JOB_LOCATION=Bangalore, India
JOB_RESULTS_WANTED=50
JOB_HOURS_OLD=72              # only last 3 days
MAX_JOBS_TO_SCORE=20          # cap OpenAI calls per run
```

To scrape only one platform:
```python
# in src/orchestrator.py → phase_scrape()
raw_jobs = scrape_jobs(platforms=["linkedin"])          # LinkedIn only
raw_jobs = scrape_jobs(platforms=["indeed"])            # Indeed only
raw_jobs = scrape_jobs(platforms=["linkedin", "indeed"]) # both (default)
```

---

## Known Limitations

- **LinkedIn throttling** — LinkedIn may temporarily block scraping if run too frequently. Space runs a few hours apart, or reduce `JOB_RESULTS_WANTED`.
- **React/SPA forms** — Uses `page.type(delay=50)` instead of `page.fill()` to trigger `onChange` events. Some custom SPAs may need manual intervention.
- **HEADLESS=false** — Currently set to show the browser window. Set `HEADLESS=true` in `.env` for unattended background runs.
- **OpenAI rate limits** — On hitting a 429, the pipeline waits and retries automatically (up to 3 attempts with increasing delays).
- **PDF layout** — The ATS optimizer works on extracted text and regenerates a clean plain-text PDF. Complex original layouts (columns, tables, graphics) are simplified.
- **Gmail 2FA required** — App Passwords only work when 2-Step Verification is enabled on your Google account.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `EnvironmentError: Missing required environment variable: X` | Add the missing key to your `.env` file |
| `ModuleNotFoundError: No module named 'src'` | Always run `python main.py` from the project root, not `python src/orchestrator.py` |
| `FileNotFoundError: Base resume not found` | Place your resume at `data/resume_base.pdf` |
| `No qualified jobs in queue` | Lower `COMPATIBILITY_THRESHOLD` in `.env`, or broaden `JOB_KEYWORD` |
| `openai.AuthenticationError` | Check your `OPENAI_API_KEY` in `.env` — ensure no extra spaces |
| `openai.RateLimitError` | Add credits at [platform.openai.com/billing](https://platform.openai.com/billing) |
| Email not received | Check spam; ensure 2FA is on and you used the App Password, not your account password |
| `SMTPAuthenticationError` | Regenerate App Password at `myaccount.google.com → Security → App passwords` |
| Playwright `TimeoutError` | `HEADLESS=false` is already set — watch the browser; the site may need a login |
| ATS score never reaches 85 | Lower `ATS_TARGET_SCORE` in `.env`, or enrich your base resume with more keywords |
| JobSpy returns 0 results | Try a broader keyword, increase `JOB_HOURS_OLD`, or check internet connection |
