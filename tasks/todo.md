# Task Queue

## Status key
- [ ] = todo
- [x] = done
- [~] = in progress

---

## Setup (do these before first run)

- [ ] Copy `.env.example` → `.env` and fill all values
- [ ] Add your resume as `data/resume_base.pdf`
- [ ] Fill in `CANDIDATE_PROFILE` and `CANDIDATE_DATA` in `src/orchestrator.py`
- [ ] Run `pip install -r requirements.txt`
- [ ] Run `playwright install chromium`
- [ ] Run `pytest tests/ -v` to verify all tests pass
- [ ] Do a dry run: `python src/orchestrator.py --dry-run`

## Enhancements (future)

- [ ] Add Indeed platform support (criteria_filter already platform-agnostic)
- [ ] Persist ATS score in jobs_queue.json after resume phase
- [ ] Add dedup: skip jobs already in results.json
- [ ] Add LinkedIn Easy Apply (1-click) detection in form_detector
- [ ] Dashboard: serve results.json as a live HTML page
