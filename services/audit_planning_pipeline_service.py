from __future__ import annotations

from copy import deepcopy

from schemas.decisions import FinalDecision
from schemas.evidence import AuditPlanningEvidenceBundle
from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import RiskAssessmentRequest
from services.acceptance_pipeline_service import run_acceptance_pipeline
from services.materiality_service import calculate_materiality
from services.risk_assessment_service import assess_audit_risks


def combine_final_decisions(*decisions: FinalDecision) -> FinalDecision:
    """
    Deterministic decision priority:
    REJECT overrides everything.
    MANUAL_REVIEW overrides CONTINUE.
    CONTINUE only applies when all modules continue.
    """
    if FinalDecision.REJECT in decisions:
        return FinalDecision.REJECT

    if FinalDecision.MANUAL_REVIEW in decisions:
        return FinalDecision.MANUAL_REVIEW

    return FinalDecision.CONTINUE


def run_audit_planning_pipeline(
    company_name: str,
    materiality_request: MaterialityRequest,
    risk_assessment_request: RiskAssessmentRequest,
) -> AuditPlanningEvidenceBundle:
    """
    Runs the deterministic full audit planning pipeline.

    This combines:
    - client acceptance / screening
    - engagement risk routing
    - materiality calculation
    - structured audit risk assessment by area/assertion

    The LLM is not involved in the decision.
    """
    acceptance_bundle = run_acceptance_pipeline(company_name)
    materiality_result = calculate_materiality(materiality_request)
    risk_assessment_result = assess_audit_risks(risk_assessment_request)

    evidence_data = deepcopy(acceptance_bundle.evidence_data)
    evidence_data["materiality_result"] = materiality_result.model_dump(mode="json")
    evidence_data["risk_assessment_result"] = risk_assessment_result.model_dump(mode="json")

    manual_review_reasons = list(acceptance_bundle.manual_review_reasons)

    if materiality_result.manual_review_flags:
        manual_review_reasons.extend(materiality_result.manual_review_flags)

    if risk_assessment_result.manual_review_reasons:
        manual_review_reasons.extend(risk_assessment_result.manual_review_reasons)

    final_decision = combine_final_decisions(
        acceptance_bundle.final_decision,
        materiality_result.decision,
        risk_assessment_result.decision,
    )

    if (
        final_decision == FinalDecision.MANUAL_REVIEW
        and not manual_review_reasons
    ):
        manual_review_reasons.append("Manual review required by full planning pipeline.")

    return AuditPlanningEvidenceBundle(
        run_id=acceptance_bundle.run_id,
        manual_version=acceptance_bundle.manual_version,
        target_company=company_name,
        engagement_type="Full Audit Planning",
        evidence_data=evidence_data,
        controls_evaluated=acceptance_bundle.controls_evaluated,
        missing_evidence=acceptance_bundle.missing_evidence,
        tool_errors=acceptance_bundle.tool_errors,
        ai_outputs=acceptance_bundle.ai_outputs,
        final_decision=final_decision,
        manual_review_reasons=manual_review_reasons,
    )