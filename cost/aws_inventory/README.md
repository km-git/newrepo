# cost/aws_inventory

Read-only AWS account inventory. Lists EC2, RDS, S3, Lambda, EBS, ELB, NAT,
and EIP into `findings_resources`.

CLI: `cost inventory aws --profile NAME --regions ap-southeast-2,us-east-1`

Uses Steampipe (`steampipe query ...`) as a CLI subprocess, with boto3 for
cost-specific fields Steampipe does not expose. Falls back to sandbox fixtures
when credentials or binaries are absent.
