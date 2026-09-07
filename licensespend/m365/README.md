# M365 seats

Parses `examples/m365/subscribedSkus.json` and `users.json` (or Graph-shaped `value` arrays). Live path: `msgraph-sdk` + `azure-identity`, scopes Organization.Read.All, User.Read.All, Directory.Read.All, AuditLog.Read.All. Read-only. Graph last-signin lags — treat idle >90 days as unused, not never.
