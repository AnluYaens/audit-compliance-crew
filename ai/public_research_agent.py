from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from schemas.research_agent import CitationType, EvidenceStatus, ResearchAgentOutput, ResearchTaskType
from schemas.sandbox_verifier import (
    SafePublicSearchHintCandidate,
    SafePublicSearchHintSensitivity,
    SafePublicSearchHintType,
)
from schemas.source_registry import SourceType


PUBLIC_RESEARCH_DATETIME = datetime(2026, 7, 11, tzinfo=timezone.utc)
STALE_PUBLIC_SOURCE_DATETIME = datetime(2020, 1, 1, tzinfo=timezone.utc)


class PublicResearchScenario(str, Enum):
    CLEAN = "clean"
    NO_HINTS = "no_hints"
    WEAK_SOURCE = "weak_source"
    STALE_SOURCE = "stale_source"
    CONTRADICTORY_PUBLIC_EVIDENCE = "contradictory_public_evidence"
    SOURCE_ERROR = "source_error"


_SOURCE_TYPE_BY_HINT = {
    SafePublicSearchHintType.OFFICIAL_WEBSITE: SourceType.COMPANY_FILING,
    SafePublicSearchHintType.ANNUAL_REPORT: SourceType.AUDITED_FINANCIAL_STATEMENT,
    SafePublicSearchHintType.FINANCIAL_STATEMENT: SourceType.AUDITED_FINANCIAL_STATEMENT,
    SafePublicSearchHintType.SANCTIONS_LIST: SourceType.REGULATORY,
    SafePublicSearchHintType.REGULATOR_SOURCE: SourceType.REGULATORY,
    SafePublicSearchHintType.RELIABLE_NEWS: SourceType.NEWS_MEDIA,
}

_UNSAFE_HINT_MARKERS = {
    "client artifact",
    "confidential",
    "internal only",
    "internal-only",
    "raw client",
    "restricted",
}


def _validate_safe_hints(hints: list[SafePublicSearchHintCandidate]) -> None:
    if not isinstance(hints, list):
        raise TypeError("Public research hints must be provided as a list.")
    for index, hint in enumerate(hints):
        if not isinstance(hint, SafePublicSearchHintCandidate):
            raise TypeError(
                f"Public research hint at index {index} must be a SafePublicSearchHintCandidate."
            )
        if hint.sensitivity not in {
            SafePublicSearchHintSensitivity.PUBLIC,
            SafePublicSearchHintSensitivity.NON_SENSITIVE,
        }:
            raise ValueError(f"Public research hint at index {index} has an unsafe sensitivity.")
        if not isinstance(hint.hint_type, SafePublicSearchHintType):
            raise ValueError(f"Public research hint at index {index} has an invalid hint type.")
        if hint.human_review_recommended:
            raise ValueError(f"Public research hint at index {index} requires prior review.")
        if hint.confidence < 0.75:
            raise ValueError(f"Public research hint at index {index} has low safety confidence.")

        public_text = " ".join(
            (hint.hint_id, hint.hint_text, hint.safe_reason)
        ).casefold()
        if any(marker in public_text for marker in _UNSAFE_HINT_MARKERS):
            raise ValueError(
                f"Public research hint at index {index} contains unsafe content markers."
            )


def _base_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_type": ResearchTaskType.SOURCE_AND_EVIDENCE_RESEARCH,
        "run_id": "synthetic-public-research-run-001",
        "target_company": "Synthetic Public Entity",
        "research_question": "Collect synthetic public evidence for later reconciliation.",
        "generated_at": PUBLIC_RESEARCH_DATETIME,
        "candidate_sources": [],
        "extracted_evidence": [],
        "missing_evidence": [],
        "contradictions": [],
        "tool_errors": [],
    }


