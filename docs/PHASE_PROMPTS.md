# Phase Prompts

Use these copy-paste prompts for future agent-assisted phases. Each prompt preserves the core rule:

```text
Python decides. Agents assist.
```

## Master Phase Prompt Template

```text
You are working on Audit Compliance Crew, a deterministic-first, agent-assisted audit planning and compliance engine.

Goal:
<state the phase goal>

Context:
Python decides. Agents assist. LLMs and agents may discover, extract, summarize, review, and draft, but they must not decide final compliance outcomes.

Files to inspect:
<list files>

Files to create:
<list files>

Files to modify if needed:
<list files>

Architecture rules:
- Keep deterministic business logic in services/.
- Keep strict Pydantic contracts in schemas/.
- Keep tools/ as thin wrappers only.
- All pipeline-affecting agent outputs must validate through Pydantic schemas.
- Final decisions are CONTINUE, MANUAL_REVIEW, or REJECT.
- Decision priority is REJECT > MANUAL_REVIEW > CONTINUE.
- The evidence bundle is the source of truth.

Required behavior:
<describe behavior>

Tests to add:
<list tests>

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not add real API calls.
- Do not add Azure SDKs or credentials.
- Do not add real agent-runtime decision logic.
- Do not move business logic into tools/.
- Do not let agents decide final decisions.
- Do not remove fail-closed behavior.

Acceptance criteria:
<list criteria>

Suggested commit message:
<type(scope): message>
```

## Phase 4.1 - Source Registry and Source Scoring

```text
Goal:
Create a deterministic source registry and source scoring layer.

Context:
Audit Compliance Crew must track evidence provenance before future agents can acquire evidence. Source scoring is deterministic and must route weak, stale, contradictory, or unverified sources to MANUAL_REVIEW.

Files to inspect:
- schemas/evidence.py
- schemas/decisions.py
- services/audit_planning_pipeline_service.py
- storage/evidence_store.py
- manual_controls/
- tests/

Files to create:
- schemas/source_registry.py
- services/source_scoring_service.py
- storage/source_registry_store.py
- tests/test_source_scoring_service.py

Files to modify if needed:
- schemas/__init__.py
- services/__init__.py
- storage/__init__.py

Architecture rules:
- Source scoring is a deterministic service.
- Agents may propose source metadata later, but Python validates and scores.
- The evidence bundle remains the source of truth.

Required behavior:
- Define source records with URL or identifier, source type, publisher, retrieval date, confidence, freshness, and notes.
- Score authority, relevance, freshness, completeness, and contradiction flags.
- Return CONTINUE only for sufficiently reliable sources.
- Return MANUAL_REVIEW for missing, stale, low-confidence, or contradictory source metadata.

Tests to add:
- reliable source returns CONTINUE
- missing source identity returns MANUAL_REVIEW
- stale source returns MANUAL_REVIEW
- contradictory source returns MANUAL_REVIEW
- invalid schema input fails validation

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not browse or call live sources.
- Do not add real API calls.
- Do not let an agent approve a source.

Acceptance criteria:
- Source schemas and deterministic scoring service exist.
- Tests cover clean and fail-closed outcomes.
- Existing tests still pass.

Suggested commit message:
feat: add deterministic source scoring
```

## Phase 4.2 - Source Registry Integration with Evidence Bundle

```text
Goal:
Integrate source registry records with evidence bundles.

Context:
Evidence bundles must show not only facts, but where those facts came from and whether the source was reliable enough for deterministic use.

Files to inspect:
- schemas/evidence.py
- schemas/source_registry.py
- services/source_scoring_service.py
- storage/evidence_store.py
- storage/source_registry_store.py
- services/audit_planning_pipeline_service.py
- tests/

Files to create:
- tests/test_evidence_bundle_sources.py

Files to modify if needed:
- schemas/evidence.py
- services/audit_planning_pipeline_service.py
- storage/evidence_store.py

Architecture rules:
- Evidence source metadata must be structured.
- Source scoring must happen before a source can support CONTINUE.
- Weak source support must create a manual review reason.

Required behavior:
- Evidence bundles can reference source records or source scoring results.
- Missing or weak source records route relevant workflows to MANUAL_REVIEW.
- Source metadata is serializable and storage-safe.

Tests to add:
- evidence bundle stores source references
- weak source creates manual review reason
- missing source support does not allow CONTINUE
- stored bundle can be reloaded with source metadata

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not add live retrieval.
- Do not change final decision priority.
- Do not remove existing evidence fields.

Acceptance criteria:
- Evidence bundles can preserve source provenance.
- Source weakness fails closed.
- Existing smoke cases remain stable.

Suggested commit message:
feat: connect source registry to evidence bundles
```

