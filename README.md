# Audit Compliance Crew

Audit Compliance Crew is a deterministic-first, AI-assisted audit planning and
compliance prototype. It demonstrates how Python services, schemas, fixtures,
and tests can own compliance routing while LLM-style agents support explanation,
research contracts, and memo wording.

## Core Principle

**Python decides. Agents assist.**

The final compliance outcome is produced by deterministic Python logic, not by
an LLM. Agents can help draft narratives, summarize structured findings, or
prepare research inputs, but they do not decide whether an engagement should
`CONTINUE`, move to `MANUAL_REVIEW`, or be `REJECT`.

## Key Features

- Deterministic compliance routing for synthetic audit planning scenarios.
- Explicit final outcomes: `CONTINUE`, `MANUAL_REVIEW`, and `REJECT`.
- Schema-validated inputs and outputs for pipeline-changing data.
- Fail-closed handling that routes uncertain or incomplete cases to manual
  review.
- Synthetic CRM, holdings, control, and evidence fixtures for repeatable demos.
- Evidence bundle outputs that preserve decision reasons for auditability.
- Focused service boundaries for decisions, storage, orchestration, AI support,
  and manual controls.
- Test coverage for deterministic rules, schema contracts, orchestration paths,
  and safety-oriented edge cases.

## Architecture Overview

The project is organized around a deterministic core with optional AI-assist
surfaces around it.

```text
Company input
    |
Deterministic ingestion service
    |
Independence and sanctions screening services
    |
Source registry and deterministic source scoring
    |
Deterministic risk scoring service
    |
Acceptance pipeline service
    |
Evidence bundle
    |
Final decision: CONTINUE / MANUAL_REVIEW / REJECT
```

- `schemas/` defines structured contracts used by the pipeline.
- `services/` contains deterministic compliance and decision-support logic.
- `storage/` contains local persistence helpers for demo data.
- `orchestration/` coordinates the pipeline without handing final decisions to
  agents.
- `ai/` contains AI-facing helper code for explanatory or drafting workflows.
- `manual_controls/` contains manual-review-oriented controls and examples.
- `data/` and `tests/fixtures/` contain synthetic demo data only.
- `tests/` validates deterministic behavior and contract boundaries.

## Deterministic Decision Rules

The compliance pipeline is designed so that deterministic rules own final
routing:

| Scenario | Final Decision |
| --- | --- |
| Independence conflict | `REJECT` |
| Sanctions hit | `REJECT` |
| Unknown or missing client data | `MANUAL_REVIEW` |
| Missing, stale, contradictory, unverified, or weak required source support | `MANUAL_REVIEW` |
| High engagement risk | `MANUAL_REVIEW` |
| Clean screening with low or moderate risk | `CONTINUE` |

Additional safeguards:

- `CONTINUE` is allowed only when required checks pass and no blocking issue is
  present.
- `MANUAL_REVIEW` is used when a case is uncertain, incomplete, ambiguous, or
  requires human judgment.
- `REJECT` is used when deterministic blocking criteria are met.
- Missing, malformed, or schema-invalid pipeline-changing data must not be
  silently accepted.
- AI-generated content can explain or draft, but cannot override deterministic
  decision logic.

## AI Governance

Audit Compliance Crew treats LLMs and agents as assistants, not authorities.

- LLMs and agents do not own final compliance decisions.
- Any AI output that could affect the pipeline must validate through schemas
  before it is used.
- Uncertainty fails closed by routing cases to `MANUAL_REVIEW`.
- Human review remains the correct path for judgment-heavy, unclear, or
  exception-based scenarios.

## Tech Stack

- Python 3
- Pytest
- Pydantic-style schema validation
- Local JSON and CSV demo fixtures
- Deterministic service modules
- Standard-library compile checks
- Optional AI-assist integration points

## Install And Run Locally

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install project dependencies:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Run the local runner:

```bash
.venv/bin/python -m app.local_runner
```

Run the deterministic acceptance pipeline manually:

```bash
.venv/bin/python - <<'PY'
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

Expected demo behavior:

```text
Quantum Cybernetics => FinalDecision.REJECT
Vanguard Mining Corp => FinalDecision.REJECT
Apex Energy Group => FinalDecision.MANUAL_REVIEW
GreenLeaf Organics => FinalDecision.CONTINUE
Unknown Company ABC => FinalDecision.MANUAL_REVIEW
```

## Run Tests

Run the test suite:

```bash
.venv/bin/python -m pytest tests
```

Run compile checks:

```bash
.venv/bin/python -m compileall schemas services storage orchestration ai tests
```

Current validation:

```text
87 passed
```

## Azure And Deployment Notes

This repository does not include production credentials, live cloud resources,
deployment files, or a real Azure deployment. Any Azure-related direction should
be treated as future-oriented architecture planning only.

Future-oriented mapping:

| Local Module | Possible Future Azure Equivalent |
| --- | --- |
| `services/ingestion_service.py` | Azure Function activity |
| `services/screening_service.py` | Azure Function activity |
| `services/risk_scoring_service.py` | Azure Function activity |
| `services/acceptance_pipeline_service.py` | Durable Functions orchestrator or activity chain |
| `schemas/contracts.py` | Shared function contracts |
| `storage/` | Evidence ledger storage |
| `ai/` | AI-assisted reporting layer |

## Public Safety Disclaimer

This project is a public portfolio prototype built with synthetic demo data.

- Synthetic demo data only.
- No real client data.
- No production credentials.
- No proprietary audit manual content.
- Not an official audit firm product.
- Not professional, legal, audit, assurance, compliance, or regulatory advice.

## License

This project is proprietary and source-available for portfolio/review purposes only.

No permission is granted to use, copy, modify, distribute, sell, host, deploy, train on, or create derivative works from this software without prior written permission from the copyright holder.

See [LICENSE](LICENSE) for details.
