from __future__ import annotations

from copy import deepcopy

from schemas.decisions import FinalDecision
from schemas.evidence import AuditPlanningEvidenceBundle
from schemas.materiality import MaterialityRequest
from services.acceptance_pipeline_service import run_acceptance_pipeline
from services.materiality_service import calculate_materiality


def combine_final_decisions(
    acceptance_decision: FinalDecision,
    materiality_decision: FinalDecision,
) -> FinalDecision:
    """
    Deterministic decision priority:
    REJECT overrides everything.
    MANUAL_REVIEW overrides CONTINUE.
    CONTINUE only applies when all modules continue.
    """
    if FinalDecision.REJECT in {acceptance_decision, materiality_decision}:
        return FinalDecision.REJECT

    if FinalDecision.MANUAL_REVIEW in {acceptance_decision, materiality_decision}:
        return FinalDecision.MANUAL_REVIEW

    return FinalDecision.CONTINUE


def run_audit_planning_pipeline(
    company_name: str,
    materiality_request: MaterialityRequest,
) -> AuditPlanningEvidenceBundle:
    """
    Runs the deterministic audit planning pipeline.

    This combines:
    - client acceptance / screening
    - engagement risk routing
    - materiality calculation

    The LLM is not involved in the decision.
    """
    acceptance_bundle = run_acceptance_pipeline(company_name)

    materiality_result = calculate_materiality(materiality_request)

    evidence_data = deepcopy(acceptance_bundle.evidence_data)
    evidence_data["materiality_result"] = materiality_result.model_dump(mode="json")

    manual_review_reasons = list(acceptance_bundle.manual_review_reasons)

    if materiality_result.manual_review_flags:
        manual_review_reasons.extend(materiality_result.manual_review_flags)

    final_decision = combine_final_decisions(
        acceptance_decision=acceptance_bundle.final_decision,
        materiality_decision=materiality_result.decision,
    )

    if (
        final_decision == FinalDecision.MANUAL_REVIEW
        and not manual_review_reasons
    ):
        manual_review_reasons.append("Manual review required by planning pipeline.")

    return AuditPlanningEvidenceBundle(
        run_id=acceptance_bundle.run_id,
        manual_version=acceptance_bundle.manual_version,
        target_company=company_name,
        engagement_type="Audit Planning",
        evidence_data=evidence_data,
        controls_evaluated=acceptance_bundle.controls_evaluated,
        missing_evidence=acceptance_bundle.missing_evidence,
        tool_errors=acceptance_bundle.tool_errors,
        ai_outputs=acceptance_bundle.ai_outputs,
        final_decision=final_decision,
        manual_review_reasons=manual_review_reasons,
    )