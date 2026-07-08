# Architecture

Audit Compliance Crew uses a deterministic-first architecture for audit planning and compliance.

```text
Python decides. Agents assist.
```

Agents may help discover, extract, summarize, review, and draft. Deterministic Python services own validation, routing, and final decisions.

## MVP Architecture Vision

The active short-term plan is a 10-day MVP demo. It is local-first, uses synthetic data, and is not a production system. The MVP adds two assisted lanes around the deterministic core:

```text
Synthetic client artifacts
-> deterministic CSV/JSON normalization
-> offline sandbox/internal verifier
-> safe hint bridge
-> public/global research provider using non-sensitive hints
-> deterministic evidence reconciliation
-> evidence bundle
-> deterministic final decision
-> demo memo/report and auditor review
```

The public research lane may use mock or fixed public evidence. Real internet search is deferred unless a later mode explicitly approves it. The offline sandbox/internal lane works only with local normalized artifacts and must not have internet access or call cloud AI APIs.

## Long-Term Architecture Vision

```text
Source discovery
-> source scoring
-> document extraction
-> evidence normalization
-> deterministic audit planning
-> evidence bundle
-> memo generation
-> auditor assistant
-> Azure orchestration
```

## Current Module Responsibilities

- `schemas/`: Pydantic contracts for decisions, evidence bundles, materiality, risk assessment, audit response, and future agent outputs.
- `services/`: deterministic business logic. This is where compliance and audit planning decisions live.
- `manual_controls/`: synthetic demo control metadata used to exercise deterministic planning logic without proprietary manual content.
- `tools/`: thin wrappers only. Tools call services; they do not contain business logic.
- `storage/`: evidence and memo persistence.
- `orchestration/`: workflow coordination for local runs and future Durable Functions migration.
- `ai/`: future safe agent wrappers and prompts.
- `app/`: local runner entry points.
- `tests/`: pytest coverage for services, pipelines, storage, and guardrails.

## MVP Confidentiality Boundaries

Sensitive client data stays local or inside an approved isolated sandbox and must not be sent to OpenAI servers, public search providers, cloud AI APIs, or internet-connected tools.

Public research may receive only non-sensitive hints, such as company name, official website, public annual report targets, regulator sources, sanctions-list targets, and reliable-news targets. Offline sandbox/internal verification works only with local normalized client artifacts.

Sandbox and public research outputs must validate through Pydantic schemas before deterministic services consume them. No agent may emit or override `CONTINUE`, `MANUAL_REVIEW`, or `REJECT`.

## Deterministic Data Flow

```text
Company name and planning inputs
-> schemas validate requests
-> ingestion service builds known client facts
-> screening service checks independence and sanctions facts
-> risk scoring service evaluates engagement risk
-> acceptance pipeline service produces an evidence bundle
-> source registry records provenance
-> source scoring service evaluates source support
-> materiality service calculates planning materiality
-> risk assessment service assesses account/assertion risks
-> audit response service designs deterministic responses
-> full planning pipeline combines decisions by priority
-> storage persists evidence and memo artifacts
```

Decision priority is always:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

`CONTINUE` is allowed only when every relevant deterministic module can continue.

## Evidence Bundle as Source of Truth

The evidence bundle is the controlled record for the pipeline. It contains:

- run metadata
- target company
- evaluated controls
- evidence data
- missing evidence
- tool errors
- AI output records
- final decision
- manual review reasons

Agents, memos, UI screens, and future Azure steps must read from validated evidence bundles, not unsupported free-form text.

Source support is also recorded in the evidence bundle. A bundle may carry
`SourceRecord` entries, a `SourceRegistryScoringResult`, and whether source
support was required for the workflow. The planning memo reports this section
from the bundle only; it does not create evidence, change source scores, or
override decisions.

## Future Agentic Architecture

Future agents can sit around the deterministic core:

- Research agents discover candidate sources.
- Source ranking agents propose source quality metadata.
- Deep evidence agents extract structured facts.
- Statement processing agents extract financial statement data.
- Memo agents improve narrative wording.
- Auditor assistant agents answer questions from evidence bundles.
- Quality review agents flag inconsistencies or missing support.

All agent output that affects the pipeline must validate through Pydantic schemas before a service may consume it.

For the MVP, agent-like behavior should be mock or deterministic first. Public research and sandbox verification may assist with structured findings, citations, confidence, contradictions, missing evidence, review reasons, and public-search hints. They do not decide final outcomes.

## Source Discovery Flow

```text
Research Scout Agent
-> candidate source records
-> Pydantic validation
-> source registry
-> deterministic source scoring
-> continue or manual-review source status
```

`SourceRecord` captures source identity, type, publisher, retrieval date,
freshness threshold, confidence, relevance, notes, and contradiction flags.
`SourceRegistry` groups records for one run and company.

Source scoring is deterministic and considers authority, relevance, freshness,
completeness, confidence, and contradictions. Missing identity, stale metadata,
low confidence, low relevance, weak authority, contradiction flags, unverified
metadata, or an empty registry fail closed to `MANUAL_REVIEW` when source support
is required.

Source scoring cannot return `REJECT`. Rejection remains reserved for hard-stop
deterministic criteria, and combined pipeline decisions still follow:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

For source-support-required workflows, missing or weak source scoring prevents
`CONTINUE`. For optional workflows, source metadata may be reported for auditor
visibility without becoming a decision override. Agents may discover, extract,
and summarize source metadata, but validated Python services score and decide.

## Statement Processing Flow

```text
Document input
-> extraction attempt
-> financial statement schema validation
-> confidence and completeness checks
-> normalization service
-> deterministic materiality and risk services
```

Low-confidence extraction, missing statement sections, or contradictory financial facts cannot become a clean planning input.

## Local-to-Azure Mapping

The current local services should map to Azure without changing decision ownership:

- `services/ingestion_service.py` -> Azure Function activity
- `services/source_scoring_service.py` -> Azure Function activity
- `services/statement_extraction_service.py` -> Azure Function activity
- `services/materiality_service.py` -> Azure Function activity
- `services/risk_assessment_service.py` -> Azure Function activity
- `services/audit_response_service.py` -> Azure Function activity
- `services/audit_planning_pipeline_service.py` -> Durable Functions orchestrator
- `storage/` -> evidence ledger storage
- `ai/` -> Azure AI Foundry agent layer

Do not add Azure SDKs, credentials, or deployment resources until an explicit migration phase begins.
