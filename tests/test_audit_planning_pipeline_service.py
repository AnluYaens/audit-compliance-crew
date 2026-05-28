from schemas.decisions import FinalDecision
from schemas.materiality import MaterialityRequest
from services.audit_planning_pipeline_service import run_audit_planning_pipeline


def valid_materiality_request(company_name: str = "GreenLeaf Organics") -> MaterialityRequest:
    return MaterialityRequest(
        target_company=company_name,
        benchmark_type="profit_before_tax",
        benchmark_amount=1_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Profit before tax is stable and appropriate for this prototype.",
    )


def flagged_materiality_request(company_name: str = "GreenLeaf Organics") -> MaterialityRequest:
    return MaterialityRequest(
        target_company=company_name,
        benchmark_type="revenue",
        benchmark_amount=10_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Revenue benchmark selected for demonstration.",
    )


def test_clean_acceptance_and_clean_materiality_continue():
    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=valid_materiality_request(),
    )

    assert bundle.final_decision == FinalDecision.CONTINUE
    assert bundle.evidence_data["materiality_result"]["decision"] == FinalDecision.CONTINUE


def test_clean_acceptance_but_flagged_materiality_routes_manual_review():
    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=flagged_materiality_request(),
    )

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert bundle.evidence_data["materiality_result"]["decision"] == FinalDecision.MANUAL_REVIEW
    assert len(bundle.manual_review_reasons) >= 1


def test_rejected_acceptance_stays_rejected_even_with_clean_materiality():
    bundle = run_audit_planning_pipeline(
        company_name="Quantum Cybernetics",
        materiality_request=valid_materiality_request("Quantum Cybernetics"),
    )

    assert bundle.final_decision == FinalDecision.REJECT
    assert bundle.evidence_data["independence_result"] == "CONFLICT_DETECTED"


def test_high_risk_acceptance_and_clean_materiality_routes_manual_review():
    bundle = run_audit_planning_pipeline(
        company_name="Apex Energy Group",
        materiality_request=valid_materiality_request("Apex Energy Group"),
    )

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert any("High engagement risk" in reason for reason in bundle.manual_review_reasons)