## Phase 4.4 - Completed: Source Registry Documentation and Operating Rules

```text
Goal:
Document the source registry and source scoring behavior added in Phases 4.1-4.3.

Completed scope:
- README, architecture, agent operating rules, decision policy, evals, phase prompts, and roadmap now describe SourceRecord, SourceRegistry, deterministic source scoring, source support requirements, and memo reporting.
- Documentation confirms that Python services score and decide after schema validation.
- Documentation confirms that the evidence bundle remains the source of truth.
- Documentation confirms that source scoring may route weak support to MANUAL_REVIEW but cannot produce REJECT.
- Documentation confirms that planning memo source support is reporting-only.

Operating rules:
- Python decides. Agents assist.
- Agents may discover, extract, and summarize source metadata.
- Validated Python services score source metadata and apply routing rules.
- Required source support fails closed for missing, stale, low-confidence, contradictory, unverified, or weak metadata.
- Optional source support may be reported for visibility but does not override decisions.
- Final decision priority remains REJECT > MANUAL_REVIEW > CONTINUE.

Validation commands:
- python -m pytest tests
- python -m compileall schemas services storage orchestration tests
- git diff --check

Future next step:
Proceed to Phase 5.1: Financial Statement Schemas.

Suggested commit message:
docs: document source registry operating rules
```

## Phase 5.1 - Financial Statement Schemas

```text
Goal:
Create strict schemas for financial statement processing.

Context:
Future materiality and risk assessment should consume validated financial statement data, not raw extraction text.

Files to inspect:
- schemas/materiality.py
- schemas/risk_assessment.py
- services/materiality_service.py
- tests/test_materiality_service.py

Files to create:
- schemas/financial_statements.py
- tests/test_financial_statement_schemas.py

Files to modify if needed:
- schemas/__init__.py

Architecture rules:
- Financial statement data must be validated before services consume it.
- Low-confidence or incomplete extraction must route to MANUAL_REVIEW in downstream services.

Required behavior:
- Define balance sheet, income statement, cash flow, and notes-related schema models.
- Include period, currency, source reference, confidence, and missing fields.
- Support normalized line item representation.

Tests to add:
- valid statement schema passes
- missing period fails or is flagged
- missing required line item is represented
- low-confidence extraction can be represented

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not parse real PDFs yet.
- Do not add model calls.
- Do not change materiality calculations unless required by schema compatibility.

Acceptance criteria:
- Financial statement contracts exist.
- Tests prove validation and low-confidence representation.

Suggested commit message:
feat: add financial statement schemas
```

## Phase 5.2 - Financial Normalization Service

```text
Goal:
Create a deterministic service that normalizes validated financial statement records.

Context:
Financial extraction may vary by source, but downstream audit planning needs stable, validated inputs.

Files to inspect:
- schemas/financial_statements.py
- schemas/materiality.py
- services/materiality_service.py
- tests/test_materiality_service.py

Files to create:
- services/financial_normalization_service.py
- tests/test_financial_normalization_service.py

Files to modify if needed:
- services/__init__.py
- schemas/financial_statements.py

Architecture rules:
- Normalization is deterministic.
- Missing or contradictory statement data must fail closed.
- Agents may extract later, but Python normalizes and validates.

Required behavior:
- Convert statement line items into stable normalized fields.
- Preserve source references and confidence.
- Return manual review flags for missing, low-confidence, or contradictory financial facts.

Tests to add:
- normalizes complete statement input
- flags missing key line items
- flags contradictory values
- flags low confidence

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not call OCR, LLMs, or external APIs.
- Do not change final decisions directly from this service unless connected through a schema.

Acceptance criteria:
- Normalization service is deterministic and tested.
- Fail-closed cases are covered.

Suggested commit message:
feat: add financial normalization service
```

## Phase 6.1 - Research Agent Contract Layer

