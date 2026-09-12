# cost/multi_account

Optional multi-account runner. Uses `c7n-org` (Apache-2.0) as a CLI to apply
the same dry-run policies across AWS accounts / Azure subscriptions / GCP
projects. `accounts.yaml` is generated from Organizations when credentials
exist. The report aggregates the per-account folder tree.
