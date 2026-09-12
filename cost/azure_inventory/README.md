# cost/azure_inventory

Read-only Azure subscription inventory via Resource Manager + Cost Management.

CLI: `cost inventory azure --subscription-id ID --tenant-id ID --client-id ID`

Steampipe Azure plugin as CLI subprocess; `azure-mgmt-resource` for tags when
installed. Sandbox fixtures when credentials are absent.
