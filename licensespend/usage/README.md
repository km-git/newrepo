# Usage

Joins M365, Slack, and GitHub seats in DuckDB view `v_unused_seats` (`idle_days`, `sku`, `monthly_cost`). Pricebook is operator-edited AUD list prices — never scraped. Unknown SKUs abstain from reclaim $. Null last-active is unused-because-lag, not "never".
