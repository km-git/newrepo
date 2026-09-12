# cost/untagged

Untagged-resource inventory against the customer tagging policy.

CLI: `cost untagged scan --tagging-policy cost/tagging-policy.yaml`

Default required tags: Environment, CostCenter, Owner. Untagged spend is an
organisational problem; the report recommends review with the account owners.
Cloud Custodian policy is dry-run only.
