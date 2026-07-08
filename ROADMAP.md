# Audit Compliance Crew Roadmap

This roadmap keeps the project aligned with the core architecture rule:

```text
Python decides. Agents assist.
```

The active direction is a focused 10-day MVP demo, not a broad long-term buildout. The MVP should demonstrate architecture, deterministic pipeline behavior, evidence handling, and security boundaries with synthetic data. It is not production-ready.

Final decisions remain deterministic and limited to:

- `CONTINUE`
- `MANUAL_REVIEW`
- `REJECT`

Decision priority remains:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

The evidence bundle remains the source of truth.

## MVP Goal

Build a demonstrable local-first audit planning flow that shows:

- a public/global research lane using only non-sensitive search hints
- an offline sandbox/internal verification lane using local normalized client artifacts
- a safe hint bridge that prevents confidential data from reaching public research
- deterministic reconciliation of public and internal evidence
- human review routing for missing, weak, contradictory, stale, unclear, or low-confidence evidence
- a synthetic end-to-end demo runner with JSON and Markdown outputs
- service boundaries that can later run on a private server or behind Azure wrappers without moving business logic

## Confidentiality Rules

Sensitive client data must stay local or inside an approved isolated sandbox. It must not be sent to OpenAI servers, public search providers, cloud AI APIs, or internet-connected tools.

Public research may receive only non-sensitive hints, such as company name, official website, public annual report targets, regulator sources, sanctions-list targets, and reliable-news targets. The offline sandbox/internal lane works only with local normalized client artifacts.

Sandbox and public research outputs must validate through Pydantic schemas. No agent may emit or override `CONTINUE`, `MANUAL_REVIEW`, or `REJECT`.

## Current Completed Foundation

The existing repository already demonstrates the deterministic foundation:

- strict schema contracts in `schemas/`
- deterministic services in `services/`
- local orchestration in `orchestration/`
- evidence and memo persistence in `storage/`
- synthetic demo controls and fixtures
- source registry and deterministic source scoring
- fail-closed decision priority
- pytest coverage for the current deterministic pipeline

Earlier long-horizon phases remain useful as future direction, but they are no longer the active near-term plan.

## 10-Day MVP Sequence

### Phase 12.1 - 10-Day MVP Roadmap Refresh

Goal: Replace the broad roadmap emphasis with a focused 10-day MVP demo plan.

Scope: Documentation only.

Expected files/modules:

- `ROADMAP.md`
- `docs/PHASE_PROMPTS.md`
- `docs/ARCHITECTURE.md` if needed
- `docs/AGENT_OPERATING_RULES.md` if needed
- `docs/DECISION_POLICY.md` if needed
- `docs/AZURE_MIGRATION_PLAN.md` if needed
- `README.md` if needed

Acceptance criteria:

- The roadmap identifies the 10-day MVP as the active short-term plan.
- Public and sandbox confidentiality boundaries are clear.
- Deterministic final decision ownership is unchanged.
- Deferred production work is explicit.

### Phase 13.1 - Client Artifact Schemas

Goal: Add Pydantic schemas for normalized client artifacts.

Expected files/modules:

- `schemas/client_artifacts.py`
- `tests/test_client_artifact_schemas.py`

Required behavior:

- Represent normalized files, tables, text chunks, provenance, parser warnings, confidence, and sensitivity classification.
- Allow synthetic local artifacts to be represented without implementing real parsing.
- Preserve enough provenance for later evidence bundle use.

Constraints:

- No parsing implementation yet.
- No PDF, Excel, OCR, network, or AI model calls.
- Missing, ambiguous, weak, or sensitive fields must be representable for manual review routing.

### Phase 13.2 - CSV/JSON Normalization Service

Goal: Deterministically normalize synthetic CSV/JSON client files into schema-valid JSON artifacts.

Expected files/modules:

- `services/client_artifact_normalization_service.py`
- synthetic local fixtures if needed
- `tests/test_client_artifact_normalization_service.py`

Required behavior:

- Normalize only synthetic CSV/JSON inputs.
- Preserve provenance.
- Flag malformed, missing, ambiguous, or weak data.
- Classify sensitivity without exposing confidential content to public lanes.

Constraints:

- No PDF parsing.
- No Excel support.
- No OCR.
- No network calls.
- No AI model calls.

### Phase 14.1 - Sandbox Verifier Contract

Goal: Define the offline/internal verifier schema and guardrails.

Expected files/modules:

- `schemas/sandbox_verifier.py`
- `ai/prompts/sandbox_verifier.md` if useful for future mock behavior
- `tests/test_sandbox_verifier_contracts.py`

Required behavior:

- Define structured verifier inputs and outputs.
- Capture findings, contradictions, missing evidence, confidence, review reasons, and candidate public-search hints.
- Validate that outputs do not include final decisions.

