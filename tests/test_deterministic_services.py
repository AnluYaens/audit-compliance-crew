import json

from services.risk_scoring_service import calculate_weighted_risk_score_service


def test_risk_service_success_low_risk():
    raw = calculate_weighted_risk_score_service(
        industry_level="Low",
        geography_level="Low",
        financial_level="Low",
    )

    payload = json.loads(raw)

    assert payload["status"] == "SUCCESS"
    assert payload["decision"] == "CONTINUE"
    assert payload["raw_score"] == 1.0
    assert payload["classification"] == "Low Risk Engagement"


def test_risk_service_invalid_input_fails_closed():
    raw = calculate_weighted_risk_score_service(
        industry_level="Unknown",
        geography_level="Low",
        financial_level="Low",
    )

    payload = json.loads(raw)

    assert payload["status"] == "INVALID_INPUT"
    assert payload["decision"] == "MANUAL_REVIEW"
    assert payload["is_blocker"] is True
    assert "industry" in payload["invalid_inputs"]
