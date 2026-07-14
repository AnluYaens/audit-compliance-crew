# Architecture

Audit Compliance Crew uses a deterministic-first architecture for audit planning
and evidence review.

```text
Python decides. Agents assist.
```

Agents may discover, extract, summarize, review, and draft. Deterministic Python
owns schema validation, evidence policy, routing, and final compliance decisions.

## Implemented Two-Agent Evidence Demo

The teacher-facing MVP is a local, synthetic-data workflow:

```text
Synthetic client CSV/JSON
-> deterministic normalization
-> deterministic mock offline sandbox verifier
-> deterministic Safe Hint Bridge
-> deterministic mock public research agent
-> deterministic evidence reconciliation
-> human-review signal
```

The demo returns validated stage objects in memory and prints a concise CLI
summary. It does not generate a final compliance decision, planning memo, or
saved evidence bundle. Its `EvidenceReconciliationStatus` and
`human_review_required` values describe evidence quality only.

The “sandbox” verifier is a deterministic mock contract implementation, not a
real VM or operating-system sandbox. The public research agent is a
deterministic fixed provider and performs no internet search. No LLM runtime is
present.

## Confidentiality Boundary

The implemented workflow separates two lanes:

```text
Local/internal lane
  normalized synthetic values
  local source metadata and provenance
              |
              v
Deterministic Safe Hint Bridge
  type, sensitivity, confidence, review,
  unsafe-marker, and status checks
  approved copies receive provenance=None
              |
              v
Mock public-research lane
  public-safe hint text only
```

A sandbox output must be successful and must not require human review before the
bridge will consider its hints. The bridge rejects unsafe or weak candidates and
removes provenance from approved copies. Raw local values, filenames, source
identifiers, and provenance do not cross into the public-research input.

This is a tested application boundary for synthetic data, not a production DLP,
network-isolation, or sandbox-hardening claim.

## Broader Deterministic Planning Pipeline

The repository also contains a separate deterministic planning foundation:

```text
Company and structured planning input
-> deterministic ingestion and screening
-> deterministic source scoring
-> materiality calculation
-> structured risk assessment
-> audit response planning
-> evidence bundle
-> deterministic final decision
-> planning memo and auditor review
```

That broader path can assign `CONTINUE`, `MANUAL_REVIEW`, or `REJECT`.
It is separate from the two-agent evidence demo. Decision priority is always:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

`CONTINUE` is available only when every relevant deterministic module has
sufficient validated support.

## Module Responsibilities

- `schemas/`: strict Pydantic contracts for artifacts, agent outputs, evidence,
  reconciliation, planning inputs, and decisions.
- `services/`: deterministic normalization, filtering, reconciliation,
  screening, scoring, materiality, planning, and memo logic.
- `ai/`: schema-constrained wrappers and deterministic mock providers; no live
  model or agent-framework runtime.
- `orchestration/`: local workflow coordination, including the two-agent demo
  and broader planning composition.
- `storage/`: local evidence, memo, and source-registry persistence.
- `manual_controls/`: public-safe synthetic control metadata.
- `app/`: local command entry points.
- `tests/`: unit, integration, contract, guardrail, and CLI coverage.
- `azure_functions/`: future boundary documentation only; no Azure runtime.
- `tools/`: thin interface boundary reserved for wrappers, not business logic.

## Validation and Decision Ownership

Pipeline-affecting assisted output follows:

```text
schema-constrained output
-> Pydantic validation
-> deterministic service
-> evidence record or reconciliation result
-> deterministic routing where applicable
-> auditor review
```

Agents cannot emit or override final decision fields. Invalid or uncertain
outputs cannot be silently treated as clean support.

## Evidence Bundle as Source of Truth

For decision-producing workflows, the evidence bundle is the controlled record.
It can contain:

- run metadata and target company
- evaluated controls
- evidence and provenance
- missing evidence and tool errors
- validated AI-output records
- source records and deterministic source-scoring results
- final decision and manual-review reasons

Memos, assistants, and future user interfaces must report from validated
evidence bundles rather than inventing facts or changing conclusions. The
two-agent demo does not currently persist its reconciliation result into this
bundle; it is a focused evidence-boundary demonstration.

## Deterministic Source Support

Source scoring evaluates structured source metadata for authority, relevance,
freshness, completeness, confidence, verification, and contradictions. Required
support that is missing, stale, weak, low-confidence, contradictory, or
unverified fails closed to `MANUAL_REVIEW`.

Source scoring cannot return `REJECT`. Rejection remains reserved for separate
deterministic hard-stop criteria such as confirmed independence conflicts or
sanctions hits.

## Assistant Boundaries

Current demo assistants are deterministic mocks:

- the sandbox verifier proposes structured internal findings and candidate
  public hints
- the public research wrapper proposes fixed public-style sources and extracted
  evidence
- the Safe Hint Bridge and reconciliation service are deterministic Python, not
  agent discretion

Future research, extraction, memo, auditor-assistant, or quality-review
capabilities may be introduced only behind stable schemas and deterministic
services. Planned capability must not be treated as currently implemented.

## Local-to-Azure Direction

Azure is not implemented. If a later migration is approved, thin adapters can
wrap existing local services without moving business logic:

| Local authority | Possible future Azure role |
| --- | --- |
| `services/ingestion_service.py` | Function activity |
| `services/source_scoring_service.py` | Function activity |
| `services/financial_normalization_service.py` | Function activity |
| `services/materiality_service.py` | Function activity |
| `services/risk_assessment_service.py` | Function activity |
| `services/audit_response_service.py` | Function activity |
| `services/audit_planning_pipeline_service.py` | Durable orchestration boundary |
| `storage/` | Evidence-ledger adapter |
| `ai/` | Optional schema-constrained assistance layer |

No Azure SDK, credential, deployment template, or cloud resource is present.

## Current Technical Limits

The MVP supports synthetic CSV/JSON normalization only. It has no OCR, PDF or
Excel parser, real browsing, network call, model runtime, agent framework, VM
isolation, cloud deployment, production security controls, or real client data.
