"""Optional SMTP delivery. No credentials, tokens or transport errors in diagnostics."""
import asyncio
from email.message import EmailMessage
import smtplib
import ssl
from urllib.parse import urlsplit, quote
from fastapi import HTTPException
from app.config import settings


def require_configuration():
    if not settings.features.account_invitation_email:
        raise HTTPException(403, "Invitation email delivery is disabled.")
    if not all((settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from_email, settings.frontend_url)):
        raise HTTPException(503, "Invitation email is not configured. Contact the platform administrator.")
    base = urlsplit(settings.frontend_url)
    if base.scheme not in ("http", "https") or not base.hostname or base.username or base.password or base.query or base.fragment:
        raise HTTPException(503, "Invitation email web address is not configured correctly.")
    if settings.app_env.lower() == "production" and base.scheme != "https":
        raise HTTPException(503, "Invitation email requires a secure web address.")


def _send(recipient, token, account_name):
    message = EmailMessage()
    message["Subject"] = "Invitation to join AI QA Squad"
    message["From"] = str(settings.smtp_from_email)
    message["To"] = recipient
    link = settings.frontend_url.rstrip("/") + "/auth?mode=signup#invite=" + quote(token, safe="")
    message.set_content(f"You have been invited to join {account_name or 'your customer account'} on AI QA Squad.\n\nSign up with this email address using this seven-day invitation:\n{link}\n\nIf you did not expect this invitation, you can ignore it.")
    context = ssl.create_default_context()
    if settings.smtp_port == 465:
        connection = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10, context=context)
    else:
        connection = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
    with connection as smtp:
        if settings.smtp_port != 465:
            smtp.ehlo(); smtp.starttls(context=context); smtp.ehlo()
        smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


async def send_invitation(recipient, token, account_name):
    require_configuration()
    await asyncio.to_thread(_send, recipient, token, account_name)
