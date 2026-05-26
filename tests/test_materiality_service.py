import pytest
from pydantic import ValidationError

from schemas.decisions import FinalDecision
from schemas.materiality import MaterialityRequest
from services.materiality_service import calculate_materiality


def test_profit_before_tax_materiality_calculation_continues():
    request = MaterialityRequest(
        target_company="Example GmbH",
        benchmark_type="profit_before_tax",
        benchmark_amount=1_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Profit before tax is stable and appropriate for this prototype.",
    )

    result = calculate_materiality(request)

    assert result.decision == FinalDecision.CONTINUE
    assert result.overall_materiality == 50_000
    assert result.performance_materiality == 37_500
    assert result.clearly_trivial_threshold == 2_500
    assert result.manual_review_flags == []


def test_outside_percentage_range_routes_to_manual_review():
    request = MaterialityRequest(
        target_company="Example GmbH",
        benchmark_type="revenue",
        benchmark_amount=10_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Revenue benchmark selected for demonstration.",
    )

    result = calculate_materiality(request)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert len(result.manual_review_flags) == 1


def test_negative_benchmark_amount_is_rejected():
    with pytest.raises(ValidationError):
        MaterialityRequest(
            target_company="Example GmbH",
            benchmark_type="profit_before_tax",
            benchmark_amount=-1,
            overall_materiality_percentage=0.05,
            performance_materiality_percentage=0.75,
            clearly_trivial_percentage=0.05,
            rationale="Invalid negative benchmark.",
        )


def test_clearly_trivial_must_be_lower_than_performance_materiality():
    with pytest.raises(ValidationError):
        MaterialityRequest(
            target_company="Example GmbH",
            benchmark_type="profit_before_tax",
            benchmark_amount=1_000_000,
            overall_materiality_percentage=0.05,
            performance_materiality_percentage=0.50,
            clearly_trivial_percentage=0.50,
            rationale="Invalid threshold relationship.",
        )