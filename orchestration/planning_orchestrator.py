from uuid import uuid4

from manual_controls.all_controls import MANUAL_CONTROLS
from schemas.evidence import AuditPlanningEvidenceBundle
from services.control_evaluation_service import evaluate_controls


def run_audit_planning_workflow(
    target_company: str,
    evidence_data: dict,
) -> AuditPlanningEvidenceBundle:
    run_id = f"RUN-{uuid4()}"

    bundle = AuditPlanningEvidenceBundle(
        run_id=run_id,
        target_company=target_company,
        evidence_data=evidence_data,
    )

    bundle = evaluate_controls(
        bundle=bundle,
        controls=MANUAL_CONTROLS,
    )

    return bundle
