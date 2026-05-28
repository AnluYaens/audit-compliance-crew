from schemas.audit_response import AuditProcedureType
from schemas.decisions import FinalDecision
from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
)
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


def low_risk_assessment_request(company_name: str = "GreenLeaf Organics") -> RiskAssessmentRequest:
    return RiskAssessmentRequest(
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


def elevated_risk_assessment_request(company_name: str = "GreenLeaf Organics") -> RiskAssessmentRequest:
    return RiskAssessmentRequest(
        target_company=company_name,
        indicators=[
            RiskIndicator(
                area=FinancialStatementArea.REVENUE,
                assertion=AuditAssertion.OCCURRENCE,
                description="Revenue growth is unusual compared with industry expectations.",
                likelihood=4,
                magnitude=4,
            )
        ],
    )


def fraud_risk_assessment_request(company_name: str = "GreenLeaf Organics") -> RiskAssessmentRequest:
    return RiskAssessmentRequest(
        target_company=company_name,
        indicators=[
            RiskIndicator(
                area=FinancialStatementArea.MANAGEMENT_OVERRIDE,
                assertion=AuditAssertion.PRESENTATION,
                description="Management override risk indicator identified.",
                likelihood=2,
                magnitude=2,
                fraud_indicator=True,
            )
        ],
    )


def test_clean_acceptance_clean_materiality_low_risk_continue():
    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=valid_materiality_request(),
        risk_assessment_request=low_risk_assessment_request(),
    )

    assert bundle.final_decision == FinalDecision.CONTINUE
    assert bundle.evidence_data["materiality_result"]["decision"] == FinalDecision.CONTINUE
    assert bundle.evidence_data["risk_assessment_result"]["decision"] == FinalDecision.CONTINUE
    assert bundle.evidence_data["audit_response_result"]["decision"] == FinalDecision.CONTINUE
    assert len(bundle.evidence_data["audit_response_result"]["procedures"]) >= 1


def test_clean_acceptance_flagged_materiality_routes_manual_review():
    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=flagged_materiality_request(),
        risk_assessment_request=low_risk_assessment_request(),
    )

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert bundle.evidence_data["materiality_result"]["decision"] == FinalDecision.MANUAL_REVIEW
    assert "audit_response_result" in bundle.evidence_data


def test_clean_acceptance_elevated_risk_routes_manual_review_with_enhanced_response():
    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=valid_materiality_request(),
        risk_assessment_request=elevated_risk_assessment_request(),
    )

    procedures = bundle.evidence_data["audit_response_result"]["procedures"]

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert bundle.evidence_data["risk_assessment_result"]["decision"] == FinalDecision.MANUAL_REVIEW
    assert bundle.evidence_data["audit_response_result"]["decision"] == FinalDecision.MANUAL_REVIEW
    assert any(
        procedure["procedure_type"] == AuditProcedureType.TEST_OF_CONTROLS
        for procedure in procedures
    )


def test_fraud_risk_routes_manual_review_with_journal_entry_testing():
    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=valid_materiality_request(),
        risk_assessment_request=fraud_risk_assessment_request(),
    )

    procedures = bundle.evidence_data["audit_response_result"]["procedures"]

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert any("FRAUD" in reason for reason in bundle.manual_review_reasons)
    assert any(
        procedure["procedure_type"] == AuditProcedureType.JOURNAL_ENTRY_TESTING
        for procedure in procedures
    )


def test_rejected_acceptance_overrides_clean_planning_modules():
    bundle = run_audit_planning_pipeline(
        company_name="Quantum Cybernetics",
        materiality_request=valid_materiality_request("Quantum Cybernetics"),
        risk_assessment_request=low_risk_assessment_request("Quantum Cybernetics"),
    )

    assert bundle.final_decision == FinalDecision.REJECT
    assert bundle.evidence_data["independence_result"] == "CONFLICT_DETECTED"
    assert "audit_response_result" in bundle.evidence_data