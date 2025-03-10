import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import emails
from jinja2 import Template

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent.parent.parent / "templates" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER_EMAIL:
        smtp_options["user"] = settings.SMTP_USER_EMAIL
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"send email result: {response}")


def request_authcode_email(*, username: str, auth_code: str) -> EmailData:
    subject = f"🔒Authentication Required🔒"
    html_content = render_email_template(
        template_name="auth_code.html",
        context={
            "username": username,
            "auth_code": auth_code,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def request_code_reset_token(*, token: str) -> EmailData:
    subject = f"🔑 Code Reset Request 🔑"
    html_content = render_email_template(
        template_name="code_reset.html",
        context={
            "token": token,
            "support_mail": "popoolakejiah3@gmail.com",
            "support_mail_link": "mailto:popoolakejiah3@gmail.com",
        },
    )
    return EmailData(html_content=html_content, subject=subject)
