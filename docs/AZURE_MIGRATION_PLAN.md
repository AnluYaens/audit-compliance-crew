# Azure Migration Plan

Audit Compliance Crew is local-first today and Azure-ready by design. The migration should preserve deterministic decision ownership.

Do not add Azure SDKs yet. Do not add credentials. Do not deploy anything.

## Migration Principle

```text
Local deterministic service
-> stable schema boundary
-> Azure Function activity
-> Durable Functions orchestration
```

The local service should remain testable without cloud infrastructure.

## Future Mapping

| Local module | Future Azure role |
|---|---|
| `services/ingestion_service.py` | Azure Function activity |
| `services/source_scoring_service.py` | Azure Function activity |
| `services/statement_extraction_service.py` | Azure Function activity |
| `services/materiality_service.py` | Azure Function activity |
| `services/risk_assessment_service.py` | Azure Function activity |
| `services/audit_response_service.py` | Azure Function activity |
| `services/audit_planning_pipeline_service.py` | Durable Functions orchestrator |
| `storage/` | Evidence ledger storage |
| `ai/` | Azure AI Foundry agent layer |

Existing acceptance services should also remain activity-compatible:

- `services/screening_service.py`
- `services/risk_scoring_service.py`
- `services/acceptance_pipeline_service.py`

## Target Azure Flow

```text
HTTP or queue trigger
-> Durable Functions orchestrator
-> ingestion activity
-> source scoring activity
-> statement extraction activity
-> materiality activity
-> risk assessment activity
-> audit response activity
-> evidence ledger write
-> memo generation activity
-> auditor review workflow
```

## Storage Direction

`storage/` should eventually map to an evidence ledger with:

- immutable evidence bundle records
- memo records
- source registry records
- audit trail events
- human override records
- run metadata

Until the migration begins, local storage should stay simple and testable.

## AI Foundry Direction

The future `ai/` layer may map to Azure AI Foundry agents for:

- research scouting
- evidence extraction
- memo enhancement
- auditor assistant workflows
- quality review

These agents must still return structured outputs that validate through Pydantic schemas before deterministic services use them.

## Function Boundary Requirements

Before creating real Azure Functions, each candidate activity should have:

- clear request schema
- clear response schema
- deterministic service implementation
- unit tests
- integration tests
- failure behavior
- no dependency on agent free-form output

## What Not To Do Yet

Do not:

- install Azure SDKs
- add credentials
- add deployment templates
- create cloud resources
- add real API calls
- move deterministic logic into function wrappers
- use Azure as a reason to weaken local tests

## Prototype Sequence

1. Document function boundaries.
2. Confirm schema contracts for each service.
3. Add local adapter tests that simulate activity calls.
4. Create a minimal orchestrator plan.
5. Add Azure SDKs only when explicitly approved.
6. Prototype one end-to-end workflow with non-production data.
7. Add observability, audit trail, and security controls.

The first Azure prototype should be boring, narrow, and reversible.
