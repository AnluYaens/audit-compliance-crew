# Phase Prompts

Use these copy-paste prompts for future agent-assisted phases. Each prompt preserves the core rule:

```text
Python decides. Agents assist.
```

The active plan is a 10-day MVP demo roadmap. The MVP demonstrates architecture and deterministic pipeline behavior with synthetic data. It is not production-ready.

## Master Phase Prompt Template

```text
You are working on Audit Compliance Crew, a deterministic-first, agent-assisted audit planning and compliance engine.

Goal:
<state the phase goal>

Context:
Python decides. Agents assist. LLMs and agents may discover, extract, summarize, review, and draft. They must not decide final compliance outcomes.

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
- Sensitive client data stays local or inside an approved isolated sandbox.
- Public/global research may receive only non-sensitive hints.

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
- Do not send sensitive client data to OpenAI servers, public search providers, cloud AI APIs, or internet-connected tools.

Acceptance criteria:
<list criteria>

Suggested commit message:
<type(scope): message>
```

## Phase 12.1 - 10-Day MVP Roadmap Refresh

```text
Goal:
Refresh the project plan from a broad long-term roadmap into a focused 10-day MVP demo roadmap.

Context:
The MVP should demonstrate public research, offline sandbox verification, a safe hint bridge, deterministic reconciliation, evidence bundle generation, and human review routing with synthetic data. Python remains the only authority for CONTINUE, MANUAL_REVIEW, and REJECT.

Files to inspect:
- ROADMAP.md
- docs/PHASE_PROMPTS.md
- docs/ARCHITECTURE.md
- docs/AGENT_OPERATING_RULES.md
- docs/DECISION_POLICY.md
- docs/AZURE_MIGRATION_PLAN.md
- README.md

Files to create:
- none

Files to modify if needed:
- ROADMAP.md
- docs/PHASE_PROMPTS.md
- docs/ARCHITECTURE.md
- docs/AGENT_OPERATING_RULES.md
- docs/DECISION_POLICY.md
- docs/AZURE_MIGRATION_PLAN.md
- README.md

Architecture rules:
- Documentation only.
- Preserve "Python decides. Agents assist."
- Preserve final decision values: CONTINUE, MANUAL_REVIEW, REJECT.
- Preserve decision priority: REJECT > MANUAL_REVIEW > CONTINUE.
- Preserve evidence bundle as source of truth.
- Keep confidentiality boundaries clear: sensitive client data stays local or sandboxed, and public research receives only non-sensitive hints.

Required behavior:
- Make the 10-day MVP the active short-term plan.
- Keep prompts for Phases 13.1 through 19.1 practical and direct.
- Keep deferred work explicit, including Azure implementation, OCR, real model runtimes, production sandbox hardening, full human review UI, and production security hardening.
- State that this is a synthetic-data demo, not a production system.

Tests to add:
- none

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not modify schemas/, services/, tools/, ai/, storage/, orchestration/, manual_controls/, tests/, evals/, azure_functions implementation files, app/, or generated outputs.
- Do not add dependencies.
- Do not add Azure SDKs, credentials, deployment templates, cloud resources, network calls, real internet search, real OCR, real PDF parsing, CrewAI runtime, OpenAI API calls, or real model calls.

Acceptance criteria:
- Allowed documentation files describe the 10-day MVP plan.
- Public and sandbox lanes are clearly separated.
- Confidentiality rules are explicit.
- Final decision authority remains deterministic.

Suggested commit message:
docs: refresh roadmap for 10-day mvp
```

## Phase 13.1 - Client Artifact Schemas

