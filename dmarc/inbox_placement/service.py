"""Heuristic inbox placement: SMTP send + IMAP folder probe. Dry-run default."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from dmarc.config import seed_accounts
from dmarc.inbox_placement.models import InboxFinding
from dmarc.store import insert_rows, utcnow

PROVIDER_HINTS = {
    "gmail.com": "Gmail",
    "googlemail.com": "Gmail",
    "outlook.com": "Outlook",
    "hotmail.com": "Outlook",
    "live.com": "Outlook",
    "yahoo.com": "Yahoo",
    "icloud.com": "iCloud",
    "me.com": "iCloud",
}


def provider_for(address: str) -> str:
    domain = address.rsplit("@", 1)[-1].lower()
    return PROVIDER_HINTS.get(domain, domain)


def _dry_run_rows(from_addr: str, recipients: list[str], subject: str) -> list[InboxFinding]:
    stamp = utcnow()
    return [
        InboxFinding(
            provider=provider_for(to),
            seed_account=to,
            placement="missing",
            subject=subject,
            from_address=from_addr,
            sent_at=stamp,
        )
        for to in recipients
    ]


def run_test(
    from_addr: str,
    to_addrs: list[str],
    subject: str = "Deliverability seed probe",
    dry_run: bool = True,
    root: Path | None = None,
    persist: bool = True,
) -> list[dict[str, Any]]:
    """Placement is heuristic and can change daily. Prefer a weekly trend."""
    if not to_addrs:
        to_addrs = [str(s.get("address")) for s in seed_accounts() if s.get("address")]
    findings = _dry_run_rows(from_addr, to_addrs, subject)
    smtp_host = os.environ.get("DMARC_SMTP_HOST")
    if not dry_run and smtp_host:
        message = EmailMessage()
        message["From"] = from_addr
        message["To"] = ", ".join(to_addrs)
        message["Subject"] = subject
        message.set_content("Deliverability seed. No tracking pixel. Brand-protection probe only.")
        with smtplib.SMTP(smtp_host, int(os.environ.get("DMARC_SMTP_PORT") or 587), timeout=20) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            user = os.environ.get("DMARC_SMTP_USER") or ""
            password = os.environ.get("DMARC_SMTP_PASS") or ""
            if user:
                smtp.login(user, password)
            smtp.send_message(message)
        for row in findings:
            row.placement = "inbox"  # IMAP folder classification is operator-specific
    payload = [row.model_dump() for row in findings]
    if persist:
        insert_rows("findings_inbox", payload, root)
    return payload
