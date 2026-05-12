"""Error email with full stack trace — SendGrid or Gmail SMTP."""
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from src import config


def _send_via_sendgrid(subject: str, html_body: str) -> bool:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content

    sg = sendgrid.SendGridAPIClient(api_key=config.SENDGRID_API_KEY)
    mail = Mail(
        from_email=Email(config.GMAIL_ADDRESS or "noreply@jobbot.local"),
        to_emails=To(config.REPORT_EMAIL_TO),
        subject=subject,
        html_content=Content("text/html", html_body),
    )
    response = sg.client.mail.send.post(request_body=mail.get())
    return response.status_code in (200, 202)


def _send_via_gmail(subject: str, html_body: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.REPORT_EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_ADDRESS, config.REPORT_EMAIL_TO, msg.as_string())
    return True


def send_error_email(job: dict, phase: str, exc: Exception) -> None:
    """Send a detailed error email with traceback. Never exposes .env values."""
    job_id = job.get("id", "unknown")
    title = job.get("title", "unknown")
    company = job.get("company", "unknown")
    tb = traceback.format_exc()

    subject = f"[JobBot ERROR] {phase} failed — {title} @ {company}"
    html_body = f"""
    <h2>Job Application Error</h2>
    <table>
      <tr><td><b>Job ID</b></td><td>{job_id}</td></tr>
      <tr><td><b>Title</b></td><td>{title}</td></tr>
      <tr><td><b>Company</b></td><td>{company}</td></tr>
      <tr><td><b>Phase</b></td><td>{phase}</td></tr>
      <tr><td><b>Error</b></td><td>{type(exc).__name__}: {str(exc)[:300]}</td></tr>
    </table>
    <h3>Traceback</h3>
    <pre>{tb}</pre>
    """

    try:
        if config.SENDGRID_API_KEY:
            ok = _send_via_sendgrid(subject, html_body)
        else:
            ok = _send_via_gmail(subject, html_body)
        if ok:
            logger.info(f"Error email sent for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to send error email: {e}")


def send_human_check_email(job: dict) -> None:
    subject = f"[JobBot] Human check needed — {job.get('title')} @ {job.get('company')}"
    html_body = f"""
    <h2>Manual Action Required</h2>
    <p>A CAPTCHA or login wall was detected on the following job application.</p>
    <table>
      <tr><td><b>Job ID</b></td><td>{job.get('id')}</td></tr>
      <tr><td><b>Title</b></td><td>{job.get('title')}</td></tr>
      <tr><td><b>Company</b></td><td>{job.get('company')}</td></tr>
      <tr><td><b>URL</b></td><td><a href="{job.get('url')}">{job.get('url')}</a></td></tr>
    </table>
    <p>Please complete this application manually.</p>
    """
    try:
        if config.SENDGRID_API_KEY:
            _send_via_sendgrid(subject, html_body)
        else:
            _send_via_gmail(subject, html_body)
        logger.info(f"Human-check email sent for job {job.get('id')}")
    except Exception as e:
        logger.error(f"Failed to send human-check email: {e}")
