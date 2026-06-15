# BDO Compliance Crew Roadmap

This roadmap keeps the project aligned with the core architecture rule:

```text
Python decides. Agents assist.
```

Each phase should preserve deterministic decision ownership, strict schemas, fail-closed behavior, and Azure-ready service boundaries.

## Phase 0 - Stabilization and Documentation

Goal: Create the strategic documentation layer and make the current direction explicit.

Purpose: Give future contributors and agents a stable operating manual before adding more capabilities.

Expected files/modules:

- `CLAUDE.md`
- `ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/AGENT_OPERATING_RULES.md`
- `docs/DECISION_POLICY.md`
- `docs/EVALS_AND_TESTING.md`
- `docs/AZURE_MIGRATION_PLAN.md`
- `docs/EVALS_AND_AGENT_TRAINING.md`
- `docs/PHASE_PROMPTS.md`

Why it matters: Documentation prevents future agent work from drifting into unsafe decision-making or cloud coupling too early.

Constraints: Documentation only. Do not modify business logic, tests, or add real integrations.

## Phase 1 - Completed: Local Compliance Prototype

Goal: Demonstrate a local compliance screening workflow.

Purpose: Prove that deterministic Python can produce auditable acceptance decisions.

Expected files/modules:

- `app/run_full_planning.py`
- `schemas/`
- `services/`
- `storage/`
- `tests/`

Why it matters: Establishes the initial compliance use case and smoke cases.

Public cleanup note: Earlier CrewAI prototype entrypoints were removed from the active repository after the deterministic service architecture became the source of truth.

## Phase 2 - Completed: Azure-Ready Deterministic Architecture

Goal: Move core decisions into strict schemas and deterministic services.

Purpose: Make the project testable, auditable, and ready for future Azure Function boundaries.

Expected files/modules:

- `schemas/contracts.py`
- `schemas/decisions.py`
- `schemas/evidence.py`
- `services/ingestion_service.py`
- `services/screening_service.py`
- `services/risk_scoring_service.py`
- `services/acceptance_pipeline_service.py`
- `manual_controls/acceptance_controls.py`
- `orchestration/planning_orchestrator.py`

Why it matters: Ensures the LLM is not the acceptance decision-maker.

Constraints: Keep tools thin. Preserve fail-closed routing.

## Phase 3 - Full Audit Planning Pipeline

Goal: Extend acceptance into audit planning.

Purpose: Combine client acceptance, materiality, risk assessment, and audit response planning into one deterministic evidence bundle.

Expected files/modules:

- `schemas/materiality.py`
- `schemas/risk_assessment.py`
- `schemas/audit_response.py`
- `services/materiality_service.py`
- `services/risk_assessment_service.py`
- `services/audit_response_service.py`
- `services/audit_planning_pipeline_service.py`
- `services/planning_memo_service.py`
- `storage/evidence_store.py`
- `storage/memo_store.py`

Why it matters: Moves the product from screening into audit planning support.

Constraints: Final decisions still follow `REJECT > MANUAL_REVIEW > CONTINUE`.

## Phase 4 - Source Registry and Source Scoring

Goal: Add a structured source registry and deterministic source scoring.

Purpose: Track where evidence came from and whether it is reliable enough to use.

Expected files/modules:

- `schemas/source_registry.py`
- `services/source_scoring_service.py`
- `storage/source_registry_store.py`
- `tests/test_source_scoring_service.py`

Why it matters: Source quality becomes auditable instead of hidden inside agent output.

Completed scope:

- Phase 4.1: source registry contracts and deterministic source scoring.
- Phase 4.2: source registry integration with evidence bundles.
- Phase 4.3: planning memo reporting from evidence bundle source support.
- Phase 4.4: source registry documentation and operating rules.

Constraints: Unknown, unverified, stale, low-confidence, missing, or conflicting
required source support must trigger `MANUAL_REVIEW`. Source scoring cannot
produce `REJECT`; final decisions still follow
`REJECT > MANUAL_REVIEW > CONTINUE`. Agents may assist with source metadata, but
validated Python services score and decide. Planning memo source support is
reporting-only.

## Phase 5 - Financial Statement Processing Layer

Goal: Add financial statement ingestion and normalization contracts.

Purpose: Convert statement facts into validated data that deterministic planning services can consume.

Expected files/modules:

