from __future__ import annotations

from schemas.decisions import FinalDecision
from schemas.materiality import BenchmarkType, MaterialityRequest, MaterialityResult


# Prototype policy ranges.
# These are configurable demo ranges, not hard-coded final firm policy.
SUGGESTED_MATERIALITY_RANGES: dict[BenchmarkType, tuple[float, float]] = {
    "profit_before_tax": (0.03, 0.10),
    "revenue": (0.005, 0.02),
    "total_assets": (0.005, 0.02),
    "equity": (0.01, 0.05),
    "expenses": (0.005, 0.02),
}


def round_money(value: float) -> float:
    return round(value, 2)


def calculate_materiality(request: MaterialityRequest) -> MaterialityResult:
    lower_bound, upper_bound = SUGGESTED_MATERIALITY_RANGES[request.benchmark_type]

    manual_review_flags: list[str] = []

    if not lower_bound <= request.overall_materiality_percentage <= upper_bound:
        manual_review_flags.append(
            (
                f"Selected overall materiality percentage "
                f"{request.overall_materiality_percentage:.4f} is outside the "
                f"prototype range for {request.benchmark_type}: "
                f"{lower_bound:.4f} to {upper_bound:.4f}."
            )
        )

    overall_materiality = round_money(
        request.benchmark_amount * request.overall_materiality_percentage
    )

    performance_materiality = round_money(
        overall_materiality * request.performance_materiality_percentage
    )

    clearly_trivial_threshold = round_money(
        overall_materiality * request.clearly_trivial_percentage
    )

    decision = (
        FinalDecision.MANUAL_REVIEW
        if manual_review_flags
        else FinalDecision.CONTINUE
    )

    return MaterialityResult(
        decision=decision,
        target_company=request.target_company,
        benchmark_type=request.benchmark_type,
        benchmark_amount=request.benchmark_amount,
        overall_materiality_percentage=request.overall_materiality_percentage,
        performance_materiality_percentage=request.performance_materiality_percentage,
        clearly_trivial_percentage=request.clearly_trivial_percentage,
        overall_materiality=overall_materiality,
        performance_materiality=performance_materiality,
        clearly_trivial_threshold=clearly_trivial_threshold,
        rationale=request.rationale,
        manual_review_flags=manual_review_flags,
    )
