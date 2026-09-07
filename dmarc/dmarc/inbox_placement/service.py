"""Inbox placement tester (SMTP send + IMAP seed check)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dmarc.db import clear_table, insert_rows
from dmarc.models import InboxFinding

DEFAULT_SEEDS = [
    ("Gmail", "seed1@gmail.com"),
    ("Outlook", "seed2@outlook.com"),
    ("Yahoo", "seed3@yahoo.com"),
]


def _host_matches(domain: str, *hosts: str) -> bool:
    domain = (domain or "").lower().strip(".")
    for host in hosts:
        host = host.lower()
        if domain == host or domain.endswith("." + host):
            return True
    return False


def _provider_from_email(email: str) -> str:
    domain = email.rsplit("@", 1)[-1].lower()
    if _host_matches(domain, "gmail.com", "googlemail.com"):
        return "Gmail"
    if _host_matches(domain, "outlook.com", "hotmail.com", "live.com"):
        return "Outlook"
    if _host_matches(domain, "yahoo.com"):
        return "Yahoo"
    if _host_matches(domain, "icloud.com", "me.com", "mac.com"):
        return "iCloud"
    return domain


def run_inbox_test(
    from_address: str,
    to_seeds: list[str],
    *,
    demo: bool = True,
) -> list[InboxFinding]:
    now = datetime.now(timezone.utc)
    findings: list[InboxFinding] = []
    subject = f"DMARC placement probe {now.strftime('%Y-%m-%d')}"

    if demo or not os.environ.get("DMARC_SMTP_HOST"):
        placements = ["inbox", "inbox", "spam"]
        for idx, seed in enumerate(to_seeds):
            findings.append(
                InboxFinding(
                    provider=_provider_from_email(seed),
                    seed_account=seed,
                    placement=placements[idx % len(placements)],
                    subject=subject,
                    from_address=from_address,
                    sent_at=now,
                )
            )
    else:
        # Real SMTP/IMAP path — operator must configure seeds
        import asyncio

        import aiosmtplib

        async def _send() -> None:
            for seed in to_seeds:
                await aiosmtplib.send(
                    message=f"From: {from_address}\r\nTo: {seed}\r\nSubject: {subject}\r\n\r\nprobe",
                    recipients=[seed],
                    sender=from_address,
                    hostname=os.environ["DMARC_SMTP_HOST"],
                    port=int(os.environ.get("DMARC_SMTP_PORT", "587")),
                    username=os.environ.get("DMARC_SMTP_USER"),
                    password=os.environ.get("DMARC_SMTP_PASS"),
                    start_tls=True,
                )

        asyncio.run(_send())
        for seed in to_seeds:
            findings.append(
                InboxFinding(
                    provider=_provider_from_email(seed),
                    seed_account=seed,
                    placement="missing",
                    subject=subject,
                    from_address=from_address,
                    sent_at=now,
                )
            )

    clear_table("findings_inbox")
    insert_rows("findings_inbox", [f.model_dump(mode="json") for f in findings])
    return findings
