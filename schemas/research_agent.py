from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import Field, computed_field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel
from schemas.source_registry import SourceType


LOW_CONFIDENCE_THRESHOLD = 0.75


class ResearchTaskType(str, Enum):
    SOURCE_DISCOVERY = "SOURCE_DISCOVERY"
    EVIDENCE_EXTRACTION = "EVIDENCE_EXTRACTION"
    SOURCE_AND_EVIDENCE_RESEARCH = "SOURCE_AND_EVIDENCE_RESEARCH"


class CitationType(str, Enum):
    URL = "URL"
    DOCUMENT = "DOCUMENT"
    REGISTRY_RECORD = "REGISTRY_RECORD"
    INTERNAL_RECORD = "INTERNAL_RECORD"
    OTHER = "OTHER"


class EvidenceStatus(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    CONTRADICTED = "CONTRADICTED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class ResearchCitation(StrictContractModel):
    source_id: NonEmptyStr = Field(
        description="Agent-assigned source identifier referenced by the cited claim.",
    )
    citation_type: CitationType = Field(description="Structured citation category.")
    locator: NonEmptyStr = Field(
        description="URL, page, paragraph, section, record ID, or other precise locator.",
    )
    excerpt: NonEmptyStr | None = Field(
        default=None,
        description="Short supporting excerpt or extract when available.",
    )
    retrieved_at: datetime | None = Field(
        default=None,
        description="When the cited material was retrieved or inspected.",
    )


class CandidateSource(StrictContractModel):
    source_id: NonEmptyStr = Field(description="Agent-assigned stable source identifier.")
    title: NonEmptyStr = Field(description="Human-readable source title.")
    source_type: SourceType = Field(description="Proposed deterministic source category.")
    url: NonEmptyStr | None = Field(
        default=None,
        description="Source URL when the source is addressable on the web.",
    )
    identifier: NonEmptyStr | None = Field(
        default=None,
        description="Stable non-URL source identifier, such as a filing ID or document ID.",
    )
    publisher: NonEmptyStr | None = Field(
        default=None,
        description="Source publisher, authority, or system owner.",
    )
    retrieval_date: datetime | None = Field(
        default=None,
        description="When the candidate source was found or inspected.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Agent confidence that this source is relevant and correctly identified.",
    )
    relevance: float = Field(
        ge=0.0,
        le=1.0,
        description="Agent estimate of source relevance from zero to one.",
    )
    provenance_notes: NonEmptyStr | None = Field(
        default=None,
        description="Structured notes about how the source was discovered.",
    )
    missing_evidence: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Expected source metadata the agent could not verify.",
    )
    contradictions: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Unresolved contradictions or inconsistencies for this source.",
    )
    citations: list[ResearchCitation] = Field(
        default_factory=list,
        description="Citations supporting source identity, publisher, or relevance.",
    )

    @model_validator(mode="after")
    def require_source_identity(self) -> "CandidateSource":
        if self.url is None and self.identifier is None:
            raise ValueError("Candidate sources require either url or identifier.")
        return self

    @computed_field
    @property
    def manual_review_reasons(self) -> list[str]:
        reasons: list[str] = []

        if not self.citations:
            reasons.append(f"Candidate source {self.source_id} has no citations.")

        if self.confidence < LOW_CONFIDENCE_THRESHOLD:
            reasons.append(
                f"Candidate source {self.source_id} confidence {self.confidence:.2f} "
                f"is below {LOW_CONFIDENCE_THRESHOLD:.2f}."
            )

        for missing in self.missing_evidence:
            reasons.append(f"Candidate source {self.source_id} missing evidence: {missing}.")

        for contradiction in self.contradictions:
            reasons.append(
                f"Candidate source {self.source_id} has unresolved contradiction: "
                f"{contradiction}."
            )

        return reasons

    @computed_field
    @property
    def human_review_required(self) -> bool:
        return bool(self.manual_review_reasons)