def _public_source_and_evidence(
    hint: SafePublicSearchHintCandidate,
    index: int,
    scenario: PublicResearchScenario,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_id = f"synthetic-public-source-{index}"
    locator = f"https://public-research.example.invalid/source-{index}#evidence"
    retrieval_date = PUBLIC_RESEARCH_DATETIME
    source_confidence = 0.94
    evidence_confidence = 0.92
    evidence_status = EvidenceStatus.PRESENT
    source_missing: list[str] = []
    evidence_missing: list[str] = []
    contradictions: list[str] = []
    notes = "Synthetic public evidence generated from a validated safe hint category."

    if scenario == PublicResearchScenario.WEAK_SOURCE:
        source_confidence = 0.45
        evidence_confidence = 0.42
        evidence_status = EvidenceStatus.LOW_CONFIDENCE
        notes = "Synthetic public source authority is weak and requires later review."
    elif scenario == PublicResearchScenario.STALE_SOURCE:
        retrieval_date = STALE_PUBLIC_SOURCE_DATETIME
        source_confidence = 0.68
        evidence_confidence = 0.64
        evidence_status = EvidenceStatus.LOW_CONFIDENCE
        source_missing = ["Synthetic public source is stale and lacks a current refresh."]
        evidence_missing = ["Current synthetic public support is unavailable."]
        notes = "Synthetic public evidence is outdated and requires later review."
    elif scenario == PublicResearchScenario.CONTRADICTORY_PUBLIC_EVIDENCE:
        evidence_status = EvidenceStatus.CONTRADICTED
        contradictions = ["Synthetic public sources report conflicting public reporting periods."]
        notes = "Synthetic public contradiction is preserved for later reconciliation."

    citation = {
        "source_id": source_id,
        "citation_type": CitationType.URL,
        "locator": locator,
        "excerpt": "Synthetic public material reports a public filing period.",
        "retrieved_at": retrieval_date,
    }
    source = {
        "source_id": source_id,
        "title": f"Synthetic public {hint.hint_type.value.replace('_', ' ')} source {index}",
        "source_type": _SOURCE_TYPE_BY_HINT[hint.hint_type],
        "url": f"https://public-research.example.invalid/source-{index}",
        "publisher": "Synthetic Public Publisher",
        "retrieval_date": retrieval_date,
        "confidence": source_confidence,
        "relevance": 0.90,
        "provenance_notes": "Derived only from a validated safe public hint category.",
        "missing_evidence": source_missing,
        "contradictions": contradictions,
        "citations": [citation],
    }
    evidence = {
        "evidence_id": f"synthetic-public-evidence-{index}",
        "source_id": source_id,
        "claim": "Synthetic public material contains a public reporting-period statement.",
        "extracted_value": "Synthetic public reporting period",
        "status": evidence_status,
        "confidence": evidence_confidence,
        "citations": [citation],
        "missing_evidence": evidence_missing,
        "contradictions": contradictions,
        "notes": notes,
    }
    return source, evidence


def run_public_research_mvp(
    hints: list[SafePublicSearchHintCandidate],
    scenario: PublicResearchScenario | str = PublicResearchScenario.CLEAN,
) -> ResearchAgentOutput:
    """Return deterministic, non-decisional public research output."""
    _validate_safe_hints(hints)
    scenario = PublicResearchScenario(scenario)
    payload = _base_payload()

    if scenario == PublicResearchScenario.SOURCE_ERROR:
        payload["tool_errors"] = [
            "Synthetic public source retrieval failed and requires later review."
        ]
        return ResearchAgentOutput.model_validate(payload)
    if scenario == PublicResearchScenario.NO_HINTS or not hints:
        payload["missing_evidence"] = [
            "No validated safe public search hints were available for research."
        ]
        return ResearchAgentOutput.model_validate(payload)

    for index, hint in enumerate(hints, start=1):
        source, evidence = _public_source_and_evidence(hint, index, scenario)
        payload["candidate_sources"].append(source)
        payload["extracted_evidence"].append(evidence)

    if scenario == PublicResearchScenario.CONTRADICTORY_PUBLIC_EVIDENCE:
        payload["contradictions"] = [
            "Synthetic public sources report conflicting public reporting periods."
        ]
    return ResearchAgentOutput.model_validate(payload)


class PublicResearchAgent:
    """Deterministic public research MVP wrapper."""

    def run(
        self,
        hints: list[SafePublicSearchHintCandidate],
        scenario: PublicResearchScenario | str = PublicResearchScenario.CLEAN,
    ) -> ResearchAgentOutput:
        return run_public_research_mvp(hints, scenario)
