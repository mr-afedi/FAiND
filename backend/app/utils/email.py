"""
Email sending utility. Supports real SMTP and console-only mode for development.
Set EMAIL_CONSOLE_MODE=True in .env to print emails to the console.
"""
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an email. Falls back to console logging in development mode."""
    if settings.EMAIL_CONSOLE_MODE or not settings.SMTP_HOST:
        import re
        plain = re.sub(r'<[^>]+>', '', html_body).strip()
        print("\n" + "=" * 60)
        print(f"[EMAIL] To: {to}")
        print(f"[EMAIL] Subject: {subject}")
        print("-" * 60)
        print(plain)
        print("=" * 60 + "\n", flush=True)
        return

    import aiosmtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )


async def send_verification_email(to: str, full_name: str, code: str) -> None:
    subject = "Verify your FAiND account"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">
      <h2 style="color: #3b82f6;">Welcome to FAiND, {full_name}!</h2>
      <p>Use the 6-digit code below to verify your email address.</p>
      <p>This code expires in <strong>15 minutes</strong>.</p>
      <div style="background:#f0f9ff;border:2px solid #3b82f6;border-radius:8px;padding:24px;text-align:center;margin:24px 0;">
        <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1e40af;">{code}</span>
      </div>
      <p style="color:#6b7280;font-size:14px;">
        If you did not create a FAiND account, you can safely ignore this email.
      </p>
    </div>
    """
    await send_email(to, subject, html)


async def send_authority_otp_email(to: str, code: str) -> None:
    subject = "Your FAiND authority login code"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">
      <h2 style="color: #3b82f6;">Authority sign-in</h2>
      <p>Use the 6-digit code below to complete your login.</p>
      <p>This code expires in <strong>10 minutes</strong>.</p>
      <div style="background:#f0f9ff;border:2px solid #3b82f6;border-radius:8px;padding:24px;text-align:center;margin:24px 0;">
        <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1e40af;">{code}</span>
      </div>
      <p style="color:#6b7280;font-size:14px;">
        If you did not attempt to sign in, contact your administrator immediately.
      </p>
    </div>
    """
    await send_email(to, subject, html)


async def send_password_reset_email(to: str, full_name: str, code: str) -> None:
    subject = "Reset your FAiND password"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">
      <h2 style="color: #3b82f6;">Password Reset</h2>
      <p>Hi {full_name}, use the code below to reset your FAiND password.</p>
      <p>This code expires in <strong>10 minutes</strong>.</p>
      <div style="background:#fff7ed;border:2px solid #f97316;border-radius:8px;padding:24px;text-align:center;margin:24px 0;">
        <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#c2410c;">{code}</span>
      </div>
      <p style="color:#6b7280;font-size:14px;">
        If you did not request a password reset, please secure your account immediately.
      </p>
    </div>
    """
    await send_email(to, subject, html)


async def send_authority_alert_email(to: str, subject: str, body_text: str) -> None:
    """Section 14.1 — authority-facing alerts (email; authorities are not app users)."""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: auto;">
      <h2 style="color: #3b82f6;">FAiND Drop Point Alert</h2>
      <p>{body_text}</p>
      <p style="color:#6b7280;font-size:14px;">
        Sign in to your authority dashboard to review this item.
      </p>
    </div>
    """
    await send_email(to, subject, html)
