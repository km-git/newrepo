# cost/loop

Watcher payload. Imports `forum-watcher/scripts/watch.py`, adds cost-specific
sources, and uses the same Monday 09:00 AEST cron. Does not duplicate the
watcher. Monthly rollup writes `monthly/YYYY-MM.md` and `monthly/cost-trend.md`.
