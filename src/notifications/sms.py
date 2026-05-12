"""Twilio SMS alert sender."""
from twilio.rest import Client
from loguru import logger
from src import config


def send_sms(message: str) -> bool:
    """Send an SMS to ALERT_TO_NUMBER. Returns True on success."""
    try:
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message[:1600],  # Twilio max body length
            from_=config.TWILIO_FROM_NUMBER,
            to=config.ALERT_TO_NUMBER,
        )
        logger.info(f"SMS sent: SID={msg.sid}")
        return True
    except Exception as e:
        logger.error(f"SMS send failed: {e}")
        return False


def notify_error(job_id: str, phase: str, error_summary: str) -> None:
    send_sms(f"[JobBot ERROR]\nJob: {job_id}\nPhase: {phase}\nError: {error_summary[:200]}")


def notify_human_check(job_id: str, url: str) -> None:
    send_sms(f"[JobBot] Human check needed\nJob: {job_id}\nURL: {url}\nPlease complete manually.")