Constraints:

- The verifier must not have internet access.
- The verifier must not call cloud AI APIs.
- The verifier must not decide final outcomes.

### Phase 14.2 - Mock Sandbox Verifier

Goal: Implement a deterministic local mock verifier.

Expected files/modules:

- `ai/sandbox_verifier.py` or a deterministic service if it affects pipeline behavior
- `tests/test_mock_sandbox_verifier.py`

Required behavior:

- Read normalized client artifacts.
- Produce findings, contradictions, missing evidence, confidence, review reasons, and safe public-search hints.
- Keep outputs schema-valid.

Constraints:

- No real model calls.
- No internet access.
- No final decisions.

### Phase 15.1 - Public Research Agent MVP

Goal: Add the public/global research lane for the MVP.

Expected files/modules:

- `schemas/public_research.py`
- `ai/public_research_agent.py` or deterministic mock provider
- `tests/test_public_research_agent_mvp.py`

Required behavior:

- Receive only non-sensitive hints.
- Use a mock/fixed provider first.
- Produce public sources, citations, extracted public claims, confidence, contradictions, and review reasons.
- Validate all outputs through Pydantic schemas.

Constraints:

- Real internet search is deferred unless an explicit later mode is approved.
- No sensitive client data may enter the public research lane.
- No final decisions.

### Phase 16.1 - Safe Hint Bridge

Goal: Deterministically filter sandbox-produced hints before public research receives them.

Expected files/modules:

- `services/safe_hint_bridge_service.py`
- `schemas/public_research.py` or `schemas/safe_hints.py`
- `tests/test_safe_hint_bridge_service.py`

Required behavior:

- Block confidential values, internal notes, uploaded document contents, private IDs, and sensitive client data.
- Allow only safe public-search hints.
- Record blocked hint reasons for auditability and manual review.

Constraints:

- Deterministic filtering only.
- No agent may bypass the bridge.
- No network calls.

### Phase 17.1 - Evidence Reconciliation MVP

Goal: Deterministically compare internal/client findings with public research findings.

Expected files/modules:

- `services/evidence_reconciliation_service.py`
- `schemas/evidence_reconciliation.py`
- `tests/test_evidence_reconciliation_service.py`

Required behavior:

- Compare sandbox/internal findings with public research findings.
- Treat agreement as stronger support.
- Route missing, weak, contradictory, stale, unclear, or low-confidence evidence to `MANUAL_REVIEW`.
- Preserve reconciliation results in the evidence bundle.

Constraints:

- Agents do not decide.
- Source scoring still cannot produce `REJECT`.
- `REJECT` remains reserved for deterministic hard-stop criteria.

### Phase 18.1 - Two-Agent Demo Runner

Goal: Create an end-to-end synthetic demo runner.

Expected files/modules:

- local runner under `app/`
- synthetic fixtures if needed
- output examples if needed
- `tests/test_two_agent_demo_runner.py` or focused integration coverage

Required behavior:

- Run normalization, sandbox verifier, hint bridge, public research provider, reconciliation, evidence bundle generation, and demo memo/report.
- Produce JSON and Markdown outputs suitable for a teacher demo.
- Use synthetic data only.

Constraints:

- Local-first execution.
- No network calls.
- No real model calls.
- No production credentials or cloud resources.

### Phase 19.1 - Demo Documentation and Presentation Polish

Goal: Document how to run and explain the MVP demo.

Expected files/modules:

- `README.md`
- `docs/` demo notes if needed

Required behavior:

- Add demo command.
- Add expected outputs.
- Explain security boundaries.
- Explain "Python decides. Agents assist."
- State clearly that the MVP is a demonstrable architecture and deterministic pipeline demo, not a production system.

Constraints:

- Documentation only unless a small runner command reference needs alignment with completed Phase 18.1 code.

## Deferred Work

The following remain deferred until explicitly approved:

- Azure implementation
- Durable Functions code
- deployment templates
- OCR
- scanned PDF support
- full Excel support
- GraphRAG/vector search
- real local model runtime
- real cloud model runtime
- real auditor assistant runtime
- real memo enhancement runtime
- production sandbox VM hardening
- full human review UI
- production security hardening

## Non-Goals for the MVP

- production deployment
- production security certification
- real client data processing
- real internet research by default
- real cloud AI calls
- real OpenAI API calls
- CrewAI runtime integration
- replacing human auditor judgment

## Azure Path

The MVP remains local-first. The same deterministic services can later be wrapped for a private server or Azure Functions, but Azure wrappers must not own business logic. Do not add Azure SDKs, credentials, deployment templates, cloud resources, or real cloud calls during the MVP phases.
