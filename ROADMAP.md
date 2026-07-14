# Audit Compliance Crew Roadmap

This public roadmap summarizes project status and likely next steps without
acting as an implementation prompt.

```text
Python decides. Agents assist.
```

## Current Status

The local MVP is implemented and tested with synthetic data. It demonstrates:

- deterministic CSV/JSON normalization with provenance
- a schema-constrained deterministic mock sandbox verifier
- deterministic filtering through the Safe Hint Bridge
- a schema-constrained deterministic mock public research lane
- deterministic evidence reconciliation
- a non-decisional human-review signal and concise CLI summary
- a separate deterministic audit-planning foundation with evidence bundles and
  final decision rules

The demo has no internet search, model runtime, VM isolation, cloud deployment,
or real client data. It is an architecture and evidence-quality demonstration,
not an autonomous auditing system or production service.

## Near-Term Priorities

- keep public documentation aligned with implemented behavior
- expand deterministic fixtures for missing, stale, weak, and contradictory
  evidence
- strengthen review ergonomics without weakening fail-closed behavior
- preserve stable schema and service boundaries for later deployment adapters
- keep generated artifacts, secrets, and private data outside version control

## Future Work Requiring Explicit Approval

- real sandbox or VM isolation
- controlled public-source acquisition
- optional model-assisted extraction behind schema validation
- additional document formats such as PDF and Excel, including OCR where needed
- human review and override records with a traceable audit trail
- Azure adapters, deployment infrastructure, and production security controls

Future work must preserve deterministic decision ownership, confidentiality
boundaries, evidence provenance, and the decision priority:

```text
REJECT > MANUAL_REVIEW > CONTINUE
```

## Out of Scope for the Current MVP

- autonomous audit conclusions
- production use or security certification
- real client or engagement data
- real browsing or network calls
- real model or agent-framework calls
- Azure SDKs or cloud resources
- OCR, PDF parsing, and Excel parsing

Future changes should be documented through public design notes, schemas,
tests, and reviewed change proposals.
