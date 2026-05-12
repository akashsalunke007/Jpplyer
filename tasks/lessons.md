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
