# Demo Compliance Data

This directory contains synthetic demo datasets used by the local deterministic
audit planning runner and tests.

The tracked files in this folder are safe sample data only:

- `client_crm.json`
- `internal_holdings.csv`
- `sanctions.json`

They do not contain real client data, real partner holdings, real sanctions data,
production credentials, or confidential information.

Do not replace these tracked demo files with real/private compliance datasets.

If private local data is ever needed, store it outside the repository or use
ignored local-only filenames documented in `.gitignore`.
