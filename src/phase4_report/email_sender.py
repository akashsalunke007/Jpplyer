"""Send batch reports via SendGrid or Gmail SMTP with CSV attachment."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone
from loguru import logger
from src import config


def _build_message(subject: str, html_body: str, csv_data: str, batch_num: int) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS or "noreply@jobbot.local"
    msg["To"] = config.REPORT_EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    attachment = MIMEBase("text", "csv")
    attachment.set_payload(csv_data.encode())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        f'attachment; filename="batch_{batch_num}_report.csv"',
    )
    msg.attach(attachment)
    return msg


def send_report(html_body: str, csv_data: str, batch_num: int) -> None:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    subject = f"Job Application Report — Batch {batch_num} ({date_str})"

    if config.SENDGRID_API_KEY:
        _send_sendgrid(subject, html_body, csv_data, batch_num)
    else:
        _send_gmail(subject, html_body, csv_data, batch_num)


def _send_sendgrid(subject: str, html_body: str, csv_data: str, batch_num: int) -> None:
    import sendgrid
    from sendgrid.helpers.mail import (
        Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
    )
    import base64

    sg = sendgrid.SendGridAPIClient(api_key=config.SENDGRID_API_KEY)
    mail = Mail(
        from_email=Email(config.GMAIL_ADDRESS or "noreply@jobbot.local"),
        to_emails=To(config.REPORT_EMAIL_TO),
        subject=subject,
        html_content=Content("text/html", html_body),
    )
    encoded_csv = base64.b64encode(csv_data.encode()).decode()
    attachment = Attachment(
        file_content=FileContent(encoded_csv),
        file_name=FileName(f"batch_{batch_num}_report.csv"),
        file_type=FileType("text/csv"),
        disposition=Disposition("attachment"),
    )
    mail.attachment = attachment
    response = sg.client.mail.send.post(request_body=mail.get())
    if response.status_code in (200, 202):
        logger.info(f"Report email sent via SendGrid: batch {batch_num}")
    else:
        logger.error(f"SendGrid returned {response.status_code}")


def _send_gmail(subject: str, html_body: str, csv_data: str, batch_num: int) -> None:
    msg = _build_message(subject, html_body, csv_data, batch_num)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_ADDRESS, config.REPORT_EMAIL_TO, msg.as_string())
    logger.info(f"Report email sent via Gmail: batch {batch_num}")
