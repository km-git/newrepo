# SaaS License & Spend

MSP seat-waste report for Microsoft 365, Slack, GitHub, and a YAML pricebook of other apps. Fixture-first, $0/month, metadata only.

```bash
python -m licensespend audit inventory
python -m licensespend usage unused --idle-days 90 --fixture examples/
python -m licensespend report build --client fixture --out reports/
```

Never revokes seats unless `--apply`, `LICENSESPEND_APPLY=1`, and the user id is in `allow-reclaim.txt`. Hash emails by default. Live SDKs are extras (`[m365]`, `[slack]`, `[github]`).
