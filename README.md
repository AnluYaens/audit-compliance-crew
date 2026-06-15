# Audit Compliance Crew - Azure-Ready Local Compliance Engine

This project is a local-first compliance and audit-planning prototype designed to evolve toward an Azure Functions / Durable Functions architecture.

The system demonstrates an AI governance pattern where Python owns deterministic compliance decisions, while LLMs and agents are used only for language synthesis, reporting, and memo drafting.

---

## Current Architecture

The current architecture is deterministic-first:

```text
Company input
    ↓
Deterministic ingestion service
    ↓
Independence and sanctions screening services
    ↓
Source registry and deterministic source scoring
    ↓
Deterministic risk scoring service
    ↓
Acceptance pipeline service
    ↓
Evidence bundle
    ↓
Final decision: CONTINUE / MANUAL_REVIEW / REJECT
```

The LLM is not the decision-maker. The LLM may help write a memo, but it does not decide whether the client is accepted, rejected, or sent to manual review.

---

## Core Principle

AI supports the process, but Python controls the compliance outcome.

Python services own:

- data validation
- deterministic screening
- risk scoring
- fail-closed routing
- final acceptance decision
- evidence bundle creation

LLMs and agents are allowed only for:

- memo drafting
- report formatting
- narrative synthesis
- explanation of validated evidence

---

## Key Decision Rules

| Scenario | Final Decision |
|---|---|
| Independence conflict | REJECT |
| Sanctions hit | REJECT |
| Unknown or missing client data | MANUAL_REVIEW |
| Missing, stale, contradictory, unverified, or weak required source support | MANUAL_REVIEW |
| High engagement risk | MANUAL_REVIEW |
| Clean screening + low/moderate risk | CONTINUE |

Source scoring is a fail-closed support check. It may route weak evidence to
`MANUAL_REVIEW`, but it does not produce `REJECT`; hard rejection remains limited
to deterministic rejection criteria such as independence conflicts and sanctions
hits.

---

## Current Test Scenarios

| Company | Expected Result | Reason |
|---|---|---|
| Quantum Cybernetics | REJECT | Independence conflict |
| Vanguard Mining Corp | REJECT | Sanctions hit + high risk |
| Apex Energy Group | MANUAL_REVIEW | High engagement risk |
| GreenLeaf Organics | CONTINUE | Clean screening |
| Unknown Company ABC | MANUAL_REVIEW | Missing client data / fail-closed |

---

## Important Modules

### `schemas/contracts.py`

Strict Pydantic data contracts for ingestion, screening, and risk outputs.

These contracts prevent loose JSON from becoming the source of truth.

### `schemas/source_registry.py`

Structured source provenance contracts.

`SourceRecord` captures source identity, type, publisher, retrieval date,
freshness, confidence, relevance, notes, and contradiction flags. `SourceRegistry`
groups those records for a run before deterministic scoring.

### `services/`

Deterministic business logic layer.

This folder contains the logic that will later map cleanly to Azure Function activity steps.

### `services/source_scoring_service.py`

Deterministic source scoring for authority, relevance, freshness, completeness,
confidence, and contradictions.

Agents may discover, extract, or summarize source metadata, but validated Python
services score it and decide whether the supported workflow can continue.

### `services/acceptance_pipeline_service.py`

Main deterministic acceptance pipeline.

This service directly calls ingestion, screening, sanctions, and risk scoring logic without relying on agent tool-calling.

### `manual_controls/`

Generic demo control matrix foundation.

This layer contains synthetic, public-safe control metadata that can be used to
exercise deterministic planning logic without publishing proprietary manual
content.

### `orchestration/`

Local orchestration layer.

This folder prepares the project for a future Durable Functions style workflow.

### `ai/`

Safe AI-assistance layer.

This folder contains agent contracts, prompts, deterministic mock agents, and guardrail wrappers. These components may assist with research, explanation, or memo wording, but they do not own final compliance decisions.

---

## Local Development

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Run tests:

```bash
python -m pytest tests
```

Run the Phase 2 local runner:

```bash
python -m app.local_runner
```

Run the deterministic acceptance pipeline manually:

```bash
python - <<'PY'
from services.acceptance_pipeline_service import run_acceptance_pipeline

for company in [
    "Quantum Cybernetics",
    "Vanguard Mining Corp",
    "Apex Energy Group",
    "GreenLeaf Organics",
    "Unknown Company ABC",
]:
    bundle = run_acceptance_pipeline(company)
    print(company, "=>", bundle.final_decision)
    print("Reasons:", bundle.manual_review_reasons)
    print()
PY
```

Expected behavior:

```text
Quantum Cybernetics => FinalDecision.REJECT
Vanguard Mining Corp => FinalDecision.REJECT
Apex Energy Group => FinalDecision.MANUAL_REVIEW
GreenLeaf Organics => FinalDecision.CONTINUE
Unknown Company ABC => FinalDecision.MANUAL_REVIEW
```

---

## Azure Migration Direction

The project is still local-first, but the folder structure is designed to migrate later toward Azure.

Future mapping:

| Local Module | Future Azure Equivalent |
|---|---|
| `services/ingestion_service.py` | Azure Function activity |
| `services/screening_service.py` | Azure Function activity |
| `services/risk_scoring_service.py` | Azure Function activity |
| `services/acceptance_pipeline_service.py` | Durable Functions orchestrator / activity chain |
| `schemas/contracts.py` | Shared function contracts |
| `storage/` | Evidence ledger storage |
| `ai/` | Azure AI Foundry reporting layer |

---

## Why This Architecture Matters

The project avoids letting an LLM make binary compliance decisions.

Instead, the system uses:

- strict Pydantic schemas
- deterministic Python services
- fail-closed routing
- evidence bundles
- manual review escalation
- optional AI-assisted reporting

This makes the project a stronger example of AI governance, auditability, and professional compliance automation.

---

## Current Milestone

Completed:

- Phase 2.1: Azure-ready local architecture
- Phase 2.2A: Strict contracts moved into `schemas/`
- Phase 2.2B: Deterministic logic extracted into `services/`
- Phase 2.2C: Deterministic acceptance pipeline implemented
- Phase 4.1-4.3: Source registry, source scoring, evidence bundle source support, and memo reporting
- High-risk engagements now route to manual review
- Tests passing

Current validation:

```bash
python -m pytest tests
```

Expected:

```text
9 passed
```

---

## Next Planned Steps

Next phases:

1. Expand the manual control matrix.
2. Add planning, materiality, and risk assessment modules.
3. Generate planning memos from validated evidence bundles.
4. Add persistent evidence storage.
5. Prepare Azure Function boundaries.
6. Later migrate orchestration to Azure Durable Functions.