```text
Goal:
Create schemas and prompts for a future research agent contract layer.

Context:
Agents may discover and extract evidence, but their output must be validated before entering the deterministic pipeline.

Files to inspect:
- docs/AGENT_OPERATING_RULES.md
- schemas/source_registry.py
- schemas/evidence.py
- ai/

Files to create:
- schemas/research_agent.py
- ai/prompts/research_agent.md
- tests/test_research_agent_contracts.py

Files to modify if needed:
- schemas/__init__.py

Architecture rules:
- Agent output is structured and validated.
- No free-form agent output enters deterministic services.
- Agent output can require human review but cannot decide final outcomes.

Required behavior:
- Define candidate source and extracted evidence output schemas.
- Include confidence, citations, missing evidence, contradictions, and human_review_required.
- Create a prompt that forbids final decision-making.

Tests to add:
- valid research output validates
- missing citation fails or requires review
- final decision field is not accepted
- contradiction requires review

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not call a real LLM.
- Do not add real agent-runtime logic.
- Do not add web/API calls.

Acceptance criteria:
- Research agent contract exists.
- Guardrail tests prove agents cannot decide outcomes.

Suggested commit message:
feat: add research agent contracts
```

## Phase 6.2 - Mock Research Agent

```text
Goal:
Implement a mock research agent that returns schema-validated outputs for tests.

Context:
Before real model calls, the project needs deterministic fake agent behavior to test guardrails.

Files to inspect:
- schemas/research_agent.py
- ai/prompts/research_agent.md
- docs/EVALS_AND_AGENT_TRAINING.md

Files to create:
- ai/research_agent.py
- tests/test_mock_research_agent.py

Files to modify if needed:
- ai/__init__.py

Architecture rules:
- Mock agent does not call external services.
- Mock output validates through Pydantic.
- Invalid mock output must route to validation failure or manual review.

Required behavior:
- Provide deterministic mock responses for clean, missing, contradictory, and low-confidence cases.
- Return structured records only.

Tests to add:
- clean mock output validates
- missing evidence mock requires review
- contradictory mock requires review
- invalid output is rejected

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not call a real LLM.
- Do not add network access.
- Do not let the mock assign final decisions.

Acceptance criteria:
- Mock research agent supports deterministic guardrail tests.
- Existing tests pass.

Suggested commit message:
test: add mock research agent
```

## Phase 7.1 - Auditor Assistant Contract and Guardrails

```text
Goal:
Create the auditor assistant contract and guardrail tests.

Context:
The auditor assistant may explain evidence bundle contents, but it cannot change decisions or invent support.

Files to inspect:
- schemas/evidence.py
- services/audit_planning_pipeline_service.py
- docs/AGENT_OPERATING_RULES.md
- docs/DECISION_POLICY.md

Files to create:
- schemas/auditor_assistant.py
- ai/prompts/auditor_assistant.md
- ai/auditor_assistant.py
- tests/test_auditor_assistant_guardrails.py

Files to modify if needed:
- schemas/__init__.py
- ai/__init__.py

Architecture rules:
- Evidence bundle is the source of truth.
- Assistant answers must cite evidence fields.
- Assistant cannot assign or override final decisions.

Required behavior:
- Define assistant request and response schemas.
- Require citations to evidence bundle fields.
- Require refusal or manual-review language when support is missing.

Tests to add:
- answer cites evidence
- unsupported answer is rejected or flagged
- attempt to change decision is rejected
- missing evidence produces review-safe response

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not call real LLMs.
- Do not add UI.
- Do not mutate evidence bundles from assistant code.

Acceptance criteria:
- Auditor assistant contract and guardrails exist.
- Tests prove decision boundaries.

Suggested commit message:
feat: add auditor assistant guardrails
```

## Phase 8.1 - AI Memo Enhancement Wrapper

```text
Goal:
Create a safe wrapper for future AI memo enhancement.

Context:
AI may improve memo wording, but the deterministic memo content and evidence-supported conclusions remain authoritative.

Files to inspect:
- services/planning_memo_service.py
- storage/memo_store.py
- schemas/evidence.py
- docs/AGENT_OPERATING_RULES.md

Files to create:
- schemas/memo_enhancement.py
- ai/prompts/memo_enhancement.md
- ai/memo_enhancement_agent.py
- tests/test_memo_enhancement_agent.py

Files to modify if needed:
- schemas/__init__.py
- ai/__init__.py

Architecture rules:
- Memo enhancement cannot add unsupported facts.
- Enhanced memo requires human review.
- Evidence bundle remains the source of truth.

Required behavior:
- Define request and response schemas for memo enhancement.
- Preserve original deterministic decision and evidence references.
- Flag unsupported additions.

Tests to add:
- valid enhancement preserves decision
- unsupported fact is flagged
- decision change attempt is rejected
- enhanced memo is marked human_review_required

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not call real LLMs.
- Do not overwrite deterministic memo source.
- Do not suppress manual review reasons.

Acceptance criteria:
- Safe memo enhancement wrapper exists.
- Tests prove conclusions cannot be changed by AI enhancement.

Suggested commit message:
feat: add memo enhancement wrapper
```

