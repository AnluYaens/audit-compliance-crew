# Agent Operating Rules

Audit Compliance Crew may use agents to assist audit work, but agents do not own compliance decisions.

```text
Agents propose.
Python validates.
Python decides.
Auditor reviews.
```

## What Agents Can Do

Agents may collect public source candidates from non-sensitive hints, inspect local normalized artifacts inside an approved offline sandbox, extract structured facts, summarize validated evidence, draft memo language, answer auditor questions from cited evidence, and flag missing support, contradictions, or low confidence.

## What Agents Cannot Do

Agents must not:

- decide `CONTINUE`, `MANUAL_REVIEW`, or `REJECT`
- approve source support or assign source scoring decisions
- override deterministic services
- bypass schemas or validation
- write free-form content directly into the deterministic pipeline
- treat missing evidence as clean evidence
- suppress contradictory evidence
- remove fail-closed behavior
- call real external APIs unless explicitly approved
- create production Azure integrations or credentials
- send sensitive client data to OpenAI servers, public search providers, cloud AI APIs, or internet-connected tools
- pass raw sandbox outputs directly to public/global research

## Required Structured Outputs

Any agent output that affects the pipeline must use a Pydantic schema. Depending on the workflow, the schema should capture source identifiers, extracted facts, confidence, missing evidence, contradictions, citations or provenance, review flags, and tool or model errors.

Free-form agent text may be stored as a memo draft or review note, but it cannot become deterministic evidence until parsed and validated.

## Pydantic Validation Requirement

All pipeline-affecting agent outputs must follow this path:

```text
agent output
-> Pydantic schema validation
-> deterministic service review
-> evidence bundle update
-> final decision priority logic
```

If validation fails, the output must not be used as evidence. The failure should be recorded as a tool error or manual review reason.

## Agent Roles

### Public Research Agent

Uses only non-sensitive hints, such as company name, official website, public annual report targets, regulator sources, sanctions-list targets, and reliable-news targets. For the MVP, this lane may use a mock or fixed provider.

Allowed output: public sources, citations, extracted public claims, confidence, contradictions, and review reasons.

Forbidden output: confidential client data, final decisions, or unsupported claims.

### Offline Sandbox/Internal Verifier

Works only with local normalized client artifacts. It must not have internet access, call cloud AI APIs, or send confidential client data outside the local or approved isolated sandbox boundary.

Allowed output: schema-valid findings, contradictions, missing evidence, confidence, review reasons, and safe public-search hint candidates.

Forbidden output: final decisions or raw confidential data for public research.

### Safe Hint Bridge

This is deterministic Python service behavior, not agent discretion. The bridge filters sandbox-produced hint candidates before public research receives them, blocking confidential values, internal notes, uploaded document contents, private IDs, and sensitive client data.

### Research Scout Agent

Finds candidate sources for a company, engagement, industry, or audit question.

Allowed output: candidate source records with provenance, relevance notes, and uncertainty.

Forbidden output: final source approval or audit decision.

### Source Ranking Agent

Proposes metadata about authority, freshness, independence, and relevance.

Allowed output: structured observations for deterministic source scoring.

Forbidden output: source status that bypasses `services/source_scoring_service.py`.

Source scoring may route missing, stale, low-confidence, contradictory,
unverified, or weak source metadata to `MANUAL_REVIEW`, but it cannot return
`REJECT`. The evidence bundle remains the source of truth for scored source
support.

### Deep Evidence Agent

Extracts detailed evidence from selected sources.

Allowed output: structured facts with citations, confidence, and missing fields.

Forbidden output: unvalidated facts directly inserted into audit planning.

### Statement Processing Agent

Extracts financial statement line items and notes.

Allowed output: structured financial statement extraction records.

Forbidden output: materiality decisions or clean normalized financial inputs without validation.

### Audit Planning Assistant Agent

Explains the deterministic planning result to an auditor.

Allowed output: explanations, cited summaries, questions, and review support.

Forbidden output: changing final decisions or control statuses.

### Memo Enhancement Agent

Improves readability of deterministic memo drafts.

Allowed output: edited narrative, clarity suggestions, and quality flags.

Forbidden output: adding unsupported facts, changing conclusions, or changing
reported source support.

### Quality Review Agent

Reviews evidence bundles, memos, and agent outputs for inconsistency.

Allowed output: structured review findings and recommended manual follow-up.

Forbidden output: suppressing manual review reasons or approving a client.

## Manual Review Triggers for Agents

Agent-assisted work must route to `MANUAL_REVIEW` when evidence is missing, contradictory, low-confidence, stale, unverified, uncited, or outside the expected schema.

The evidence bundle remains the source of truth.

Planning memo source sections are reporting-only. They may summarize source
records and deterministic source scoring from the evidence bundle, but they do
not create evidence, approve sources, or override final decisions.
