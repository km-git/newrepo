#!/usr/bin/env python3
"""Print a sample parsedmarc.ini and IMAP mailbox checklist (no secrets)."""

from __future__ import annotations

from pathlib import Path

from dmarc.paths import PARSEDMARC_INI

CHECKLIST = """
1. Create mailbox dmarc@customer-domain (operator-owned).
2. Set DNS: _dmarc TXT  "v=DMARC1; p=none; rua=mailto:dmarc@customer-domain"
3. Export DMARC_IMAP_PASS in the environment (GitHub Actions secret, never the repo).
4. Copy dmarc/parsedmarc.ini and point host/user at that mailbox.
5. Run: dmarc ingest pull --imap-host HOST --imap-user dmarc@customer-domain
6. Or: parsedmarc --config dmarc/parsedmarc.ini
"""


def main() -> None:
    print(PARSEDMARC_INI.read_text(encoding="utf-8"))
    print(CHECKLIST)
    print("ini:", Path(PARSEDMARC_INI).resolve())


if __name__ == "__main__":
    main()
