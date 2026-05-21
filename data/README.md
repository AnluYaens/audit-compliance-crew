# Local Compliance Data

This directory is reserved for local CRM, partner holdings, and sanctions datasets.

The real `*.json` and `*.csv` files are intentionally ignored by Git because they may
contain client, partner, sanctions, financial, or other compliance-sensitive data.

Expected local filenames:

- `client_crm.json`
- `internal_holdings.csv`
- `sanctions.json`

Use sanitized `*.example.json` or `*.example.csv` fixtures if sample data needs to be
shared in the repository.
