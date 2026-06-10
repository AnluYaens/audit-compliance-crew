import pytest
from pydantic import ValidationError

from ai.research_agent import (
    MockResearchAgent,
    MockResearchScenario,
    get_mock_research_agent_output,
    mock_research_agent_payload,
)
from schemas.research_agent import EvidenceStatus, ResearchAgentOutput


def test_clean_mock_output_validates():
    output = MockResearchAgent().run(MockResearchScenario.CLEAN)

    assert isinstance(output, ResearchAgentOutput)
    assert output.human_review_required is False
    assert output.manual_review_reasons == []
    assert output.candidate_sources[0].source_id == "src-mock-1"
    assert output.extracted_evidence[0].status == EvidenceStatus.PRESENT


def test_missing_evidence_mock_requires_review():
    output = get_mock_research_agent_output("missing")

    assert output.human_review_required is True
    assert output.extracted_evidence[0].status == EvidenceStatus.MISSING
    assert any("missing support" in reason for reason in output.manual_review_reasons)
    assert any("Research missing evidence" in reason for reason in output.manual_review_reasons)


def test_contradictory_mock_requires_review():
    output = get_mock_research_agent_output(MockResearchScenario.CONTRADICTORY)

    assert output.human_review_required is True
    assert output.extracted_evidence[0].status == EvidenceStatus.CONTRADICTED
    assert any("CONTRADICTED" in reason for reason in output.manual_review_reasons)
    assert any("unresolved contradiction" in reason for reason in output.manual_review_reasons)


def test_low_confidence_mock_requires_review():
    output = get_mock_research_agent_output(MockResearchScenario.LOW_CONFIDENCE)

    assert output.human_review_required is True
    assert output.extracted_evidence[0].status == EvidenceStatus.LOW_CONFIDENCE
    assert any("below 0.75" in reason for reason in output.manual_review_reasons)


def test_tool_error_mock_requires_review():
    output = get_mock_research_agent_output(MockResearchScenario.TOOL_ERROR)

    assert output.human_review_required is True
    assert any("Research tool error" in reason for reason in output.manual_review_reasons)


def test_invalid_output_is_rejected():
    with pytest.raises(ValidationError) as exc_info:
        get_mock_research_agent_output(MockResearchScenario.INVALID)

    assert any(
        error["loc"] == ("candidate_sources", 0, "confidence")
        for error in exc_info.value.errors()
    )


def test_invalid_payload_cannot_be_manually_accepted_without_validation():
    payload = mock_research_agent_payload(MockResearchScenario.INVALID)

    with pytest.raises(ValidationError):
        ResearchAgentOutput.model_validate(payload)
