from manual_controls.control_model import ManualControl
from schemas.decisions import ControlStatus, FinalDecision
from schemas.evidence import AuditPlanningEvidenceBundle, ControlEvaluation


EMPTY_COLLECTION_ALLOWED_FIELDS = {
    "manual_review_reasons",
}


def is_missing_required_value(key: str, evidence_data: dict) -> bool:
    if key not in evidence_data:
        return True

    value = evidence_data.get(key)

    if value is None:
        return True

    if isinstance(value, str) and value.strip() == "":
        return True

    if isinstance(value, (list, dict, set, tuple)):
        if len(value) == 0 and key not in EMPTY_COLLECTION_ALLOWED_FIELDS:
            return True

    return False


def evaluate_control(
    control: ManualControl,
    evidence_data: dict,
) -> ControlEvaluation:
    missing_inputs = [
        key for key in control.required_inputs
        if is_missing_required_value(key, evidence_data)
    ]

    missing_outputs = [
        key for key in control.required_outputs
        if is_missing_required_value(key, evidence_data)
    ]

    if missing_inputs or missing_outputs:
        if control.fail_closed_if_missing:
            return ControlEvaluation(
                control_id=control.control_id,
                status=ControlStatus.MANUAL_REVIEW,
                missing_inputs=missing_inputs,
                missing_outputs=missing_outputs,
                notes="Required evidence is missing. Fail-closed behavior applied.",
            )

    return ControlEvaluation(
        control_id=control.control_id,
        status=ControlStatus.PASSED,
        notes="Required evidence is present.",
    )


def evaluate_controls(
    bundle: AuditPlanningEvidenceBundle,
    controls: list[ManualControl],
) -> AuditPlanningEvidenceBundle:
    evaluations = [
        evaluate_control(control, bundle.evidence_data)
        for control in controls
    ]

    bundle.controls_evaluated = evaluations

    for evaluation in evaluations:
        if evaluation.status in {ControlStatus.FAILED, ControlStatus.MANUAL_REVIEW}:
            bundle.final_decision = FinalDecision.MANUAL_REVIEW
            bundle.manual_review_reasons.append(
                f"{evaluation.control_id}: {evaluation.notes}"
            )
            bundle.missing_evidence.extend(evaluation.missing_inputs)
            bundle.missing_evidence.extend(evaluation.missing_outputs)

    if not bundle.manual_review_reasons:
        bundle.final_decision = FinalDecision.CONTINUE

    bundle.missing_evidence = sorted(set(bundle.missing_evidence))
    return bundle
