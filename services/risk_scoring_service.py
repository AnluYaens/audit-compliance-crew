from __future__ import annotations

from schemas.contracts import (
    RiskEvaluationInput,
    RiskInputSnapshot,
    RiskScoringOutput,
)
from services.compliance_common import (
    ALLOWED_RISK_VALUES,
    RISK_VALUES,
    contract_json,
    invalid_value_label,
    normalize_risk_state,
)


def calculate_weighted_risk_score_service(
    industry_level: str,
    geography_level: str,
    financial_level: str,
) -> str:
    """
    Runs the deterministic weighted risk equation framework.
    Inputs must map to 'Low', 'Medium', or 'High'; all other inputs fail closed.
    """
    inputs = RiskInputSnapshot(
        industry=normalize_risk_state(industry_level),
        geography=normalize_risk_state(geography_level),
        financial=normalize_risk_state(financial_level),
    )

    invalid_inputs = {
        key: invalid_value_label(value)
        for key, value in {
            "industry": industry_level,
            "geography": geography_level,
            "financial": financial_level,
        }.items()
        if getattr(inputs, key) == "INVALID_INPUT"
    }

    if invalid_inputs:
        payload = RiskScoringOutput(
            status="INVALID_INPUT",
            decision="MANUAL_REVIEW",
            is_blocker=True,
            severity="HIGH",
            message="Risk levels must be exactly High, Medium, or Low.",
            inputs=inputs,
            invalid_inputs=invalid_inputs,
            allowed_values=ALLOWED_RISK_VALUES,
        )
        return contract_json(payload)

    try:
        validated = RiskEvaluationInput(
            industry_level=inputs.industry,
            geography_level=inputs.geography,
            financial_level=inputs.financial,
        )

        score = (
            RISK_VALUES[validated.industry_level] * 0.5
            + RISK_VALUES[validated.geography_level] * 0.3
            + RISK_VALUES[validated.financial_level] * 0.2
        )

        if score < 1.8:
            classification = "Low Risk Engagement"
        elif score <= 2.5:
            classification = "Moderate Risk Engagement"
        else:
            classification = "High Risk Engagement (Requires Enhanced Due Diligence)"

        payload = RiskScoringOutput(
            status="SUCCESS",
            decision="CONTINUE",
            is_blocker=False,
            severity="HIGH" if score > 2.5 else "MEDIUM" if score >= 1.8 else "LOW",
            raw_score=round(score, 2),
            classification=classification,
            inputs=inputs,
            allowed_values=ALLOWED_RISK_VALUES,
        )
        return contract_json(payload)

    except Exception as exc:
        payload = RiskScoringOutput(
            status="INVALID_INPUT",
            decision="MANUAL_REVIEW",
            is_blocker=True,
            severity="HIGH",
            message=f"Risk scoring failed closed: {exc}",
            inputs=inputs,
            invalid_inputs={
                "industry": invalid_value_label(industry_level),
                "geography": invalid_value_label(geography_level),
                "financial": invalid_value_label(financial_level),
            },
            allowed_values=ALLOWED_RISK_VALUES,
        )
        return contract_json(payload)
