"""ATS simulation scorer — keyword overlap heuristic."""
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z][a-z0-9+#.]*\b", text.lower())


def _extract_jd_keywords(job_description: str, top_n: int = 40) -> list[str]:
    """Return the most frequent meaningful words from the JD."""
    stopwords = {
        "the", "and", "or", "a", "an", "in", "on", "at", "to", "for", "of",
        "with", "is", "are", "was", "be", "will", "we", "you", "our", "your",
        "this", "that", "have", "has", "job", "work", "role", "team", "must",
        "can", "not", "but", "from", "as", "by", "it", "its", "if", "so",
        "they", "their", "all", "who", "what", "when", "how", "any", "up",
    }
    tokens = [t for t in _tokenize(job_description) if t not in stopwords and len(t) > 2]
    return [word for word, _ in Counter(tokens).most_common(top_n)]


def calculate_ats_score(resume_text: str, job_description: str) -> tuple[int, list[str]]:
    """Return (score_0_to_100, missing_keywords)."""
    keywords = _extract_jd_keywords(job_description)
    if not keywords:
        return 50, []

    resume_lower = resume_text.lower()
    matched = [kw for kw in keywords if kw in resume_lower]
    missing = [kw for kw in keywords if kw not in resume_lower]

    score = int(len(matched) / len(keywords) * 100)
    return score, missing
