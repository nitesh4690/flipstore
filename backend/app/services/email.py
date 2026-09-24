"""Transactional email service with pluggable backends.

Backends (settings.EMAIL_BACKEND; "" auto-selects):
    memory  — appends to `outbox` (used in tests so they can assert sends)
    file    — appends a readable transcript to settings.EMAIL_FILE_PATH
    console — prints a one-liner to stdout
    smtp    — real SMTP relay (requires SMTP_* settings)

`send_email` NEVER raises: delivery failures are logged and swallowed so a
broken mailer can never break checkout, registration or an admin action.
"""

import logging
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("flipstore.email")

# Captured messages when the memory backend is active (tests).
outbox: list[dict] = []


# ---------------------------------------------------------------------------
# Backend plumbing
# ---------------------------------------------------------------------------
def _backend() -> str:
    configured = settings.EMAIL_BACKEND.strip().lower()
    if configured:
        return configured
    return "memory" if settings.ENVIRONMENT == "test" else "file"


def get_outbox() -> list[dict]:
    """Messages captured by the memory backend (test helper)."""
    return outbox


def clear_outbox() -> None:
    outbox.clear()


def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Dispatch one email. Returns True on (apparent) success, False otherwise."""
    message = {
        "from": settings.EMAIL_FROM,
        "to": to,
        "subject": subject,
        "html": html,
        "text": text if text is not None else _html_to_text(html),
    }
    backend = _backend()
    try:
        if backend == "memory":
            outbox.append(message)
        elif backend == "console":
            print(f"[email] -> {to} | {subject}")
        elif backend == "smtp":
            _send_smtp(message)
        else:  # file (development default)
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with open(settings.EMAIL_FILE_PATH, "a", encoding="utf-8") as handle:
                handle.write(f"{stamp} | {message['from']} -> {to} | {subject}\n")
                handle.write((message["text"] or subject) + "\n")
                handle.write("-" * 60 + "\n")
        return True
    except Exception:  # noqa: BLE001 — email must never break the triggering request
        logger.exception("Email delivery failed (%s -> %s)", backend, to)
        return False


def _send_smtp(message: dict) -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not configured")
    email = EmailMessage()
    email["From"] = message["from"]
    email["To"] = message["to"]
    email["Subject"] = message["subject"]
    email.set_content(message["text"] or message["subject"])
    email.add_alternative(message["html"], subtype="html")

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as client:
        if settings.SMTP_USE_TLS:
            client.starttls()
        if settings.SMTP_USER:
            client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        client.send_message(email)


def _html_to_text(html: str) -> str:
    """Tiny HTML → text fallback for the plain-text MIME part."""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"</(p|div|tr|h[1-6])>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"[ \t]+", " ", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
def _shell(title: str, body: str) -> str:
    """Minimal inline-styled HTML shell (works in every mail client)."""
    return f"""<!DOCTYPE html>
<html>
  <body style="margin:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:24px 12px;">
      <div style="background:#ffffff;border-radius:16px;padding:32px;border:1px solid #e2e8f0;">
        <div style="font-size:20px;font-weight:800;color:#0f172a;margin-bottom:4px;">
          Flip<span style="color:#4f46e5;">Store</span>
        </div>
        <h1 style="font-size:18px;color:#0f172a;margin:16px 0 12px;">{title}</h1>
        {body}
        <p style="color:#94a3b8;font-size:12px;margin-top:28px;border-top:1px solid #e2e8f0;padding-top:16px;">
          &copy; FlipStore &middot; This is a transactional message about your account or order.
        </p>
      </div>
    </div>
  </body>
</html>"""


def _rows(pairs: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<tr><td style="padding:6px 0;color:#64748b;font-size:13px;">{label}</td>'
        f'<td style="padding:6px 0;text-align:right;color:#0f172a;font-size:13px;font-weight:700;">{value}</td></tr>'
        for label, value in pairs
    )
    return f'<table style="width:100%;border-collapse:collapse;background:#f8fafc;border-radius:12px;padding:8px 16px;">{cells}</table>'


def _button(href: str, text: str) -> str:
    return (
        f'<p style="margin:20px 0 4px;"><a href="{href}" '
        'style="display:inline-block;background:#4f46e5;color:#ffffff;text-decoration:none;'
        f'padding:12px 22px;border-radius:12px;font-size:14px;font-weight:700;">{text}</a></p>'
    )


def send_welcome(to: str, first_name: str) -> bool:
    """Welcome email sent right after registration."""
    subject = f"Welcome to FlipStore, {first_name}!"
    html = _shell(
        f"Welcome, {first_name}!",
        f"""
        <p style="color:#475569;font-size:14px;line-height:1.6;">
          Your FlipStore account is ready. Track orders, save addresses and
          keep a wishlist — all in one place.
        </p>
        {_button(f"{settings.FRONTEND_URL}/products", "Start shopping")}
        <p style="color:#475569;font-size:14px;line-height:1.6;">
          Questions? Just reply to this email.
        </p>
        """,
    )
    text = (
        f"Welcome to FlipStore, {first_name}!\n\n"
        "Your account is ready. Start shopping: "
        f"{settings.FRONTEND_URL}/products"
    )
    return send_email(to, subject, html, text)


def send_order_confirmation(
    *,
    to: str,
    first_name: str,
    order_number: str,
    total: float,
    item_count: int,
    payment_status: str,
) -> bool:
    """Order confirmation sent immediately after checkout."""
    subject = f"Order {order_number} confirmed"
    html = _shell(
        "Thanks — your order is confirmed!",
        f"""
        <p style="color:#475569;font-size:14px;line-height:1.6;">
          Hi {first_name}, we've received your order and it's being prepared.
        </p>
        {_rows([
            ("Order number", order_number),
            ("Items", str(item_count)),
            ("Payment status", payment_status.title()),
            ("Total", f"${total:,.2f}"),
        ])}
        {_button(f"{settings.FRONTEND_URL}/account/orders", "View your order")}
        """,
    )
    text = (
        f"Hi {first_name},\n\n"
        f"Your order {order_number} is confirmed.\n"
        f"Items: {item_count} | Payment: {payment_status} | Total: ${total:,.2f}\n\n"
        f"View it: {settings.FRONTEND_URL}/account/orders"
    )
    return send_email(to, subject, html, text)


def send_order_status_update(
    *,
    to: str,
    first_name: str,
    order_number: str,
    changes: dict[str, tuple[str, str]],
) -> bool:
    """Status-change notice sent when an admin updates an order."""
    subject = f"Update for order {order_number}"
    rows_html = _rows([(label, f"{old} → {new}") for label, (old, new) in changes.items()])
    html = _shell(
        f"Order {order_number} has been updated",
        f"""
        <p style="color:#475569;font-size:14px;line-height:1.6;">
          Hi {first_name}, here's what changed with your order:
        </p>
        {rows_html}
        {_button(f"{settings.FRONTEND_URL}/account/orders", "View your order")}
        """,
    )
    text = (
        f"Hi {first_name},\n\n"
        f"Order {order_number} has been updated:\n"
        + "\n".join(f"  - {label}: {old} -> {new}" for label, (old, new) in changes.items())
        + f"\n\nView it: {settings.FRONTEND_URL}/account/orders"
    )
    return send_email(to, subject, html, text)
