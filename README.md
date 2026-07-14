# Audit Compliance Crew

Audit Compliance Crew is a deterministic-first, agent-assisted demonstration of
an audit evidence workflow. It shows how structured assistance can support
evidence discovery and review while deterministic Python owns validation and
decision logic.

The working local MVP focuses on evidence quality, confidentiality boundaries,
and conservative human-review signalling. It is decision-support software, not
an autonomous auditor, and it is not production-ready.

## Core Governance Rule

```text
Python decides. Agents assist.
```

- Agents may discover, extract, summarize, and draft.
- Agents do not determine `CONTINUE`, `MANUAL_REVIEW`, or `REJECT` outcomes.
- Pipeline-affecting outputs must pass Pydantic validation before deterministic
  services can use them.
- Missing, contradictory, low-confidence, or unverified evidence fails closed
  to human review.
- The evidence bundle remains the source of truth in decision-producing
  workflows.

The teacher-facing two-agent demo is intentionally non-decisional: it reports
evidence-reconciliation status and a `human_review_required` signal, not a final
compliance outcome.

## Working MVP Flow

```text
Synthetic client CSV/JSON
-> deterministic normalization
-> deterministic mock offline sandbox verifier
-> deterministic Safe Hint Bridge
-> deterministic mock public research agent
-> deterministic evidence reconciliation
-> human-review signal
```

The default CLI run creates a temporary synthetic CSV, passes each stage's
schema-validated output to the next stage, and prints a concise summary. It does
not call the internet, a model provider, a virtual machine, or Azure.

## Confidentiality Boundary

The demo separates a local/internal artifact lane from a public-research lane.

- The local lane may contain confidential-classified synthetic values and
  retains artifact provenance for internal verification.
- The Safe Hint Bridge accepts only approved public or non-sensitive hint types
  that meet deterministic safety and confidence rules.
- Approved hints are copied without local provenance before public research
  receives them.
- Raw local values, filenames, source identifiers, and provenance do not cross
  the bridge.
- Review-required sandbox results produce no approved public hints.
- All current data is synthetic. The repository contains no real client data.

## Quick Start

Run these commands from the repository root.

Python 3 is required. Create a local virtual environment and install the
development dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

Run the full test suite:

```bash
.venv/bin/python -m pytest tests -s
```

Run the clean demo:

```bash
.venv/bin/python -m app.run_two_agent_demo
```

Run the review-required demo:

```bash
.venv/bin/python -m app.run_two_agent_demo --scenario review
```

Other supported scenarios target a specific evidence-quality condition:

```text
sandbox-contradiction
sandbox-missing-evidence
public-weak
public-stale
public-error
```

For example:

```bash
.venv/bin/python -m app.run_two_agent_demo --scenario public-weak
```

An optional positional path may point to a synthetic CSV or JSON artifact:

```bash
.venv/bin/python -m app.run_two_agent_demo path/to/synthetic-input.json
```

## Interpreting the Demo

| Scenario | Reconciliation status    | Human review required | Meaning                                                                                                          |
| -------- | ------------------------ | --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `clean`  | `aligned`                | `no`                  | The deterministic mocks produced mutually aligned, schema-valid evidence.                                        |
| `review` | `contradictory_evidence` | `yes`                 | The local verifier raised a contradiction, the bridge approved no hints, and the issue was preserved for review. |

The CLI also reports the status and item count for normalization, sandbox
verification, the Safe Hint Bridge, and public research. In the review scenario,
`Safe Hint Bridge: no_approved_hints` means the filtering stage ran but released
nothing to the public lane.

These labels describe evidence processing and reconciliation only:

- `aligned` is not a `CONTINUE` decision.
- `human_review_required: yes` is a review signal, not an independently assigned
  `MANUAL_REVIEW` outcome.
- Reconciliation never produces `REJECT`.

Final compliance outcomes, where used elsewhere in the project, remain owned by
separate deterministic services and follow:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for a short presentation script,
stage explanations, and troubleshooting.

## Current Limitations

- Public research is deterministic and mocked; it performs no real internet
  search.
- The sandbox verifier is deterministic and mocked; it provides no real VM or
  operating-system isolation.
- There is no LLM or agent-framework runtime.
- There is no OpenAI API, CrewAI runtime, or other model-provider integration.
- There is no Azure deployment, Azure SDK, or cloud resource.
- Artifact normalization supports CSV and JSON only for this MVP.
- There is no OCR, PDF parsing, or Excel parsing.
- The project uses synthetic data only.
- The MVP is not a production security design and does not replace auditor
  judgment, professional standards, or human review.

## Repository Structure

- `schemas/`: strict Pydantic contracts for inputs, evidence, reconciliation,
  and deterministic decisions.
- `services/`: deterministic business logic, including normalization, hint
  filtering, reconciliation, screening, materiality, and planning services.
- `ai/`: schema-constrained assistant wrappers and deterministic mock agents;
  no live model runtime.
- `orchestration/`: local workflow composition, including the two-agent demo.
- `app/`: command-line entry points.
- `storage/`: local evidence, memo, and source-registry persistence helpers.
- `manual_controls/`: public-safe deterministic demo controls.
- `data/`: tracked synthetic datasets for local demonstrations.
- `tests/` and `evals/`: deterministic tests, fixtures, and small golden assets.
- `docs/`: architecture, policy, demo, evaluation, and future migration notes.
- `azure_functions/`: documentation and local contract preparation only; no
  Azure implementation.
- `output/` and `memos/`: ignored destinations for local generated artifacts;
  only empty directory placeholders are tracked.

## Additional Documentation

- [Demo guide](docs/DEMO_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decision policy](docs/DECISION_POLICY.md)
- [Agent operating rules](docs/AGENT_OPERATING_RULES.md)
- [Azure migration plan](docs/AZURE_MIGRATION_PLAN.md)
- [Public project roadmap](ROADMAP.md)

## Safety and Scope

This repository is a public portfolio and academic-review prototype. It contains
synthetic examples, no production credentials, and no proprietary audit-manual
content. It is not professional audit, assurance, legal, compliance, or
regulatory advice.

## License

This project is proprietary and source-available for portfolio and review
purposes only. See [LICENSE](LICENSE) for the full terms.
