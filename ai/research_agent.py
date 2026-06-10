from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from schemas.research_agent import (
    CitationType,
    EvidenceStatus,
    ResearchAgentOutput,
    ResearchTaskType,
)
from schemas.source_registry import SourceType


MOCK_RESEARCH_DATETIME = datetime(2026, 5, 31, tzinfo=timezone.utc)


class MockResearchScenario(str, Enum):
    CLEAN = "clean"
    MISSING = "missing"
    CONTRADICTORY = "contradictory"
    LOW_CONFIDENCE = "low_confidence"
    TOOL_ERROR = "tool_error"
    INVALID = "invalid"


def _base_citation(source_id: str = "src-mock-1") -> dict[str, Any]:
    return {
        "source_id": source_id,
        "citation_type": CitationType.URL,
        "locator": "https://example.com/mock-filing#note-1",
        "excerpt": "The audited financial statements cover the 2025 reporting period.",
        "retrieved_at": MOCK_RESEARCH_DATETIME,
    }


def _base_source() -> dict[str, Any]:
    return {
        "source_id": "src-mock-1",
        "title": "Example GmbH 2025 audited financial statements",
        "source_type": SourceType.AUDITED_FINANCIAL_STATEMENT,
        "url": "https://example.com/mock-filing",
        "publisher": "Example GmbH",
        "retrieval_date": MOCK_RESEARCH_DATETIME,
        "confidence": 0.95,
        "relevance": 0.91,
        "provenance_notes": "Deterministic mock source for research guardrail tests.",
        "citations": [_base_citation()],
    }


def _base_evidence() -> dict[str, Any]:
    return {
        "evidence_id": "ev-mock-1",
        "source_id": "src-mock-1",
        "claim": "The audited financial statements cover fiscal year 2025.",
        "extracted_value": "2025",
        "status": EvidenceStatus.PRESENT,
        "confidence": 0.93,
        "citations": [_base_citation()],
    }


def mock_research_agent_payload(
    scenario: MockResearchScenario | str = MockResearchScenario.CLEAN,
    *,
    run_id: str = "mock-run-001",
    target_company: str = "Example GmbH",
    research_question: str = "Find audited financial statement support for planning.",
) -> dict[str, Any]:
    scenario = MockResearchScenario(scenario)
    source = _base_source()
    evidence = _base_evidence()
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "task_type": ResearchTaskType.SOURCE_AND_EVIDENCE_RESEARCH,
        "run_id": run_id,
        "target_company": target_company,
        "research_question": research_question,
        "generated_at": MOCK_RESEARCH_DATETIME,
        "candidate_sources": [source],
        "extracted_evidence": [evidence],
        "missing_evidence": [],
        "contradictions": [],
        "tool_errors": [],
    }

    if scenario == MockResearchScenario.MISSING:
        evidence.update(
            {
                "status": EvidenceStatus.MISSING,
                "extracted_value": None,
                "confidence": 0.60,
                "citations": [],
                "missing_evidence": [
                    "No cited support was available for the requested filing period.",
                ],
                "notes": "Mock missing-evidence response.",
            },
        )
        payload["missing_evidence"] = [
            "Audited financial statement support for fiscal year 2025 is missing.",
        ]

    if scenario == MockResearchScenario.CONTRADICTORY:
        contradiction = (
            "Source states fiscal year 2025, but client records state fiscal year 2024."
        )
        evidence.update(
            {
                "status": EvidenceStatus.CONTRADICTED,
                "confidence": 0.82,
                "contradictions": [contradiction],
                "notes": "Mock contradictory-evidence response.",
            },
        )
        source["contradictions"] = [contradiction]
        payload["contradictions"] = [contradiction]

    if scenario == MockResearchScenario.LOW_CONFIDENCE:
        evidence.update(
            {
                "status": EvidenceStatus.LOW_CONFIDENCE,
                "confidence": 0.42,
                "notes": "Mock low-confidence extraction response.",
            },
        )
        source["confidence"] = 0.70

    if scenario == MockResearchScenario.TOOL_ERROR:
        payload["tool_errors"] = [
            "Mock retrieval tool failed before evidence could be refreshed.",
        ]

    if scenario == MockResearchScenario.INVALID:
        source["confidence"] = 1.20
        evidence["source_id"] = "unknown-source"

    return payload


def get_mock_research_agent_output(
    scenario: MockResearchScenario | str = MockResearchScenario.CLEAN,
    *,
    run_id: str = "mock-run-001",
    target_company: str = "Example GmbH",
    research_question: str = "Find audited financial statement support for planning.",
) -> ResearchAgentOutput:
    payload = mock_research_agent_payload(
        scenario,
        run_id=run_id,
        target_company=target_company,
        research_question=research_question,
    )
    return ResearchAgentOutput.model_validate(payload)


class MockResearchAgent:
    """Deterministic research agent for schema and guardrail tests."""

    def run(
        self,
        scenario: MockResearchScenario | str = MockResearchScenario.CLEAN,
        *,
        run_id: str = "mock-run-001",
        target_company: str = "Example GmbH",
        research_question: str = "Find audited financial statement support for planning.",
    ) -> ResearchAgentOutput:
        return get_mock_research_agent_output(
            scenario,
            run_id=run_id,
            target_company=target_company,
            research_question=research_question,
        )