```text
Goal:
Add Pydantic schemas for normalized client artifacts.

Context:
The MVP needs local normalized representations of synthetic client-provided data before sandbox/internal verification. This phase defines the schema contract only; parsing comes later.

Files to inspect:
- schemas/
- docs/ARCHITECTURE.md
- docs/DECISION_POLICY.md
- tests/

Files to create:
- schemas/client_artifacts.py
- tests/test_client_artifact_schemas.py

Files to modify if needed:
- schemas/__init__.py

Architecture rules:
- Keep strict Pydantic contracts in schemas/.
- Sensitive client data must stay local or inside an approved isolated sandbox.
- The evidence bundle remains the source of truth.
- Missing, malformed, ambiguous, weak, or sensitive evidence must be representable for manual review routing.

Required behavior:
- Represent normalized files, tables, text chunks, provenance, parser warnings, confidence, and sensitivity classification.
- Include source filename or local identifier, normalized artifact type, row/table/chunk references, extraction or parser warnings, confidence, and sensitivity labels.
- Support synthetic client artifacts without implementing real PDF, Excel, OCR, network, or AI parsing.

Tests to add:
- valid normalized file artifact validates
- valid table and text chunk artifacts validate
- provenance is required
- parser warnings and low confidence can be represented
- sensitivity classification is required
- invalid or missing required fields fail validation

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not implement parsing.
- Do not add PDF, Excel, OCR, network, or AI model calls.
- Do not add dependencies.
- Do not expose sensitive client data to public research schemas.

Acceptance criteria:
- Client artifact schemas exist and are tested.
- Schemas can represent confidence, warnings, provenance, and sensitivity.
- Existing tests still pass.

Suggested commit message:
feat: add client artifact schemas
```

## Phase 13.2 - CSV/JSON Normalization Service

```text
Goal:
Deterministically normalize synthetic CSV/JSON client files into schema-valid JSON artifacts.

Context:
The MVP should accept small synthetic local files and convert them into validated normalized artifacts for sandbox/internal verification. This is deterministic preprocessing, not AI extraction.

Files to inspect:
- schemas/client_artifacts.py
- services/
- tests/
- tests/fixtures/

Files to create:
- services/client_artifact_normalization_service.py
- tests/test_client_artifact_normalization_service.py
- tests/fixtures/client_artifacts/ if needed

Files to modify if needed:
- services/__init__.py

Architecture rules:
- Keep normalization logic in services/.
- Preserve provenance for every normalized artifact.
- Flag malformed, missing, ambiguous, or weak data.
- Sensitive client data remains local.

Required behavior:
- Normalize synthetic CSV and JSON inputs into schema-valid artifacts.
- Preserve local file identifiers, row/table/chunk references, parser warnings, confidence, and sensitivity classification.
- Return structured warnings for malformed rows, missing fields, ambiguous values, weak data, or unsupported file types.
- Avoid silent cleanup that would hide uncertainty from downstream manual review.

Tests to add:
- valid CSV normalizes into table artifacts
- valid JSON normalizes into structured artifacts
- malformed CSV is flagged
- missing required content is flagged
- ambiguous or weak values are flagged
- unsupported file type does not parse and records a warning/error

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not parse PDF files.
- Do not parse Excel files.
- Do not add OCR.
- Do not add network calls.
- Do not call AI models.
- Do not add dependencies.

Acceptance criteria:
- CSV/JSON normalization is deterministic and tested.
- Normalized outputs validate through Pydantic schemas.
- Provenance and warnings are preserved.

Suggested commit message:
feat: normalize synthetic client artifacts
```

## Phase 14.1 - Sandbox Verifier Contract

```text
Goal:
Define the offline/internal verifier schema and guardrails.

Context:
The sandbox/internal verifier checks confidential client-provided data locally. It may produce structured findings and safe public-search hint candidates, but it must not access the internet, call cloud AI APIs, or decide final outcomes.

Files to inspect:
- schemas/client_artifacts.py
- docs/AGENT_OPERATING_RULES.md
- docs/DECISION_POLICY.md
- tests/

Files to create:
- schemas/sandbox_verifier.py
- tests/test_sandbox_verifier_contracts.py

Files to modify if needed:
- schemas/__init__.py

Architecture rules:
- Sandbox verifier outputs must validate through Pydantic schemas.
- The verifier must not emit CONTINUE, MANUAL_REVIEW, or REJECT.
- Sensitive client data must stay local or inside an approved isolated sandbox.
- Any uncertainty must be expressible as review reasons.

Required behavior:
- Define verifier input and output schemas.
- Capture findings, contradictions, missing evidence, confidence, review reasons, and safe public-search hint candidates.
- Preserve artifact provenance references.
- Reject or omit final decision fields.

Tests to add:
- valid verifier output validates
- missing evidence can be represented
- contradiction requires review reason
- low confidence can be represented
- final decision field is rejected or ignored according to schema policy
- hint candidates carry safety metadata

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not add internet access.
- Do not call cloud AI APIs.
- Do not add real model calls.
- Do not decide final outcomes.

Acceptance criteria:
- Offline verifier contracts and guardrail tests exist.
- Schemas support findings, contradictions, missing evidence, confidence, review reasons, and hint candidates.

Suggested commit message:
feat: add sandbox verifier contract
```

