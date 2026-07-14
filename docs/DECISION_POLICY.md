# Decision Policy

Final compliance and audit planning decisions are deterministic. LLMs and agents may assist with discovery and drafting, but Python assigns final decision values.

## Final Decision Values

- `CONTINUE`: the engagement can continue through the automated planning path.
- `MANUAL_REVIEW`: a human auditor must review uncertainty, missing evidence, high risk, or unresolved facts.
- `REJECT`: the engagement must not continue based on deterministic rejection criteria.

## Decision Priority

When modules disagree, combine outcomes in this order:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

`REJECT` overrides every other outcome. `MANUAL_REVIEW` overrides `CONTINUE`. `CONTINUE` applies only when all relevant services continue.

## REJECT Triggers

Route to `REJECT` when deterministic evidence identifies:

- independence conflicts
- sanctions hits
- prohibited client or engagement facts
- failed controls that require rejection
- any future hard-stop condition defined in `manual_controls/`

`REJECT` should be explainable from evidence bundle fields and evaluated controls.

## MANUAL_REVIEW Triggers

Route to `MANUAL_REVIEW` when:

- required evidence is missing
- evidence is contradictory
- extraction confidence is low
- required source support is missing, stale, low-confidence, contradictory, unverified, or weak
- public evidence and internal/client evidence are missing, weak, contradictory, stale, unclear, or low-confidence after reconciliation
- sandbox verifier or public research output fails Pydantic validation
- safe hint filtering blocks required search context and leaves evidence unsupported
- client data is unknown or incomplete
- engagement risk is high but not automatically rejecting
- materiality inputs are unusual or unsupported
- risk assessment inputs are incomplete
- audit response planning identifies unresolved planning issues
- an agent output fails schema validation
- a tool fails or returns unusable data

Manual review is required when uncertainty affects the conclusion.

## CONTINUE Criteria

Route to `CONTINUE` only when:

- all required deterministic checks pass
- no rejection trigger exists
- no manual review trigger exists
- evidence is present and sufficiently reliable
- all pipeline-affecting outputs have passed Pydantic validation
- the evidence bundle supports the conclusion

`CONTINUE` is never inferred from silence or missing data.

## Fail-Closed Policy

The system must fail closed. If the pipeline cannot establish reliable support for a clean outcome, it must route to `MANUAL_REVIEW` or `REJECT`, depending on the condition.

Examples include missing source data, invalid agent output, or a tool error during a required check routing to `MANUAL_REVIEW`; confirmed independence conflicts or sanctions hits route to `REJECT`.

## Source Scoring Policy

Source scoring is deterministic support logic. `SourceRecord` captures provenance
metadata, and `SourceRegistry` groups records for one run. The source scoring
service evaluates authority, relevance, freshness, completeness, confidence, and
contradictions after schema validation.

Required source support must fail closed to `MANUAL_REVIEW` when source metadata
is missing, stale, low-confidence, contradictory, unverified, incomplete, or
below deterministic scoring thresholds. Optional source support may be reported
for auditor visibility, but it does not override the evidence bundle or final
decision.

Source scoring cannot produce `REJECT`. Hard rejection must come from separate
deterministic rejection criteria, and final decision priority remains:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

## Missing Evidence Policy

Missing evidence must be recorded in the evidence bundle and should create a manual review reason when it affects the conclusion.

The system must not fill gaps with agent assumptions.

## MVP Evidence-Reconciliation Policy

The MVP reconciliation service is deterministic. It compares offline/internal
findings from local normalized client artifacts with mock public research
findings derived from non-sensitive hints. Agreements may strengthen evidence
support, but agents cannot resolve contradictions or decide final outcomes.

The teacher-facing demo produces an `EvidenceReconciliationStatus` and a
`human_review_required` signal. Missing, weak, contradictory, stale, unclear,
low-confidence, schema-invalid, or source-error evidence must set the
appropriate review signal. These values are not final compliance decisions:

- `aligned` does not mean `CONTINUE`
- `human_review_required` does not independently assign `MANUAL_REVIEW`
- reconciliation cannot produce `REJECT`

If a decision-producing workflow later consumes a validated reconciliation
result, deterministic policy must prevent a clean outcome while a review signal
is present. Hard rejection remains reserved for separate deterministic
hard-stop criteria.

## Confidentiality Policy

Sensitive client data must stay local or inside an approved isolated sandbox. It must not be sent to OpenAI servers, public search providers, cloud AI APIs, or internet-connected tools.

Public research may receive only non-sensitive hints such as company name, official website, public annual report targets, regulator sources, sanctions-list targets, and reliable-news targets. The offline sandbox/internal lane works only with local normalized client artifacts. Sandbox and public research outputs must validate through Pydantic schemas before deterministic services may use them.

## Contradictory Evidence Policy

Contradictory evidence must route to `MANUAL_REVIEW` unless deterministic rules identify a hard rejection trigger.

Contradictions should be preserved for auditor review rather than silently resolved by an agent.

## Memo Reporting Policy

Planning memo source support is reporting-only. Memo output may present source
records, source scoring status, and source manual review reasons already present
in the evidence bundle, but it must not create source support, change source
scores, or override final decisions.

## Low-Confidence Extraction Policy

Low-confidence extraction cannot be treated as reliable evidence. The extracted data may be stored for review, but deterministic services should not use it as clean input unless it passes validation and confidence thresholds.

## Human Auditor Override Concept

A human auditor may override or resolve a decision outside the automated pipeline, but the override must be explicit, traceable, and supported by documented rationale.

Future override records should include:

- original system decision
- auditor override decision
- rationale
- supporting evidence
- reviewer identity or role
- timestamp

The automated pipeline should not hide the original decision.

## Expected Smoke-Case Decisions

| Company | Expected decision | Reason |
|---|---|---|
| Quantum Cybernetics | `REJECT` | Independence conflict |
| Vanguard Mining Corp | `REJECT` | Sanctions hit and high risk |
| Apex Energy Group | `MANUAL_REVIEW` | High engagement risk |
| GreenLeaf Organics | `CONTINUE` | Clean screening |
| Unknown Company ABC | `MANUAL_REVIEW` | Missing client data and fail-closed routing |
