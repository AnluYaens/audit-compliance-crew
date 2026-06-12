# Future Azure Function Boundaries

These boundaries prepare the local services for future Azure Functions without
adding Azure dependencies. Every future activity should remain a wrapper around
the existing service and schema contracts.

## Activity Boundary Table

| Future activity | Local implementation | Request schema | Response schema | Notes |
|---|---|---|---|---|
| `read_client_crm_data` | `services.ingestion_service.read_client_crm_data_service` | `schemas.contracts.ClientCRMReadRequest` | `schemas.contracts.IngestionToolOutput` | Current service accepts `company_name` and returns a JSON string. A wrapper should validate the request before calling the service and validate the emitted JSON before returning it. |
| `check_partner_independence` | `services.screening_service.check_partner_independence_service` | `schemas.contracts.PartnerIndependenceRequest` | `schemas.contracts.ScreeningResponse` | Current service accepts `company_name` and returns a JSON string. |
| `scan_sanctions_watchlist` | `services.screening_service.scan_sanctions_watchlist_service` | `schemas.contracts.WatchlistScanRequest` | `schemas.contracts.ScreeningResponse` | Current service accepts `ceo_name`, `company_name`, and `global_offices`, then returns a JSON string. |
| `calculate_weighted_risk_score` | `services.risk_scoring_service.calculate_weighted_risk_score_service` | `schemas.contracts.RiskEvaluationInput` for validated mapped levels | `schemas.contracts.RiskScoringOutput` | Acceptance orchestration maps CRM attributes to risk levels before this service is called. |
| `score_source_registry` | `services.source_scoring_service.score_source_registry` | `schemas.source_registry.SourceRegistry` | `schemas.source_registry.SourceRegistryScoringResult` | Source scoring is deterministic provenance validation. It must not acquire evidence or approve weak sources. |
| `normalize_financial_statement` | `services.financial_normalization_service.normalize_financial_statement` | `schemas.financial_statements.FinancialStatementNormalizationRequest` | `schemas.financial_statements.FinancialStatementNormalizationResult` | This is the current local boundary corresponding to the planned statement extraction/normalization step. A separate extraction service is not present yet. |
| `calculate_materiality` | `services.materiality_service.calculate_materiality` | `schemas.materiality.MaterialityRequest` | `schemas.materiality.MaterialityResult` | The activity should only execute the configured deterministic materiality calculation. |
| `assess_audit_risks` | `services.risk_assessment_service.assess_audit_risks` | `schemas.risk_assessment.RiskAssessmentRequest` | `schemas.risk_assessment.RiskAssessmentResult` | Risk levels, risk types, and review routing are owned by the local service. |
| `design_audit_response` | `services.audit_response_service.design_audit_response` | `schemas.audit_response.AuditResponseRequest` | `schemas.audit_response.AuditResponseResult` | The activity should receive assessed risks and return planned procedures. |
| `generate_planning_memo` | `services.planning_memo_service.generate_planning_memo` | `schemas.evidence.AuditPlanningEvidenceBundle` | `str` markdown memo | The memo is presentation over an already validated evidence bundle; it must not change decisions. |
| `run_acceptance_pipeline` | `services.acceptance_pipeline_service.run_acceptance_pipeline` | `schemas.contracts.ClientCRMReadRequest` or future aggregate acceptance request | `schemas.evidence.AuditPlanningEvidenceBundle` | This is an orchestration-style local service today. In Durable Functions, its internal steps may become separate activities. |
| `run_audit_planning_pipeline` | `services.audit_planning_pipeline_service.run_audit_planning_pipeline` | Current typed arguments: `company_name`, `MaterialityRequest`, `RiskAssessmentRequest`, optional `list[SourceRecord]`, optional `require_source_support` | `schemas.evidence.AuditPlanningEvidenceBundle` | This maps to the future Durable Functions orchestrator. A future aggregate request schema can be added when wrapper work begins. |
| `evaluate_controls` | `services.control_evaluation_service.evaluate_controls` | `schemas.evidence.AuditPlanningEvidenceBundle` plus deterministic controls list | `schemas.evidence.AuditPlanningEvidenceBundle` | This supports `orchestration/planning_orchestrator.py` and should remain local-testable. |

## Orchestrator Boundary

The future Durable Functions orchestrator should coordinate activities only. It
should not contain business logic, scoring thresholds, materiality policy, source
quality rules, audit procedure selection, or memo conclusions.

Expected orchestration shape:

```text
client/company input
-> read_client_crm_data
-> check_partner_independence
-> scan_sanctions_watchlist
-> calculate_weighted_risk_score
-> normalize_financial_statement, when statement extraction exists
-> score_source_registry
-> calculate_materiality
-> assess_audit_risks
-> design_audit_response
-> evaluate_controls
-> generate_planning_memo
```

The final output boundary for the planning workflow is
`schemas.evidence.AuditPlanningEvidenceBundle`.

## Wrapper Rules

Future function wrappers should:

- validate inbound JSON into the documented request schema
- call exactly one local service, except for orchestrator wrappers
- validate the local service response before returning
- serialize with Pydantic JSON-compatible output, excluding computed fields from
  wire payloads when those fields are derived by the receiving model
- preserve fail-closed decisions from local services
- avoid Azure-specific imports in local service modules

Future function wrappers should not:

- contain scoring thresholds or compliance policy
- move service logic into `azure_functions/`
- depend on credentials during local tests
- call live external services unless the local service already owns that behavior
- accept or return free-form agent output without schema validation