## Phase 14.2 - Mock Sandbox Verifier

```text
Goal:
Implement a deterministic local mock verifier.

Context:
Before real local model or sandbox runtime work, the MVP needs deterministic mock behavior that reads normalized client artifacts and produces schema-valid internal findings.

Files to inspect:
- schemas/client_artifacts.py
- schemas/sandbox_verifier.py
- services/client_artifact_normalization_service.py
- tests/

Files to create:
- ai/sandbox_verifier.py
- tests/test_mock_sandbox_verifier.py

Files to modify if needed:
- ai/__init__.py

Architecture rules:
- Mock verifier behavior is deterministic.
- Mock outputs must validate through Pydantic schemas.
- The verifier cannot decide final outcomes.
- Candidate public-search hints must still pass through the safe hint bridge in a later phase.

Required behavior:
- Read normalized client artifacts.
- Produce findings, contradictions, missing evidence, confidence, review reasons, and safe public-search hint candidates.
- Provide deterministic synthetic cases for clean support, missing evidence, contradiction, and low confidence.

Tests to add:
- clean mock verifier output validates
- missing internal evidence creates review reasons
- contradictory internal evidence is preserved
- low-confidence internal evidence is flagged
- final decision is not present

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not call real models.
- Do not add network access.
- Do not send client data outside the local process.
- Do not produce CONTINUE, MANUAL_REVIEW, or REJECT.

Acceptance criteria:
- Mock sandbox verifier is deterministic and tested.
- Outputs are schema-valid and contain no final decisions.

Suggested commit message:
test: add mock sandbox verifier
```

## Phase 15.1 - Public Research Agent MVP

```text
Goal:
Create the public/global research lane for the MVP.

Context:
The public research lane uses only non-sensitive hints. The MVP should use a mock or fixed provider; real internet search requires a later explicit approval.

Files to inspect:
- schemas/source_registry.py
- docs/AGENT_OPERATING_RULES.md
- docs/DECISION_POLICY.md
- tests/

Files to create:
- schemas/public_research.py
- ai/public_research_agent.py
- tests/test_public_research_agent_mvp.py

Files to modify if needed:
- schemas/__init__.py
- ai/__init__.py

Architecture rules:
- Public research receives only non-sensitive hints.
- Public research outputs must validate through Pydantic schemas.
- Agents do not assign final decisions.
- Public evidence must carry citations, confidence, contradictions, and review reasons.

Required behavior:
- Accept safe hints such as company name, official website, public annual report targets, regulator sources, sanctions-list targets, and reliable-news targets.
- Produce public sources, citations, extracted public claims, confidence, contradictions, and review reasons.
- Use deterministic mock/fixed provider responses for the MVP.

Tests to add:
- valid public research output validates
- output includes citations/provenance
- low-confidence public evidence requires review reason
- contradictory public claims are preserved
- final decision field is rejected or absent
- sensitive hint examples are not accepted by the public lane schema or provider

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not add real internet search unless explicitly approved in a later mode.
- Do not add network calls.
- Do not call real models.
- Do not allow sensitive client data into public research.
- Do not decide final outcomes.

Acceptance criteria:
- Public research MVP contract and mock provider exist.
- Outputs validate and contain no final decisions.
- Sensitive inputs are blocked or rejected.

Suggested commit message:
feat: add public research mvp contract
```

