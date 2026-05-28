from __future__ import annotations

from schemas.decisions import FinalDecision
from schemas.risk_assessment import (
    AssessedRisk,
    RiskAssessmentRequest,
    RiskAssessmentResult,
    RiskIndicator,
    RiskLevel,
    RiskType,
)


def calculate_risk_level(score: int) -> RiskLevel:
    if score <= 5:
        return RiskLevel.LOW
    if score <= 10:
        return RiskLevel.MODERATE
    if score <= 16:
        return RiskLevel.ELEVATED
    return RiskLevel.SIGNIFICANT


def determine_risk_type(indicator: RiskIndicator) -> RiskType:
    if indicator.fraud_indicator:
        return RiskType.FRAUD

    if indicator.going_concern_indicator:
        return RiskType.GOING_CONCERN

    return RiskType.NORMAL


def assess_single_risk(indicator: RiskIndicator) -> AssessedRisk:
    score = indicator.likelihood * indicator.magnitude
    risk_level = calculate_risk_level(score)
    risk_type = determine_risk_type(indicator)

    manual_review_required = (
        risk_level in {RiskLevel.ELEVATED, RiskLevel.SIGNIFICANT}
        or risk_type in {RiskType.FRAUD, RiskType.GOING_CONCERN}
    )

    rationale = (
        f"{indicator.description} "
        f"Likelihood={indicator.likelihood}, magnitude={indicator.magnitude}, "
        f"score={score}, risk_level={risk_level.value}."
    )

    if risk_type == RiskType.FRAUD:
        rationale += " Fraud indicator identified."

    if risk_type == RiskType.GOING_CONCERN:
        rationale += " Going concern indicator identified."

    return AssessedRisk(
        area=indicator.area,
        assertion=indicator.assertion,
        risk_level=risk_level,
        risk_type=risk_type,
        score=score,
        rationale=rationale,
        manual_review_required=manual_review_required,
    )


def assess_audit_risks(request: RiskAssessmentRequest) -> RiskAssessmentResult:
    assessed_risks = [
        assess_single_risk(indicator)
        for indicator in request.indicators
    ]

    manual_review_reasons = [
        (
            f"{risk.area.value} / {risk.assertion.value}: "
            f"{risk.risk_level.value} {risk.risk_type.value} risk requires review."
        )
        for risk in assessed_risks
        if risk.manual_review_required
    ]

    decision = (
        FinalDecision.MANUAL_REVIEW
        if manual_review_reasons
        else FinalDecision.CONTINUE
    )

    return RiskAssessmentResult(
        decision=decision,
        target_company=request.target_company,
        assessed_risks=assessed_risks,
        manual_review_reasons=manual_review_reasons,
    )