- `schemas/financial_statements.py`
- `services/statement_extraction_service.py`
- `services/financial_normalization_service.py`
- `tests/test_financial_normalization_service.py`

Why it matters: Audit planning needs reliable financial inputs for materiality and risk assessment.

Constraints: No free-form extraction may enter the pipeline without schema validation and confidence handling.

## Phase 6 - Evidence Acquisition Agents

Goal: Add safe agent wrappers for source discovery and evidence extraction.

Purpose: Let agents help find and structure evidence while deterministic services retain authority.

Expected files/modules:

- `ai/research_agent.py`
- `ai/prompts/research_agent.md`
- `schemas/research_agent.py`
- `services/evidence_normalization_service.py`
- `tests/test_research_agent_contracts.py`

Why it matters: Agents can increase coverage without taking over compliance decisions.

Constraints: No real API calls unless explicitly approved. Mock agents first.

## Phase 7 - Auditor Assistant Agent

Goal: Add an assistant that answers auditor questions from evidence bundles.

Purpose: Improve review workflow while keeping the evidence bundle as the source of truth.

Expected files/modules:

- `ai/auditor_assistant.py`
- `ai/prompts/auditor_assistant.md`
- `schemas/auditor_assistant.py`
- `tests/test_auditor_assistant_guardrails.py`

Why it matters: Auditors need explanations, not opaque automation.

Constraints: The assistant may explain and cite evidence, but may not change final decisions.

## Phase 8 - AI Memo Enhancement and Review Agent

Goal: Let an agent improve memo wording and flag quality issues.

Purpose: Separate narrative quality from deterministic memo facts and decisions.

Expected files/modules:

- `ai/memo_enhancement_agent.py`
- `ai/prompts/memo_enhancement.md`
- `schemas/memo_enhancement.py`
- `tests/test_memo_enhancement_agent.py`

Why it matters: Better memos are useful, but only if the underlying facts remain controlled.

Constraints: Enhanced memos must cite evidence bundle fields and require human review.

## Phase 9 - Evals, Training Dataset, and Agent Reliability

Goal: Build evaluation fixtures and reliability checks for agent behavior.

Purpose: Improve agent predictability through prompts, schemas, tests, and golden outputs before considering model training.

Expected files/modules:

- `tests/fixtures/`
- `evals/`
- `evals/golden_outputs/`
- `tests/test_agent_guardrails.py`
- `docs/EVALS_AND_AGENT_TRAINING.md`

Why it matters: Agent reliability must be measured, not assumed.

Constraints: Do not fine-tune first. Start with architecture, prompts, structured outputs, and evals.

## Phase 10 - Azure-Ready Function Boundaries

Goal: Make local services map cleanly to Azure Functions.

Purpose: Prepare the codebase for cloud orchestration without migrating prematurely.

Expected files/modules:

- `azure_functions/README.md`
- `azure_functions/function_boundaries.md`
- service-level request and response schemas
- integration tests around pipeline boundaries

Why it matters: Clean boundaries reduce migration risk.

Constraints: Do not add Azure SDKs, credentials, or deployment configuration yet.

## Phase 11 - Azure Migration Prototype

Goal: Design a minimal Azure prototype plan.

Purpose: Identify the first Durable Functions workflow and storage mapping.

Expected files/modules:

- `docs/AZURE_MIGRATION_PLAN.md`
- `azure_functions/prototype_plan.md`
- local adapter interfaces if needed

Why it matters: The migration should be incremental and reversible.

Constraints: Planning only unless explicitly approved. No deployment.

## Phase 12 - UI / CLI Auditor Workflow

Goal: Provide a practical auditor workflow through CLI or UI.

Purpose: Let auditors run planning, inspect evidence, review memos, and record override notes.

Expected files/modules:

- `app/cli.py`
- optional UI modules
- `storage/audit_trail_store.py`
- tests for review workflow

Why it matters: A useful audit tool needs clear human interaction points.

Constraints: The UI or CLI must not bypass deterministic services.

## Phase 13 - Security, Audit Trail, and Production Hardening

Goal: Harden the system for controlled production-like use.

Purpose: Add audit trail, access controls, retention planning, and operational safeguards.

Expected files/modules:

- audit trail schemas
- storage retention policy docs
- security review checklist
- production readiness tests

Why it matters: Compliance systems need evidence of process integrity, not just outputs.

Constraints: No secrets in the repo. No production credentials. Preserve human override traceability.
