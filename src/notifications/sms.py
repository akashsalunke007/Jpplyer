"""
Notification stubs — phone/SMS notifications removed in favour of email-only.
These no-ops keep the orchestrator import working without any changes.
All real alerts are sent via src/notifications/email_alert.py (Gmail SMTP).
"""
from loguru import logger


def notify_error(job_id: str, phase: str, error_summary: str) -> None:
    """No-op — error details are sent by email_alert.send_error_email()."""
    logger.debug(f"[notify_error stub] job={job_id} phase={phase}")


def notify_human_check(job_id: str, url: str) -> None:
    """No-op — human-check alert is sent by email_alert.send_human_check_email()."""
    logger.debug(f"[notify_human_check stub] job={job_id}")