## Phase 9.1 - Fixtures and Evaluation Dataset

```text
Goal:
Create the initial fixture and evaluation dataset structure.

Context:
Agent reliability should improve through evals and tests before any fine-tuning is considered.

Files to inspect:
- docs/EVALS_AND_TESTING.md
- docs/EVALS_AND_AGENT_TRAINING.md
- tests/

Files to create:
- tests/fixtures/README.md
- tests/fixtures/evidence_bundles/
- tests/fixtures/agent_outputs/
- tests/fixtures/financial_statements/
- evals/README.md
- evals/golden_outputs/
- tests/test_fixture_integrity.py

Files to modify if needed:
- none unless imports require it

Architecture rules:
- Fixtures should be deterministic and small.
- Golden outputs should avoid unstable timestamps.
- Real LLM evals are later, not required for unit tests.

Required behavior:
- Create representative fixtures for clean, reject, manual review, contradiction, missing evidence, and low-confidence cases.
- Add integrity tests that fixtures load and validate.

Tests to add:
- fixture files exist
- fixture JSON validates against schemas where applicable
- golden output metadata is readable

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not add real client data.
- Do not add real model calls.
- Do not fine-tune.

Acceptance criteria:
- Fixture structure exists and is documented.
- Integrity tests pass.

Suggested commit message:
test: add initial eval fixtures
```

## Phase 10.1 - Azure Function Boundary Preparation

```text
Goal:
Prepare local service boundaries for future Azure Functions.

Context:
The project should be Azure-ready without adding Azure dependencies yet.

Files to inspect:
- docs/AZURE_MIGRATION_PLAN.md
- services/
- schemas/
- orchestration/planning_orchestrator.py

Files to create:
- azure_functions/README.md
- azure_functions/function_boundaries.md
- tests/test_function_boundary_contracts.py

Files to modify if needed:
- schemas/ files if request/response contracts need clearer boundaries

Architecture rules:
- No Azure SDKs yet.
- No deployment files yet.
- Services remain locally testable.
- Function wrappers must not contain business logic.

Required behavior:
- Document each future activity boundary.
- Identify request and response schemas.
- Add tests for serializable boundary payloads where practical.

Tests to add:
- boundary payloads serialize
- pipeline inputs and outputs remain schema-valid
- no function-boundary test requires Azure

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not install Azure packages.
- Do not add credentials.
- Do not deploy anything.
- Do not move service logic into Azure folders.

Acceptance criteria:
- Function boundaries are documented.
- Tests verify local schema compatibility.

Suggested commit message:
docs: define azure function boundaries
```

## Phase 11.1 - Minimal Azure Prototype Planning

```text
Goal:
Plan a minimal Azure migration prototype.

Context:
The first Azure prototype should be narrow, reversible, and preserve deterministic decision ownership.

Files to inspect:
- docs/AZURE_MIGRATION_PLAN.md
- azure_functions/function_boundaries.md
- services/audit_planning_pipeline_service.py
- storage/

Files to create:
- azure_functions/prototype_plan.md

Files to modify if needed:
- docs/AZURE_MIGRATION_PLAN.md

Architecture rules:
- Planning only unless explicitly approved.
- No SDKs, credentials, deployment templates, or cloud resources.
- Durable Functions orchestration must call deterministic activities.

Required behavior:
- Identify the smallest useful prototype.
- Define trigger, activities, storage, logging, and rollback assumptions.
- Document security and audit-trail questions.

Tests to add:
- none required for planning-only work unless docs links or examples need validation

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not create cloud resources.
- Do not add Azure SDKs.
- Do not add secrets.
- Do not deploy.

Acceptance criteria:
- Prototype plan is explicit, narrow, and reversible.
- Deterministic decision ownership remains clear.

Suggested commit message:
docs: plan minimal azure prototype
```
