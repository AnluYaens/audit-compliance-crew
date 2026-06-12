# Test Fixtures

These fixtures are small, deterministic examples for schema validation, guardrail tests, and future evaluation datasets.

They use synthetic company names and synthetic source metadata only. Do not add real client data, real model responses, run-specific IDs, or unstable timestamps.

## Directories

- `evidence_bundles/` contains serialized `AuditPlanningEvidenceBundle` examples for clean, reject, and manual-review routing.
- `agent_outputs/` contains serialized `ResearchAgentOutput` examples for clean, missing-evidence, contradiction, and low-confidence cases.
- `financial_statements/` contains serialized `FinancialStatementSet` examples for clean and manual-review extraction scenarios.

## Fixture Rules

- Keep files readable and compact.
- Prefer fixed ISO timestamps such as `2025-01-15T00:00:00Z`.
- Golden outputs and fixture metadata should avoid run timestamps unless the value is intentionally normalized.
- Real LLM calls belong in later eval workflows, not unit tests.
