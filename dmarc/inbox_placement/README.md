Heuristic inbox-placement probe. Sends via SMTP (`aiosmtplib` / stdlib smtplib)
to the operator's own seed mailboxes (Gmail, Outlook, Yahoo samples in
`templates/seed_accounts.yaml`) and records inbox / spam / promotions / missing.
Honest gap: placement changes daily; run weekly. Default is dry-run so CI never
sends mail. CLI: `dmarc inbox test --from sender@example.com.au --to ...`.
