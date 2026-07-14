# Agent Operating Rules

Audit Compliance Crew may use agents or agent-like wrappers to assist audit
work, but they never own compliance decisions.

```text
Agents propose.
Python validates.
Python decides.
Auditor reviews.
```

## Current Demo Components

The two “agents” in the current MVP are deterministic mock wrappers, not LLM
runtimes.

### Mock Offline Sandbox Verifier

The verifier reads a normalized synthetic artifact bundle and returns
schema-valid findings, missing evidence, contradictions, confidence, review
reasons, and candidate public-search hints.

It does not browse, call a model, run inside a VM, or provide real sandbox
isolation. It cannot emit a final compliance decision.

### Safe Hint Bridge

The bridge is deterministic Python, not an agent. It accepts candidates only
from a successful, non-review verifier result and applies type, sensitivity,
confidence, review, and unsafe-marker rules.

Approved copies have local provenance removed. Review-required verifier results
produce no approved hints. No agent may bypass the bridge or pass raw local
output to the public lane.

### Mock Public Research Agent

The public wrapper receives only bridge-approved, provenance-free hints and
returns fixed schema-valid public-style sources and extracted evidence for the
selected scenario.

It does not search the internet, call an external API, or use a model. It cannot
receive raw artifact values or determine a final outcome.

### Evidence Reconciliation

Reconciliation is deterministic Python, not agent judgment. It compares local
and public outputs and reports an evidence status plus a human-review signal.
Those values are not `CONTINUE`, `MANUAL_REVIEW`, or `REJECT` decisions.

## What Assisted Components May Do

Within an approved, schema-constrained workflow, assistants may:

- collect candidate public sources from non-sensitive hints
- inspect local normalized artifacts inside an approved local boundary
- extract structured facts with citations or provenance
- summarize validated evidence
- draft memo wording from an evidence bundle
- answer auditor questions from cited evidence
- flag missing, contradictory, stale, weak, or low-confidence support

## What Assisted Components Must Not Do

Agents and wrappers must not:

- decide or override `CONTINUE`, `MANUAL_REVIEW`, or `REJECT`
- approve source support or bypass deterministic source scoring
- bypass Pydantic schemas or validation
- write free-form content directly into deterministic evidence
- treat missing evidence as clean evidence
- suppress contradictions, uncertainty, citations, or tool errors
- remove fail-closed behavior
- pass raw sandbox output or local provenance to public research
- send sensitive client data to model providers, search providers, cloud AI
  APIs, or internet-connected tools
- call real external APIs unless a separately approved feature introduces them
- create production Azure integrations or credentials

## Structured Output Requirement

Any assisted output that affects processing must use a Pydantic contract. The
contract should capture the fields relevant to its role, such as:

- source or evidence identifiers
- extracted facts
- confidence
- citations or local provenance
- missing evidence
- contradictions
- review flags and reasons
- tool or model errors

Free-form prose may be stored as a draft or review note, but it cannot become
pipeline evidence without parsing and validation.

## Validation Path

The applicable path is:

```text
schema-constrained assisted output
-> Pydantic validation
-> deterministic service
-> validated evidence or reconciliation result
-> deterministic routing where applicable
-> auditor review
```

The current two-agent demo ends with a reconciliation result and does not write
an evidence bundle or assign a final decision. Decision-producing workflows use
the evidence bundle as their source of truth.

If validation fails, the output must not be accepted as evidence. The failure
must remain visible as a review reason or tool error in the applicable
deterministic workflow.

## Future Permitted Roles

The following are governed design roles, not claims about current live agent
capabilities:

- **Research scout** — may propose candidate sources; cannot approve them.
- **Source metadata assistant** — may propose authority, freshness, and
  relevance metadata; cannot bypass deterministic scoring.
- **Evidence extraction assistant** — may propose cited structured facts; cannot
  insert unvalidated facts into planning.
- **Statement extraction assistant** — may propose financial statement fields;
  cannot calculate materiality or certify clean input.
- **Memo enhancement assistant** — may improve wording; cannot add unsupported
  facts or change conclusions.
- **Auditor assistant** — may explain cited evidence-bundle content; cannot
  alter decisions.
- **Quality review assistant** — may flag issues; cannot suppress review reasons
  or approve a client.

Introducing any real implementation would require an explicit change, stable
schemas, deterministic validation, tests, and an approved confidentiality
boundary.

## Human Review Triggers

Assisted work must remain review-required when evidence is missing,
contradictory, low-confidence, stale, weak, unverified, uncited, schema-invalid,
or affected by a tool error.

Source scoring and reconciliation cannot produce `REJECT`. Memo and assistant
outputs are reporting-only. The evidence bundle remains the source of truth for
workflows that assign final outcomes.
