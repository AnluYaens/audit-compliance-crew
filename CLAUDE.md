# Audit Compliance Crew

Audit Compliance Crew is a deterministic-first, agent-assisted audit planning and compliance engine.

The project direction is simple:

```text
Python decides. Agents assist.
```

LLMs and agents may discover, extract, summarize, review, and draft. They must not decide final compliance outcomes.

## Current Architecture

The local architecture is designed to stay Azure-ready while remaining testable without cloud services.

```text
Company input
-> deterministic ingestion
-> independence, sanctions, and risk screening
-> materiality calculation
-> structured risk assessment
-> audit response planning
-> evidence bundle
-> deterministic final decision
-> planning memo and auditor review
```

Final decisions are always one of:

- `CONTINUE`
- `MANUAL_REVIEW`
- `REJECT`

Decision priority is:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

## Folder Responsibilities

- `schemas/`: strict Pydantic contracts for pipeline inputs, outputs, evidence, and decisions.
- `services/`: deterministic business logic and pipeline steps.
- `tools/`: thin wrappers around deterministic services for agent/tool interfaces.
- `ai/`: safe future agent wrappers, prompts, and structured output contracts.
- `storage/`: persistence for evidence bundles and planning memos.
- `manual_controls/`: generic demo control rules and public-safe control metadata.
- `orchestration/`: workflow coordination that can later map to Durable Functions.
- `app/`: local runners and command entry points.
- `tests/`: pytest unit and integration coverage.
- `docs/`: project strategy, architecture, agent rules, decision policy, and migration plans.
- `azure_functions/`: future Azure boundary prototypes only.

## Non-Negotiable Rules

1. Do not move business logic into `tools/`.
2. Do not let LLMs or agents decide `CONTINUE`, `MANUAL_REVIEW`, or `REJECT`.
3. Do not remove fail-closed behavior.
4. Every new feature must include schemas, services, and tests.
5. Run `python -m pytest tests` before finishing.
6. Use small commits with clear messages.
7. Preserve Azure-ready service boundaries.
8. All agent outputs that affect the pipeline must be validated through Pydantic schemas.
9. If evidence is missing, contradictory, low-confidence, or unverified, route to `MANUAL_REVIEW`.
10. The evidence bundle is the source of truth.

## Development Pattern

Use this sequence for new functional work:

1. Define or update the schema contract in `schemas/`.
2. Implement deterministic logic in `services/`.
3. Add focused pytest coverage in `tests/`.
4. Integrate into the pipeline or orchestrator.
5. Run a local smoke test.
6. Commit a small, clear change.

Agents and tools may be added only after the deterministic contract and service behavior exist.

## Validation Commands

Run the full test suite:

```bash
python -m pytest tests
```

Compile Python files when changing module boundaries or imports:

```bash
python -m py_compile $(find . -name "*.py" -not -path "./.venv/*")
```

Run the local acceptance runner:

```bash
python -m app.local_runner
```

Run the full planning runner when pipeline behavior changes:

```bash
python -m app.run_full_planning
```

## Agent Boundaries

Agents may:

- collect candidate source material
- extract facts into structured schemas
- summarize validated evidence
- draft memos from an evidence bundle
- propose review notes for an auditor

Agents must not:

- assign final decisions
- override deterministic services
- bypass Pydantic validation
- write directly into the evidence bundle without validation
- turn missing or uncertain evidence into a `CONTINUE`
- add real API calls or cloud dependencies without explicit approval

The required governance chain is:

```text
Agents propose.
Python validates.
Python decides.
Auditor reviews.
```

## Commit Style

Use small commits with direct messages, for example:

- `docs: add agent operating rules`
- `feat: add source scoring schema`
- `test: cover missing evidence routing`
- `refactor: isolate materiality helpers`

Do not commit automatically unless explicitly instructed.
