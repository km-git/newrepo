# cost/rightsizing

Heuristic rightsizing observations: over-provisioned instances, idle
resources, untagged spend. Always review with the engineering team before
applying any change — this tool never mutates customer systems.

CLI: `cost rightsizing scan --provider aws`

AWS Compute Optimizer / Azure Advisor / GCP Recommender when credentials
exist; Cloud Custodian YAML (dry-run) as the policy source of truth.
