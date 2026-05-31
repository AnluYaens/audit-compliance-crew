from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
)
from services.audit_planning_pipeline_service import run_audit_planning_pipeline
from services.planning_memo_service import generate_planning_memo


def test_planning_memo_contains_core_sections():
    company_name = "GreenLeaf Organics"

    materiality_request = MaterialityRequest(
        target_company=company_name,
        benchmark_type="profit_before_tax",
        benchmark_amount=1_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Prototype planning materiality calculation.",
    )

    risk_assessment_request = RiskAssessmentRequest(
        target_company=company_name,
        indicators=[
            RiskIndicator(
                area=FinancialStatementArea.CASH,
                assertion=AuditAssertion.EXISTENCE,
                description="Cash balance is simple and reconciled.",
                likelihood=1,
                magnitude=2,
            )
        ],
    )

    bundle = run_audit_planning_pipeline(
        company_name=company_name,
        materiality_request=materiality_request,
        risk_assessment_request=risk_assessment_request,
    )

    memo = generate_planning_memo(bundle)

    assert "# Audit Planning Memo" in memo
    assert "Engagement Overview" in memo
    assert "Governance Note" in memo
    assert "Materiality Summary" in memo
    assert "Risk Assessment Summary" in memo
    assert "Audit Response Plan" in memo
    assert "GreenLeaf Organics" in memo
    assert bundle.final_decision.value in memo


def test_planning_memo_states_llm_did_not_decide():
    company_name = "GreenLeaf Organics"

    materiality_request = MaterialityRequest(
        target_company=company_name,
        benchmark_type="profit_before_tax",
        benchmark_amount=1_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Prototype planning materiality calculation.",
    )

    risk_assessment_request = RiskAssessmentRequest(
        target_company=company_name,
        indicators=[
            RiskIndicator(
                area=FinancialStatementArea.CASH,
                assertion=AuditAssertion.EXISTENCE,
                description="Cash balance is simple and reconciled.",
                likelihood=1,
                magnitude=2,
            )
        ],
    )

    bundle = run_audit_planning_pipeline(
        company_name=company_name,
        materiality_request=materiality_request,
        risk_assessment_request=risk_assessment_request,
    )

    memo = generate_planning_memo(bundle)

    assert "not by an LLM" in memo
    assert "does not override compliance decisions" in memo