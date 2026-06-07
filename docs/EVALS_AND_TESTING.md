# Evals and Testing

Testing protects the project's core promise:

```text
Python decides. Agents assist.
```

The test strategy should prove that deterministic services, schemas, storage, and future agents preserve fail-closed behavior.

## Unit Tests

Unit tests should cover individual deterministic services and schema behavior.

Current examples:

- `tests/test_acceptance_pipeline_service.py`
- `tests/test_materiality_service.py`
- `tests/test_risk_assessment_service.py`
- `tests/test_audit_response_service.py`
- `tests/test_deterministic_services.py`
- `tests/test_phase2_control_evaluation.py`
- `tests/test_source_scoring_service.py`

Unit tests should assert:

- expected decisions
- manual review reasons
- rejection triggers
- missing evidence handling
- source scoring fail-closed behavior
- schema validation errors
- deterministic output shape

## Integration Tests

Integration tests should cover service composition and full pipeline behavior.

Current examples:

- `tests/test_audit_planning_pipeline_service.py`
- `tests/test_evidence_bundle_sources.py`
- `tests/test_full_planning_runner_storage.py`
- `tests/test_memo_store.py`
- `tests/test_planning_memo_service.py`

Integration tests should confirm that combined decisions follow:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

## Manual Smoke Tests

Run:

```bash
python -m app.local_runner
python -m app.run_full_planning
```

Manual smoke tests should print readable outcomes for known companies and produce inspectable evidence or memo artifacts.

## Required Validation Command

Before finishing a change, run:

```bash
python -m pytest tests
```

When changing imports, module boundaries, or broad Python structure, also run:

```bash
python -m compileall schemas services storage orchestration tests
```

## Fixtures Strategy

Future fixtures should live under `tests/fixtures/` and represent:

- known clean clients
- independence conflicts
- sanctions hits
- high-risk engagements
- missing company data
- missing or weak required source support
- contradictory evidence
- low-confidence extraction
- invalid agent outputs
- sample financial statements

Fixtures should be small, readable, and versioned with expected outcomes.

## Golden Output Strategy

Golden outputs should capture stable expected artifacts, such as:

- evidence bundle snapshots
- planning memo drafts
- normalized financial statement records
- source scoring outputs
- evidence bundle source records
- agent structured outputs

Golden files should avoid brittle timestamps and run IDs unless those values are explicitly normalized.

## Fake Model Strategy

Agent tests should start with fake models, not real LLM calls.

Fake models should return:

- valid structured output
- invalid JSON
- schema-valid but low-confidence output
- contradictory evidence
- unsupported claims
- empty responses
- tool error simulations

This lets guardrails be tested deterministically.

## Agent Guardrail Tests

Future agent guardrail tests should assert that:

- free-form output cannot enter the deterministic pipeline
- invalid agent output causes `MANUAL_REVIEW`
- low confidence causes `MANUAL_REVIEW`
- missing citations cause `MANUAL_REVIEW`
- agents cannot assign final decisions
- agents cannot approve source support or produce `REJECT` through source scoring
- memo enhancement cannot add unsupported facts
- memo source sections report only evidence bundle source support
- auditor assistant answers cite evidence bundle fields

## Current Smoke Cases

| Company | Expected decision |
|---|---|
| Quantum Cybernetics | `REJECT` |
| Vanguard Mining Corp | `REJECT` |
| Apex Energy Group | `MANUAL_REVIEW` |
| GreenLeaf Organics | `CONTINUE` |
| Unknown Company ABC | `MANUAL_REVIEW` |

These cases should remain stable unless the documented control assumptions change.

## Future Test Fixtures

Planned fixture groups:

- `tests/fixtures/sources/`
- `tests/fixtures/financial_statements/`
- `tests/fixtures/agent_outputs/`
- `tests/fixtures/evidence_bundles/`
- `tests/fixtures/golden_memos/`

The fixture set should become the base for future evals and reliability tracking.
