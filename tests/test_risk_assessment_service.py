import pytest
from pydantic import ValidationError

from schemas.decisions import FinalDecision
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
    RiskLevel,
    RiskType,
)
from services.risk_assessment_service import assess_audit_risks


def test_low_risk_assessment_continues():
    request = RiskAssessmentRequest(
        target_company="GreenLeaf Organics",
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

    result = assess_audit_risks(request)

    assert result.decision == FinalDecision.CONTINUE
    assert result.assessed_risks[0].risk_level == RiskLevel.LOW
    assert result.manual_review_reasons == []


def test_elevated_revenue_risk_routes_manual_review():
    request = RiskAssessmentRequest(
        target_company="Apex Energy Group",
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

    result = assess_audit_risks(request)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert result.assessed_risks[0].risk_level == RiskLevel.ELEVATED
    assert len(result.manual_review_reasons) == 1


def test_fraud_indicator_routes_manual_review():
    request = RiskAssessmentRequest(
        target_company="Example GmbH",
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

    result = assess_audit_risks(request)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert result.assessed_risks[0].risk_type == RiskType.FRAUD


def test_going_concern_indicator_routes_manual_review():
    request = RiskAssessmentRequest(
        target_company="Example GmbH",
        indicators=[
            RiskIndicator(
                area=FinancialStatementArea.GOING_CONCERN,
                assertion=AuditAssertion.VALUATION,
                description="Liquidity pressure indicates possible going concern risk.",
                likelihood=2,
                magnitude=2,
                going_concern_indicator=True,
            )
        ],
    )

    result = assess_audit_risks(request)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert result.assessed_risks[0].risk_type == RiskType.GOING_CONCERN


def test_invalid_likelihood_is_rejected():
    with pytest.raises(ValidationError):
        RiskIndicator(
            area=FinancialStatementArea.REVENUE,
            assertion=AuditAssertion.OCCURRENCE,
            description="Invalid likelihood.",
            likelihood=0,
            magnitude=3,
        )