class ExtractedEvidence(StrictContractModel):
    evidence_id: NonEmptyStr = Field(description="Agent-assigned evidence item identifier.")
    source_id: NonEmptyStr = Field(description="Candidate source identifier this evidence came from.")
    claim: NonEmptyStr = Field(description="Structured factual assertion extracted by the agent.")
    extracted_value: NonEmptyStr | None = Field(
        default=None,
        description="Normalized extracted value when the evidence supports a specific value.",
    )
    status: EvidenceStatus = Field(
        default=EvidenceStatus.PRESENT,
        description="Whether the evidence was found, missing, contradicted, or low-confidence.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Agent confidence in the extraction from zero to one.",
    )
    citations: list[ResearchCitation] = Field(
        default_factory=list,
        description="Citations supporting the extracted claim.",
    )
    missing_evidence: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Required supporting facts or citations the agent could not find.",
    )
    contradictions: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Unresolved evidence contradictions discovered by the agent.",
    )
    notes: NonEmptyStr | None = Field(
        default=None,
        description="Optional structured extraction note for auditor review.",
    )

    @model_validator(mode="after")
    def require_missing_reason_for_missing_status(self) -> "ExtractedEvidence":
        if self.status == EvidenceStatus.MISSING and not self.missing_evidence:
            raise ValueError("Missing evidence items require missing_evidence details.")
        return self

    @computed_field
    @property
    def manual_review_reasons(self) -> list[str]:
        reasons: list[str] = []

        if not self.citations:
            reasons.append(f"Extracted evidence {self.evidence_id} has no citations.")

        if self.status in {
            EvidenceStatus.MISSING,
            EvidenceStatus.CONTRADICTED,
            EvidenceStatus.LOW_CONFIDENCE,
        }:
            reasons.append(
                f"Extracted evidence {self.evidence_id} status requires review: "
                f"{self.status.value}."
            )

        if self.confidence < LOW_CONFIDENCE_THRESHOLD:
            reasons.append(
                f"Extracted evidence {self.evidence_id} confidence {self.confidence:.2f} "
                f"is below {LOW_CONFIDENCE_THRESHOLD:.2f}."
            )

        for missing in self.missing_evidence:
            reasons.append(f"Extracted evidence {self.evidence_id} missing support: {missing}.")

        for contradiction in self.contradictions:
            reasons.append(
                f"Extracted evidence {self.evidence_id} has unresolved contradiction: "
                f"{contradiction}."
            )

        return reasons

    @computed_field
    @property
    def human_review_required(self) -> bool:
        return bool(self.manual_review_reasons)


class ResearchAgentOutput(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    task_type: ResearchTaskType = Field(description="Research task category.")
    run_id: NonEmptyStr = Field(description="Pipeline run identifier.")
    target_company: NonEmptyStr = Field(description="Client or target company name.")
    research_question: NonEmptyStr = Field(description="Question the agent attempted to research.")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    candidate_sources: list[CandidateSource] = Field(
        default_factory=list,
        description="Structured candidate sources proposed by the agent.",
    )
    extracted_evidence: list[ExtractedEvidence] = Field(
        default_factory=list,
        description="Structured extracted evidence proposed by the agent.",
    )
    missing_evidence: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Research-level evidence the agent could not find.",
    )
    contradictions: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Research-level unresolved contradictions.",
    )
    tool_errors: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Structured tool or model errors encountered during research.",
    )

    @model_validator(mode="after")
    def validate_citation_source_ids(self) -> "ResearchAgentOutput":
        source_ids = {source.source_id for source in self.candidate_sources}

        for evidence in self.extracted_evidence:
            if evidence.source_id not in source_ids:
                raise ValueError(
                    f"Extracted evidence {evidence.evidence_id} references unknown "
                    f"source_id {evidence.source_id}."
                )

            for citation in evidence.citations:
                if citation.source_id not in source_ids:
                    raise ValueError(
                        f"Extracted evidence {evidence.evidence_id} citation references "
                        f"unknown source_id {citation.source_id}."
                    )

        return self

    @computed_field
    @property
    def manual_review_reasons(self) -> list[str]:
        reasons: list[str] = []

        for source in self.candidate_sources:
            reasons.extend(source.manual_review_reasons)

        for evidence in self.extracted_evidence:
            reasons.extend(evidence.manual_review_reasons)

        for missing in self.missing_evidence:
            reasons.append(f"Research missing evidence: {missing}.")

        for contradiction in self.contradictions:
            reasons.append(f"Research has unresolved contradiction: {contradiction}.")

        for error in self.tool_errors:
            reasons.append(f"Research tool error: {error}.")

        return reasons

    @computed_field
    @property
    def human_review_required(self) -> bool:
        return bool(self.manual_review_reasons)
