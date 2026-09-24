"""
Delivery of one-time codes by email.

Uses Django's configured EMAIL_BACKEND: real SMTP in production, the console
backend in local development. The code itself is never written to application
logs.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def deliver_otp(user, otp, subject=None) -> bool:
    minutes = max(int((otp.expires_at - otp.created_at).total_seconds() // 60), 1)
    body = (
        f"Your verification code is {otp.code}.\n\n"
        f"It expires in {minutes} minutes and can be used once.\n"
        "If you did not try to sign in, ignore this email and tell your administrator."
    )
    try:
        send_mail(
            subject or settings.OTP_EMAIL_SUBJECT,
            body,
            settings.OTP_EMAIL_SENDER,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Could not send OTP email to user %s", user.pk)
        return False
    return True
