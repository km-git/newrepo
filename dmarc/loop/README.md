Watcher payload for the deliverability toolkit. Imports
`forum-watcher/scripts/watch.py` and `state/seen.json`, adds DMARC sources,
and classifies with the DMARC context block. Monday 09:00 AEST cron lives in
`.github/workflows/dmarc-watch.yml`. Dedupe is SHA-256 of the canonical URL.
Do not duplicate the watcher.
