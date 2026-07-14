# Minimal Azure Prototype Plan

This document is planning only. It describes the smallest useful future Azure
prototype shape without adding Azure SDKs, credentials, deployment templates,
cloud resources, infrastructure files, or Azure implementation code.

The core rule remains:

```text
Python decides. Agents assist.
```

Deterministic Python services remain the only authority for final decisions:
`CONTINUE`, `MANUAL_REVIEW`, and `REJECT`. Agents and LLMs may assist with
discovery, extraction, summarization, explanation, drafting, or wording, but
they must not assign or override final decisions.

## Smallest Useful Prototype

The first useful prototype should run one non-production audit planning workflow
through future Durable Functions boundaries while reusing the existing local
Python services as activity bodies.

Recommended prototype scope:

- one manually submitted company planning request
- one Durable Functions orchestration instance
- deterministic activity calls for acceptance, source scoring, materiality,
  risk assessment, audit response, and memo generation
- evidence bundle output using `schemas.evidence.AuditPlanningEvidenceBundle`
- optional memo output generated from the validated evidence bundle
- no live data acquisition, OCR, PDF parsing, LLM calls, CrewAI runtime, or
  external API calls

The prototype should prove boundary shape, orchestration sequencing, storage
contract assumptions, and auditability. It should not prove production
scalability, live integrations, agent behavior, or cloud security posture.

## Proposed Trigger

Use a manual HTTP trigger for the prototype request.

Request input should be a small aggregate payload that contains only data needed
to call existing deterministic services:

- `company_name`
- materiality request fields compatible with
  `schemas.materiality.MaterialityRequest`
- risk assessment request fields compatible with
  `schemas.risk_assessment.RiskAssessmentRequest`
- optional source records compatible with `schemas.source_registry.SourceRecord`
- optional `require_source_support`

The HTTP function should validate the request, start the orchestration, and
return the orchestration instance metadata. The HTTP trigger must not make
compliance decisions and must not call agents or external services.

A queue trigger can be considered after the HTTP prototype if batch submission
or replay behavior becomes important. It should not be part of the first
prototype.

## Durable Orchestration Shape

The Durable Functions orchestrator should coordinate activities only. It should
not contain scoring thresholds, materiality policy, source quality rules,
screening logic, audit procedure selection, memo conclusions, or final decision
logic.

Expected orchestration:

```text
HTTP trigger
-> start durable orchestration
-> run_acceptance_pipeline activity
-> calculate_materiality activity
-> assess_audit_risks activity
-> design_audit_response activity
-> score_source_registry activity, when source support is required or present
-> assemble_evidence_bundle activity
-> generate_planning_memo activity, optional
-> write_evidence_outputs activity
```

Durable Functions orchestration must call deterministic Python activities. The
activities may wrap existing service calls, but business logic should stay in
`services/`, `schemas/`, `storage/`, and existing orchestration modules rather
than moving into `azure_functions/`.

## Deterministic Activities

The prototype should prefer the boundaries already documented in
`azure_functions/function_boundaries.md`.

| Prototype activity | Local authority | Purpose |
|---|---|---|
| `run_acceptance_pipeline` | `services.acceptance_pipeline_service.run_acceptance_pipeline` | Runs deterministic acceptance, independence, sanctions, and engagement risk routing. |
| `calculate_materiality` | `services.materiality_service.calculate_materiality` | Calculates deterministic materiality and review flags. |
| `assess_audit_risks` | `services.risk_assessment_service.assess_audit_risks` | Assesses structured audit risks and review reasons. |
| `design_audit_response` | `services.audit_response_service.design_audit_response` | Designs deterministic audit response procedures from assessed risks. |
| `score_source_registry` | `services.source_scoring_service.score_source_registry` | Scores source metadata and routes weak support to `MANUAL_REVIEW`. |
| `assemble_evidence_bundle` | Existing evidence schemas and pipeline composition rules | Combines validated activity outputs and applies deterministic decision priority. |
| `generate_planning_memo` | `services.planning_memo_service.generate_planning_memo` | Produces presentation text from the validated evidence bundle only. |
| `write_evidence_outputs` | `storage/` concepts | Persists evidence, source registry, memo, and run metadata outputs. |

