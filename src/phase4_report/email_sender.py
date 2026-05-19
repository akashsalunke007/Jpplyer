"""Send batch reports via Gmail SMTP with CSV attachment — completely free."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone
from loguru import logger
from src import config


def send_report(html_body: str, csv_data: str, batch_num: int) -> None:
    """Email an HTML report with attached CSV to REPORT_EMAIL_TO via Gmail SMTP."""
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
        logger.warning("Gmail not configured — skipping report email")
        return

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    subject = f"Job Application Report — Batch {batch_num} ({date_str})"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.REPORT_EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    # Attach CSV
    attachment = MIMEBase("text", "csv")
    attachment.set_payload(csv_data.encode())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        f'attachment; filename="batch_{batch_num}_report.csv"',
    )
    msg.attach(attachment)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            server.sendmail(config.GMAIL_ADDRESS, config.REPORT_EMAIL_TO, msg.as_string())
        logger.info(f"Batch {batch_num} report emailed to {config.REPORT_EMAIL_TO}")
    except Exception as e:
        logger.error(f"Report email failed: {e}")
