DNS record checker for one customer domain. Looks up A, AAAA, MX, TXT (SPF),
DKIM (`selector._domainkey`), DMARC (`_dmarc`), MTA-STS, TLS-RPT, and BIMI.
Primary tool: dnspython, with Cloudflare DNS-over-HTTPS as a free fallback.
CLI: `dmarc dns check --domain example.com.au`. Output lands in `findings_dns`.
Read-only; no record mutation.
