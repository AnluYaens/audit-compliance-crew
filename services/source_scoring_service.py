from __future__ import annotations

from datetime import datetime, timezone

from schemas.decisions import FinalDecision
from schemas.source_registry import (
    SourceRecord,
    SourceRegistry,
    SourceRegistryScoringResult,
    SourceScoreBreakdown,
    SourceScoringResult,
    SourceType,
)


AUTHORITY_SCORES: dict[SourceType, float] = {
    SourceType.REGULATORY: 1.0,
    SourceType.GOVERNMENT_REGISTRY: 0.95,
    SourceType.AUDITED_FINANCIAL_STATEMENT: 0.95,
    SourceType.COMPANY_FILING: 0.9,
    SourceType.INTERNAL_SYSTEM: 0.85,
    SourceType.THIRD_PARTY_DATABASE: 0.75,
    SourceType.NEWS_MEDIA: 0.55,
    SourceType.OTHER: 0.4,
}

MIN_AUTHORITY_SCORE = 0.7
MIN_RELEVANCE_SCORE = 0.7
MIN_CONFIDENCE_SCORE = 0.75
MIN_TOTAL_SCORE = 0.8


def _scoring_datetime(scoring_datetime: datetime | None) -> datetime:
    if scoring_datetime is not None:
        return scoring_datetime
    return datetime.now(timezone.utc)


def _age_days(source: SourceRecord, scoring_datetime: datetime) -> int:
    retrieved_at = source.retrieval_date
    if retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)

    scoring_at = scoring_datetime
    if scoring_at.tzinfo is None:
        scoring_at = scoring_at.replace(tzinfo=timezone.utc)

    return (scoring_at.date() - retrieved_at.date()).days


def _freshness_score(age_days: int, freshness_days: int) -> float:
    if age_days < 0:
        return 0.0

    if age_days <= freshness_days:
        return 1.0

    if age_days == 0:
        return 1.0

    return round(max(0.0, min(1.0, freshness_days / age_days)), 4)


def _completeness_score(source: SourceRecord) -> float:
    completeness_checks = [
        bool(source.url or source.identifier),
        source.publisher is not None,
        source.source_type is not None,
        source.retrieval_date is not None,
        source.confidence is not None,
        source.freshness_days is not None,
        source.relevance is not None,
    ]
    completed = sum(1 for check in completeness_checks if check)
    return round(completed / len(completeness_checks), 4)


def _total_score(scores: SourceScoreBreakdown) -> float:
    if scores.contradiction_flag:
        return 0.0

    total = (
        scores.authority_score * 0.25
        + scores.relevance_score * 0.25
        + scores.freshness_score * 0.2
        + scores.completeness_score * 0.15
        + scores.confidence_score * 0.15
    )
    return round(total, 4)


def score_source(
    source: SourceRecord,
    scoring_datetime: datetime | None = None,
) -> SourceScoringResult:
    """
    Deterministically scores one source record and fails closed to MANUAL_REVIEW.

    This service validates provenance metadata only. It does not acquire evidence,
    call live sources, or let an agent approve source reliability.
    """
    scoring_at = _scoring_datetime(scoring_datetime)
    age_days = _age_days(source, scoring_at)

    authority_score = AUTHORITY_SCORES[source.source_type]
    freshness_score = _freshness_score(age_days, source.freshness_days)

    scores = SourceScoreBreakdown(
        authority_score=authority_score,
        relevance_score=source.relevance,
        freshness_score=freshness_score,
        completeness_score=_completeness_score(source),
        confidence_score=source.confidence,
        contradiction_flag=bool(source.contradiction_flags),
    )

    total_score = _total_score(scores)
    manual_review_reasons: list[str] = []

    if not source.url and not source.identifier:
        manual_review_reasons.append("Source identity is missing.")

    if source.publisher is None:
        manual_review_reasons.append("Source publisher is missing.")

    if authority_score < MIN_AUTHORITY_SCORE:
        manual_review_reasons.append(
            f"Source authority score {authority_score:.2f} is below {MIN_AUTHORITY_SCORE:.2f}."
        )

    if source.relevance < MIN_RELEVANCE_SCORE:
        manual_review_reasons.append(
            f"Source relevance score {source.relevance:.2f} is below {MIN_RELEVANCE_SCORE:.2f}."
        )

    if source.confidence < MIN_CONFIDENCE_SCORE:
        manual_review_reasons.append(
            f"Source confidence {source.confidence:.2f} is below {MIN_CONFIDENCE_SCORE:.2f}."
        )

    if age_days < 0:
        manual_review_reasons.append("Source retrieval date is in the future.")
    elif age_days > source.freshness_days:
        manual_review_reasons.append(
            (
                f"Source is stale: age {age_days} days exceeds "
                f"freshness threshold {source.freshness_days} days."
            )
        )

    if source.contradiction_flags:
        manual_review_reasons.append("Source has unresolved contradiction flags.")

    if total_score < MIN_TOTAL_SCORE and not manual_review_reasons:
        manual_review_reasons.append(
            f"Source total score {total_score:.2f} is below {MIN_TOTAL_SCORE:.2f}."
        )

    decision = (
        FinalDecision.MANUAL_REVIEW
        if manual_review_reasons
        else FinalDecision.CONTINUE
    )

    return SourceScoringResult(
        status="REVIEW_REQUIRED" if manual_review_reasons else "SUCCESS",
        decision=decision,
        source=source,
        scores=scores,
        total_score=total_score,
        manual_review_reasons=manual_review_reasons,
    )


def score_source_registry(
    registry: SourceRegistry,
    scoring_datetime: datetime | None = None,
) -> SourceRegistryScoringResult:
    source_results = [
        score_source(source, scoring_datetime=scoring_datetime)
        for source in registry.records
    ]

    manual_review_reasons = [
        f"Source {index + 1}: {reason}"
        for index, result in enumerate(source_results)
        for reason in result.manual_review_reasons
    ]

    if not registry.records:
        manual_review_reasons.append("Source registry contains no source records.")

    decision = (
        FinalDecision.MANUAL_REVIEW
        if manual_review_reasons
        else FinalDecision.CONTINUE
    )

    return SourceRegistryScoringResult(
        status="REVIEW_REQUIRED" if manual_review_reasons else "SUCCESS",
        decision=decision,
        run_id=registry.run_id,
        target_company=registry.target_company,
        source_results=source_results,
        manual_review_reasons=manual_review_reasons,
    )
