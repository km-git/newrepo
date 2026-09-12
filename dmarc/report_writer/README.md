Writes the operator-facing Markdown and JSON review titled
"Email Deliverability & Brand-Protection Review". Never "email security".
Jinja2 templates plus `disclaimers/disclaimer_au.txt` on every file. Banned
words (compliance, attestation, certified, secure, guaranteed) are stripped.
CLI: `dmarc report generate --domain example.com.au --since 30d`.
