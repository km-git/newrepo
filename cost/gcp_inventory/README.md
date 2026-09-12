# cost/gcp_inventory

Read-only GCP project inventory via Cloud Asset Inventory + Cloud Billing.

CLI: `cost inventory gcp --project-id ID --service-account PATH`

Steampipe GCP plugin as CLI subprocess; `google-cloud-resource-manager` for
project metadata when installed. Sandbox fixtures when credentials are absent.
