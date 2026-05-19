"""Error + human-check emails via Gmail SMTP — completely free."""
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from src import config


def _send(subject: str, html_body: str) -> bool:
    """Send an HTML email from GMAIL_ADDRESS to REPORT_EMAIL_TO."""
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
        logger.warning("Gmail not configured — skipping email alert")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.GMAIL_ADDRESS
        msg["To"] = config.REPORT_EMAIL_TO
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            server.sendmail(config.GMAIL_ADDRESS, config.REPORT_EMAIL_TO, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Gmail alert send failed: {e}")
        return False


def send_error_email(job: dict, phase: str, exc: Exception) -> None:
    """Send a detailed error email with traceback. Never exposes .env values."""
    job_id = job.get("id", "unknown")
    title = job.get("title", "unknown")
    company = job.get("company", "unknown")
    tb = traceback.format_exc()

    subject = f"[JobBot ERROR] {phase} failed — {title} @ {company}"
    html_body = f"""
    <h2 style="color:#c0392b;">Job Application Error</h2>
    <table cellpadding="6" style="border-collapse:collapse;">
      <tr><td><b>Job ID</b></td><td>{job_id}</td></tr>
      <tr><td><b>Title</b></td><td>{title}</td></tr>
      <tr><td><b>Company</b></td><td>{company}</td></tr>
      <tr><td><b>Phase</b></td><td>{phase}</td></tr>
      <tr><td><b>Error</b></td><td><code>{type(exc).__name__}: {str(exc)[:300]}</code></td></tr>
    </table>
    <h3>Traceback</h3>
    <pre style="background:#f5f5f5;padding:12px;font-size:12px;">{tb}</pre>
    """
    if _send(subject, html_body):
        logger.info(f"Error email sent for job {job_id}")


def send_human_check_email(job: dict) -> None:
    """Notify that a CAPTCHA/login wall was hit and manual action is needed."""
    subject = f"[JobBot] Human check needed — {job.get('title')} @ {job.get('company')}"
    html_body = f"""
    <h2 style="color:#e67e22;">Manual Action Required</h2>
    <p>A CAPTCHA or login wall was detected. Please complete this application manually.</p>
    <table cellpadding="6" style="border-collapse:collapse;">
      <tr><td><b>Job ID</b></td><td>{job.get('id')}</td></tr>
      <tr><td><b>Title</b></td><td>{job.get('title')}</td></tr>
      <tr><td><b>Company</b></td><td>{job.get('company')}</td></tr>
      <tr><td><b>URL</b></td>
          <td><a href="{job.get('url')}">{job.get('url')}</a></td></tr>
    </table>
    """
    if _send(subject, html_body):
        logger.info(f"Human-check email sent for job {job.get('id')}")
