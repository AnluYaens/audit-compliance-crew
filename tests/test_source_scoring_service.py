from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from schemas.decisions import FinalDecision
from schemas.source_registry import SourceRecord, SourceType
from services.source_scoring_service import score_source


SCORING_DATETIME = datetime(2026, 5, 31, tzinfo=timezone.utc)


def reliable_source() -> SourceRecord:
    return SourceRecord(
        url="https://example.com/regulatory-filing",
        source_type=SourceType.REGULATORY,
        publisher="Example Regulator",
        retrieval_date=datetime(2026, 5, 20, tzinfo=timezone.utc),
        confidence=0.95,
        freshness_days=90,
        relevance=0.9,
        notes="Regulatory filing metadata captured for deterministic scoring.",
    )


def test_reliable_source_returns_continue():
    result = score_source(
        reliable_source(),
        scoring_datetime=SCORING_DATETIME,
    )

    assert result.decision == FinalDecision.CONTINUE
    assert result.status == "SUCCESS"
    assert result.manual_review_reasons == []
    assert result.scores.authority_score == 1.0


def test_missing_source_identity_returns_manual_review():
    source = reliable_source().model_copy(update={"url": None, "identifier": None})

    result = score_source(source, scoring_datetime=SCORING_DATETIME)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert result.status == "REVIEW_REQUIRED"
    assert "Source identity is missing." in result.manual_review_reasons


def test_stale_source_returns_manual_review():
    source = reliable_source().model_copy(
        update={
            "retrieval_date": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "freshness_days": 90,
        }
    )

    result = score_source(source, scoring_datetime=SCORING_DATETIME)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert any("Source is stale" in reason for reason in result.manual_review_reasons)


def test_low_confidence_source_returns_manual_review():
    source = reliable_source().model_copy(update={"confidence": 0.5})

    result = score_source(source, scoring_datetime=SCORING_DATETIME)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert any("Source confidence" in reason for reason in result.manual_review_reasons)


def test_contradictory_source_returns_manual_review():
    source = reliable_source().model_copy(
        update={"contradiction_flags": ["Conflicts with audited trial balance."]}
    )

    result = score_source(source, scoring_datetime=SCORING_DATETIME)

    assert result.decision == FinalDecision.MANUAL_REVIEW
    assert result.scores.contradiction_flag is True
    assert "Source has unresolved contradiction flags." in result.manual_review_reasons


def test_invalid_schema_input_fails_validation():
    with pytest.raises(ValidationError):
        SourceRecord(
            identifier="INVALID-CONFIDENCE-SOURCE",
            source_type=SourceType.COMPANY_FILING,
            publisher="Example Publisher",
            retrieval_date=datetime(2026, 5, 20, tzinfo=timezone.utc),
            confidence=1.25,
            freshness_days=90,
            relevance=0.9,
        )