## Phase 16.1 - Safe Hint Bridge

```text
Goal:
Deterministically filter sandbox-produced hints before they reach the public research lane.

Context:
The sandbox/internal lane may identify public-search hint candidates, but the bridge must prevent confidential client data from reaching public research or internet-connected tooling.

Files to inspect:
- schemas/sandbox_verifier.py
- schemas/public_research.py
- docs/AGENT_OPERATING_RULES.md
- tests/

Files to create:
- schemas/safe_hints.py
- services/safe_hint_bridge_service.py
- tests/test_safe_hint_bridge_service.py

Files to modify if needed:
- schemas/__init__.py
- services/__init__.py

Architecture rules:
- Filtering is deterministic business logic in services/.
- The bridge blocks confidential values, internal notes, uploaded document contents, private IDs, and sensitive client data.
- The bridge allows only safe public-search hints.
- No agent may bypass the bridge.

Required behavior:
- Accept sandbox hint candidates and return allowed hints plus blocked hint records.
- Allow public-safe categories such as company name, official website, annual report target, regulator source, sanctions-list target, and reliable-news target.
- Block client-private identifiers, document snippets, internal notes, non-public financial data, employee/customer data, and secrets.
- Preserve blocked reasons for auditability and manual review.

Tests to add:
- safe public hint is allowed
- confidential client value is blocked
- internal note is blocked
- uploaded document content is blocked
- private ID is blocked
- mixed input returns allowed and blocked records

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not add network calls.
- Do not call AI models.
- Do not place filtering logic in tools/.
- Do not allow raw sandbox outputs to reach public research.

Acceptance criteria:
- Safe hint bridge service is deterministic and tested.
- Blocked reasons are preserved.
- Public research receives only allowed hints.

Suggested commit message:
feat: add safe hint bridge
```

## Phase 17.1 - Evidence Reconciliation MVP

```text
Goal:
Create a deterministic service that compares internal/client findings with public research findings.

Context:
The MVP needs Python-owned reconciliation between sandbox/internal evidence and public evidence. Agreements may strengthen support. Missing, weak, contradictory, stale, unclear, or low-confidence evidence must route to MANUAL_REVIEW.

Files to inspect:
- schemas/evidence.py
- schemas/sandbox_verifier.py
- schemas/public_research.py
- services/source_scoring_service.py
- docs/DECISION_POLICY.md
- tests/

Files to create:
- schemas/evidence_reconciliation.py
- services/evidence_reconciliation_service.py
- tests/test_evidence_reconciliation_service.py

Files to modify if needed:
- schemas/__init__.py
- services/__init__.py
- evidence bundle schemas or pipeline integration only if needed

Architecture rules:
- Reconciliation is deterministic service logic.
- Agents do not decide.
- The evidence bundle remains the source of truth.
- Source scoring still cannot produce REJECT.
- Final decision priority remains REJECT > MANUAL_REVIEW > CONTINUE.

Required behavior:
- Compare internal/client findings with public research findings.
- Record agreements, conflicts, missing support, weak support, stale evidence, unclear evidence, and low-confidence evidence.
- Agreements strengthen support but cannot override hard-stop rejection criteria.
- Missing, weak, contradictory, stale, unclear, or low-confidence evidence routes to MANUAL_REVIEW.

Tests to add:
- matching internal and public findings produce supported reconciliation
- missing public evidence routes to MANUAL_REVIEW
- missing internal evidence routes to MANUAL_REVIEW
- contradictory findings route to MANUAL_REVIEW
- stale or low-confidence public source routes to MANUAL_REVIEW
- source scoring does not produce REJECT

Validation commands:
- python -m pytest tests
- git status --short

Forbidden actions:
- Do not let agents decide outcomes.
- Do not use source scoring to produce REJECT.
- Do not add network calls.
- Do not call real models.

Acceptance criteria:
- Reconciliation service is deterministic and tested.
- Review routing covers missing, weak, contradictory, stale, unclear, and low-confidence evidence.
- Evidence bundle integration preserves reconciliation details where applicable.

Suggested commit message:
feat: reconcile internal and public evidence
```

