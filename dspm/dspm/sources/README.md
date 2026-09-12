# Data Sources — unified multi-protocol ingestion

Read backup archives, NFS/SMB shares, S3, M365, and SaaS unstructured data.

## URI schemes

| Scheme | Example | Notes |
|--------|---------|-------|
| `file://` | `file://examples/archives` | Local paths |
| `nfs://` | `nfs:///mnt/nfs/backup` | NFS mount point (same as file) |
| `backup://` | `backup://examples/archives` | tar, zip, .bak archives |
| `s3://` | `s3://bucket/prefix/` | AWS/MinIO (`DSPM_S3_ENDPOINT`) |
| `smb://` | `smb://server/share/path` | CIFS (`SMB_USER`, `SMB_PASSWORD`) |
| `m365://` | `m365://sharepoint`, `m365://exchange` | Graph API (`AZURE_*` env) |
| `saas://` | `saas://gdrive`, `saas://dropbox` | SaaS APIs or fixtures |

## CLI

```bash
dspm sources discover s3://my-bucket/backups/
dspm sources preview backup://archives/payroll.zip payroll.csv
dspm sources scan m365://exchange
dspm discovery any smb://fileserver/hr
```

## Web UI

Data Sources panel → pick scheme, enter path → Discover + Classify
