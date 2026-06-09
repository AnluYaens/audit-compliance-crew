from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from schemas.research_agent import (
    CandidateSource,
    CitationType,
    EvidenceStatus,
    ExtractedEvidence,
    ResearchAgentOutput,
    ResearchCitation,
    ResearchTaskType,
)
from schemas.source_registry import SourceType


RESEARCH_DATETIME = datetime(2026, 5, 31, tzinfo=timezone.utc)


def citation(source_id: str = "src-1") -> ResearchCitation:
    return ResearchCitation(
        source_id=source_id,
        citation_type=CitationType.URL,
        locator="https://example.com/filing#directors-report",
        excerpt="Management disclosed the current-year audit engagement context.",
        retrieved_at=RESEARCH_DATETIME,
    )


def candidate_source() -> CandidateSource:
    return CandidateSource(
        source_id="src-1",
        title="Example GmbH 2025 audited financial statements",
        source_type=SourceType.AUDITED_FINANCIAL_STATEMENT,
        url="https://example.com/filing",
        publisher="Example GmbH",
        retrieval_date=RESEARCH_DATETIME,
        confidence=0.95,
        relevance=0.90,
        citations=[citation()],
    )


def extracted_evidence() -> ExtractedEvidence:
    return ExtractedEvidence(
        evidence_id="ev-1",
        source_id="src-1",
        claim="The audited financial statements cover fiscal year 2025.",
        extracted_value="2025",
        confidence=0.92,
        citations=[citation()],
    )


def valid_research_output() -> ResearchAgentOutput:
    return ResearchAgentOutput(
        task_type=ResearchTaskType.SOURCE_AND_EVIDENCE_RESEARCH,
        run_id="run-123",
        target_company="Example GmbH",
        research_question="Find audited financial statement support for planning.",
        generated_at=RESEARCH_DATETIME,
        candidate_sources=[candidate_source()],
        extracted_evidence=[extracted_evidence()],
    )


def test_valid_research_output_validates():
    output = valid_research_output()

    assert output.human_review_required is False
    assert output.manual_review_reasons == []
    assert output.extracted_evidence[0].citations[0].source_id == "src-1"


def test_missing_citation_requires_review():
    output = valid_research_output().model_copy(
        update={
            "extracted_evidence": [
                extracted_evidence().model_copy(update={"citations": []}),
            ],
        },
    )

    assert output.human_review_required is True
    assert "Extracted evidence ev-1 has no citations." in output.manual_review_reasons


def test_final_decision_field_is_not_accepted():
    payload = {
        "task_type": ResearchTaskType.SOURCE_AND_EVIDENCE_RESEARCH,
        "run_id": "run-123",
        "target_company": "Example GmbH",
        "research_question": "Find audited financial statement support for planning.",
        "generated_at": RESEARCH_DATETIME,
        "candidate_sources": [candidate_source()],
        "extracted_evidence": [extracted_evidence()],
        "final_decision": "CONTINUE",
    }

    with pytest.raises(ValidationError) as exc_info:
        ResearchAgentOutput.model_validate(payload)

    assert any(error["loc"] == ("final_decision",) for error in exc_info.value.errors())


def test_contradiction_requires_review():
    output = valid_research_output().model_copy(
        update={
            "extracted_evidence": [
                extracted_evidence().model_copy(
                    update={
                        "status": EvidenceStatus.CONTRADICTED,
                        "contradictions": [
                            "The source conflicts with the client-provided reporting period.",
                        ],
                    },
                ),
            ],
        },
    )

    assert output.human_review_required is True
    assert any("CONTRADICTED" in reason for reason in output.manual_review_reasons)
    assert any("unresolved contradiction" in reason for reason in output.manual_review_reasons)