## Phase 18.1 - Two-Agent Demo Runner

```text
Goal:
Build an end-to-end synthetic demo runner for the two-lane MVP flow.

Context:
The demo should show local normalization, offline sandbox verification, safe hint filtering, public research via a mock/fixed provider, deterministic reconciliation, evidence bundle generation, and a demo memo/report.

Files to inspect:
- app/
- schemas/
- services/
- ai/
- storage/
- tests/
- README.md

Files to create:
- app/run_two_agent_demo.py
- tests/test_two_agent_demo_runner.py
- synthetic fixtures if needed

Files to modify if needed:
- README.md after the runner exists
- storage/ only if existing storage helpers are needed for evidence bundle output

Architecture rules:
- The runner orchestrates existing deterministic services and mock providers.
- Final decisions come only from deterministic Python services.
- The evidence bundle remains the source of truth.
- Synthetic data only.
- Local-first execution.

Required behavior:
- Run CSV/JSON normalization.
- Run mock sandbox verifier.
- Run safe hint bridge.
- Run mock/fixed public research provider.
- Run deterministic reconciliation.
- Generate or update an evidence bundle.
- Produce JSON and Markdown outputs suitable for a teacher demo.
- Show review routing for missing, weak, contradictory, stale, unclear, or low-confidence evidence.

Tests to add:
- demo runner completes with synthetic data
- generated JSON is schema-valid
- generated Markdown includes deterministic decision and review reasons
- no network or real model calls are required
- final decision comes from deterministic services

Validation commands:
- python -m pytest tests
- python -m app.run_two_agent_demo
- git status --short

Forbidden actions:
- Do not use real client data.
- Do not add network calls.
- Do not call real models.
- Do not add OpenAI API calls.
- Do not add CrewAI runtime.
- Do not add cloud dependencies.

Acceptance criteria:
- End-to-end synthetic demo runs locally.
- Outputs are suitable for a teacher demo.
- Security boundaries and deterministic decision ownership are visible in the output.

Suggested commit message:
feat: add two-agent mvp demo runner
```

## Phase 19.1 - Demo Documentation and Presentation Polish

```text
Goal:
Document how to run and explain the 10-day MVP demo.

Context:
The final MVP phase should make the synthetic demo easy to present, including expected commands, outputs, security boundaries, and the core principle that Python decides while agents assist.

Files to inspect:
- README.md
- ROADMAP.md
- docs/ARCHITECTURE.md
- docs/AGENT_OPERATING_RULES.md
- docs/DECISION_POLICY.md
- app/run_two_agent_demo.py

Files to create:
- docs/DEMO.md if needed

Files to modify if needed:
- README.md
- docs/DEMO.md
- docs/ARCHITECTURE.md

Architecture rules:
- Documentation must not imply production readiness.
- Documentation must not imply agents can decide final outcomes.
- Documentation must state that synthetic data is used.
- Documentation must state that sensitive client data stays local or inside an approved isolated sandbox.

Required behavior:
- Add demo command.
- Add expected JSON and Markdown outputs at a high level.
- Explain public/global research lane, offline sandbox/internal lane, safe hint bridge, deterministic reconciliation, and human review routing.
- Explain deferred production work.
- Preserve the local-first path to private server deployment and future Azure wrappers.

Tests to add:
- none required unless docs examples are executable and already covered by tests

Validation commands:
- python -m pytest tests
- python -m app.run_two_agent_demo
- git status --short

Forbidden actions:
- Do not add new dependencies.
- Do not add Azure SDKs, credentials, deployment templates, or cloud resources.
- Do not add real network, OCR, PDF parsing, CrewAI, OpenAI API, or model calls.
- Do not modify deterministic behavior unless the phase explicitly includes code alignment from completed earlier phases.

Acceptance criteria:
- README or demo docs include clear run instructions and expected outputs.
- Security boundaries are clear.
- The MVP is described as a demonstrable architecture and deterministic pipeline demo, not a production system.

Suggested commit message:
docs: polish mvp demo instructions
```
