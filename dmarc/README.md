# Email Deliverability & Brand-Protection Review

Read-only DNS / SPF / DKIM / DMARC (RUA+RUF) / inbox-placement toolkit.

```bash
python3 -m dmarc --help
make dmarc-all                 # example.com.au + fixtures + static UI
python3 ew_tool.py --dmarc-ui  # http://127.0.0.1:8765/dmarc
python3 ew_tool.py --dmarc-ui --static  # reports/dmarc_explorer.html
```

Nine modules under `dmarc/`. Not an email-security product. Reports append
`disclaimers/disclaimer_au.txt`. IMAP password: `DMARC_IMAP_PASS` only.