The current local `services.audit_planning_pipeline_service.run_audit_planning_pipeline`
already demonstrates the deterministic composition rules. A future Azure
prototype may either call that pipeline as a single coarse activity for the
smallest smoke test, or split the sequence into the activities above to exercise
Durable Functions replay and per-step audit logging. The split activity chain is
preferred for boundary validation once wrapper work is approved.

## Storage Inputs And Outputs

Prototype storage should model the future evidence ledger without introducing
new infrastructure in this planning phase.

Inputs:

- validated request payload
- deterministic activity inputs
- optional source metadata supplied with the request
- manual run metadata such as submitter role, environment label, and request id

Outputs:

- validated `AuditPlanningEvidenceBundle`
- source registry output when source records are present or required
- planning memo markdown when memo generation is enabled
- activity result records with schema name, service name, status, and timestamp
- orchestration run metadata with instance id, request id, target company, and
  final decision
- error records for validation failures, activity failures, and fail-closed
  routing

Storage assumptions:

- evidence bundle records should be immutable after write
- human overrides should be separate records and must not overwrite original
  system decisions
- memo records are derived from evidence bundles and must not become decision
  authority
- source records and source scoring results should remain traceable to the run
  that used them
- any storage key strategy must avoid secrets and should not encode sensitive
  client data beyond the minimum needed for traceability

## Logging And Audit-Trail Assumptions

The prototype should log orchestration and activity progress in a way that can
be reconciled with the evidence bundle.

Minimum log fields:

- run id
- orchestration instance id
- request id
- activity name
- local service name
- schema names for request and response payloads
- status: started, succeeded, failed, or routed to manual review
- final decision when available
- manual review reasons when available
- error category for validation or service failures
- timestamp

Audit-trail assumptions:

- logs should describe control flow and validation outcomes, not full secret or
  sensitive payloads
- every final decision must be explainable from validated evidence bundle fields
- every `MANUAL_REVIEW` or `REJECT` outcome should preserve deterministic
  reasons
- replay behavior must not create duplicate evidence records without an
  idempotency strategy
- agents, if introduced in later phases, must emit structured outputs that are
  validated before deterministic services can use them

## Rollback Assumptions

The prototype must be reversible.

Rollback should mean:

- no production workflow depends on the Azure prototype
- local CLI and local tests continue to work without Azure configuration
- deterministic services remain unchanged and locally testable
- removing the Azure wrapper layer does not remove business logic
- stored prototype outputs can be identified by environment label or run
  metadata
- failed or abandoned prototype runs do not alter local decision policy,
  schemas, or service behavior

The fallback path is the existing local pipeline and local storage outputs.

## Security Questions

Resolve these before any Azure implementation phase:

- What identity model should submit prototype requests?
- Which roles can start a run, read evidence, read memos, and record human
  overrides?
- Which payload fields are sensitive and should be excluded from logs?
- What retention period applies to evidence bundles, logs, memos, and source
  registry records?
- What encryption, key management, and private networking requirements apply?
- How should idempotency keys prevent duplicate writes during orchestrator
  replay or retries?
- What is the approved approach for configuration, secrets, and environment
  separation?
- What data classification rules apply to client names, financial statements,
  sanctions screening results, and auditor notes?

## Audit-Trail Questions

Resolve these before any Azure implementation phase:

- What is the canonical run id across HTTP request, orchestration instance,
  evidence bundle, source registry, memo, logs, and human review records?
- Which activity input and output hashes should be stored for replayable
  traceability?
- What fields must be immutable after final decision generation?
- How should failed validation be recorded when no evidence bundle can be
  produced?
- How are human override records linked to the original system decision?
- Who can mark a `MANUAL_REVIEW` item resolved, and what rationale is required?
- How should source scoring reasons be presented to auditors without implying
  that source scoring can produce `REJECT`?
- What audit report should show the path from request payload to final decision?

## Explicit Non-Goals for a Future Prototype

Do not:

- add Azure SDKs
- add credentials or secrets
- add deployment templates or infrastructure files
- create cloud resources
- implement Azure Functions
- make real API calls, network calls, OCR calls, PDF parsing calls, LLM calls,
  or CrewAI runtime calls
- change schemas, services, orchestration, storage, AI wrappers, or
  deterministic decision logic
- move business logic into `azure_functions/`

This plan does not authorize implementation. Any Azure implementation requires
a separate explicit approval.
