"""Resume load/save — pdfplumber for extraction, reportlab for PDF generation."""
import re
from pathlib import Path
import pdfplumber
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from loguru import logger
from src import config


def load_base_resume_text() -> str:
    """Extract full text from the base resume PDF."""
    if not config.RESUME_BASE.exists():
        raise FileNotFoundError(f"Base resume not found: {config.RESUME_BASE}")

    with pdfplumber.open(config.RESUME_BASE) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]

    text = "\n".join(pages)
    # Normalise bullet characters that pdfplumber sometimes mangles
    text = re.sub(r"[•·▪‣⁃◦]", "•", text)
    return text


def tailored_path(job_id: str) -> Path:
    return config.TAILORED_DIR / f"{job_id}.pdf"


def tailored_exists(job_id: str) -> bool:
    return tailored_path(job_id).exists()


def save_tailored_resume(job_id: str, resume_text: str) -> Path:
    """Write resume_text to a PDF at data/tailored/{job_id}.pdf."""
    config.TAILORED_DIR.mkdir(parents=True, exist_ok=True)
    dest = tailored_path(job_id)
    _text_to_pdf(resume_text, dest)
    logger.info(f"Saved tailored resume: {dest}")
    return dest


def _text_to_pdf(text: str, dest: Path) -> None:
    doc = SimpleDocTemplate(
        str(dest),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
    )
    story = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 6))
            continue
        # Escape XML special chars for reportlab
        stripped = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(stripped, body_style))

    doc.build(story)
