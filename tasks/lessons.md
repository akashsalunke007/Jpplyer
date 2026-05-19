# Lessons Learned

_Update this file after every bug fix or correction._

---

## Lesson 2026-05-12: Initial project build
**What went wrong:** N/A — initial build.
**Root cause:** N/A
**Rules added:**
- Never read `.env` directly — always go through `src/config.py`.
- Normalise bullet characters from pdfplumber to `•` before ATS processing (pdfplumber mangles multi-byte bullet glyphs).
- Use `page.type(selector, value, delay=50)` instead of `page.fill()` for React SPAs — fill() does not trigger onChange events.
- Always screenshot before AND after submit — saves debugging time when form state is unexpected.
- Strip markdown fences (`\`\`\`json`) before calling `json.loads()` on all Claude API responses.
- Never expose `.env` values in error messages, logs, or email bodies.

---

## Lesson 2026-05-19: Migrated to fully free stack
**What went wrong:** Initial build used paid services (Anthropic API, Apify actors, Twilio SMS, SendGrid).
**Root cause:** Default to well-known SDKs without checking free alternatives.
**Rules added:**
- Use **JobSpy** (open-source) instead of Apify actors — no API key, no cost, scrapes LinkedIn + Indeed directly.
- Use **Google Gemini 1.5 Flash** (free tier: 1,500 req/day) instead of Anthropic Claude for scoring, ATS rewriting, and form detection.
- Use **Telegram Bot** (free forever) instead of Twilio for phone notifications — setup takes 2 minutes via @BotFather.
- Use **Gmail SMTP** (free, 500/day) instead of SendGrid for all email — requires App Password with 2FA enabled.
- Gemini returns markdown fences more often than Claude — always strip with `re.sub(r"^```(?:json)?", "", text)` before `json.loads()`.
- Gemini free tier is 15 RPM — do not add `time.sleep()` manually; let the 429 retry handler in orchestrator catch it naturally.
