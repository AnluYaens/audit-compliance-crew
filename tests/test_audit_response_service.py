from schemas.audit_response import AuditProcedureType, AuditResponseRequest
from schemas.decisions import FinalDecision
from schemas.risk_assessment import (
    AssessedRisk,
    AuditAssertion,
    FinancialStatementArea,
    RiskLevel,
    RiskType,
)
from services.audit_response_service import design_audit_response


def assessed_risk(
    area=FinancialStatementArea.CASH,
    assertion=AuditAssertion.EXISTENCE,
    risk_level=RiskLevel.LOW,
    risk_type=RiskType.NORMAL,
):
    return AssessedRisk(
        area=area,
        assertion=assertion,
        risk_level=risk_level,
        risk_type=risk_type,
        score=2,
        rationale="Test assessed risk.",
        manual_review_required=risk_level in {RiskLevel.ELEVATED, RiskLevel.SIGNIFICANT}
        or risk_type in {RiskType.FRAUD, RiskType.GOING_CONCERN},
    )


def test_low_cash_risk_gets_basic_response_and_continues():
    request = AuditResponseRequest(
        target_company="GreenLeaf Organics",
        assessed_risks=[assessed_risk()],
    )

    result = design_audit_response(request)

    assert result.decision == FinalDecision.CONTINUE
    assert result.procedures[0].procedure_type == AuditProcedureType.RECALCULATION
    assert result.manual_review_reasons == []


def test_elevated_revenue_risk_gets_enhanced_response_and_manual_review():
    request = AuditResponseRequest(
        target_company="Example GmbH",
        assessed_risks=[
            assessed_risk(
                area=FinancialStatementArea.REVENUE,
                assertion=AuditAssertion.OCCURRENCE,
                risk_level=RiskLevel.ELEVATED,
            )
        ],
    )

    result = design_audit_response(request)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert len(result.procedures) == 2
    assert any(
        procedure.procedure_type == AuditProcedureType.TEST_OF_CONTROLS
        for procedure in result.procedures
    )


def test_fraud_risk_gets_journal_entry_testing_and_manual_review():
    request = AuditResponseRequest(
        target_company="Example GmbH",
        assessed_risks=[
            assessed_risk(
                area=FinancialStatementArea.MANAGEMENT_OVERRIDE,
                assertion=AuditAssertion.PRESENTATION,
                risk_level=RiskLevel.MODERATE,
                risk_type=RiskType.FRAUD,
            )
        ],
    )

    result = design_audit_response(request)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert any(
        procedure.procedure_type == AuditProcedureType.JOURNAL_ENTRY_TESTING
        for procedure in result.procedures
    )


def test_going_concern_risk_routes_manual_review():
    request = AuditResponseRequest(
        target_company="Example GmbH",
        assessed_risks=[
            assessed_risk(
                area=FinancialStatementArea.GOING_CONCERN,
                assertion=AuditAssertion.VALUATION,
                risk_level=RiskLevel.MODERATE,
                risk_type=RiskType.GOING_CONCERN,
            )
        ],
    )

    result = design_audit_response(request)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert any("going concern" in reason.lower() for reason in result.manual_review_reasons)