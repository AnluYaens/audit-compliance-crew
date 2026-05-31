from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel
from schemas.decisions import FinalDecision


class SourceType(str, Enum):
    REGULATORY = "REGULATORY"
    GOVERNMENT_REGISTRY = "GOVERNMENT_REGISTRY"
    AUDITED_FINANCIAL_STATEMENT = "AUDITED_FINANCIAL_STATEMENT"
    COMPANY_FILING = "COMPANY_FILING"
    INTERNAL_SYSTEM = "INTERNAL_SYSTEM"
    THIRD_PARTY_DATABASE = "THIRD_PARTY_DATABASE"
    NEWS_MEDIA = "NEWS_MEDIA"
    OTHER = "OTHER"


class SourceRecord(StrictContractModel):
    url: NonEmptyStr | None = Field(
        default=None,
        description="Source URL when the source is addressable on the web.",
    )
    identifier: NonEmptyStr | None = Field(
        default=None,
        description="Stable non-URL source identifier, such as a filing ID or document ID.",
    )
    source_type: SourceType = Field(description="Deterministic source category.")
    publisher: NonEmptyStr | None = Field(
        default=None,
        description="Source publisher, authority, or system owner.",
    )
    retrieval_date: datetime = Field(description="When the source metadata was retrieved.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Metadata confidence from zero to one.",
    )
    freshness_days: int = Field(
        ge=0,
        description="Maximum acceptable source age in days for this source record.",
    )
    relevance: float = Field(
        ge=0.0,
        le=1.0,
        description="Deterministic relevance score from zero to one.",
    )
    notes: NonEmptyStr | None = Field(default=None, description="Optional provenance notes.")
    contradiction_flags: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Known contradictions or unresolved inconsistencies for this source.",
    )


class SourceRegistry(StrictContractModel):
    run_id: NonEmptyStr
    target_company: NonEmptyStr
    records: list[SourceRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceScoreBreakdown(StrictContractModel):
    authority_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    contradiction_flag: bool


class SourceScoringResult(StrictContractModel):
    tool: Literal["Score Source Reliability"] = "Score Source Reliability"
    status: Literal["SUCCESS", "REVIEW_REQUIRED"]
    decision: FinalDecision
    source: SourceRecord
    scores: SourceScoreBreakdown
    total_score: float = Field(ge=0.0, le=1.0)
    manual_review_reasons: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision_matches_reasons(self) -> "SourceScoringResult":
        if self.decision == FinalDecision.CONTINUE:
            if self.status != "SUCCESS":
                raise ValueError("CONTINUE source scoring results must have SUCCESS status.")
            if self.manual_review_reasons:
                raise ValueError("CONTINUE source scoring results cannot include review reasons.")

        if self.decision == FinalDecision.MANUAL_REVIEW:
            if self.status != "REVIEW_REQUIRED":
                raise ValueError("MANUAL_REVIEW source scoring results must require review.")
            if not self.manual_review_reasons:
                raise ValueError("MANUAL_REVIEW source scoring results require review reasons.")

        if self.decision == FinalDecision.REJECT:
            raise ValueError("Source scoring cannot reject sources; it must fail closed to review.")

        return self


class SourceRegistryScoringResult(StrictContractModel):
    tool: Literal["Score Source Registry"] = "Score Source Registry"
    status: Literal["SUCCESS", "REVIEW_REQUIRED"]
    decision: FinalDecision
    run_id: NonEmptyStr
    target_company: NonEmptyStr
    source_results: list[SourceScoringResult] = Field(default_factory=list)
    manual_review_reasons: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_registry_decision(self) -> "SourceRegistryScoringResult":
        if self.decision == FinalDecision.CONTINUE:
            if self.status != "SUCCESS":
                raise ValueError("CONTINUE registry scoring results must have SUCCESS status.")
            if self.manual_review_reasons:
                raise ValueError("CONTINUE registry scoring results cannot include review reasons.")

        if self.decision == FinalDecision.MANUAL_REVIEW:
            if self.status != "REVIEW_REQUIRED":
                raise ValueError("MANUAL_REVIEW registry scoring results must require review.")
            if not self.manual_review_reasons:
                raise ValueError("MANUAL_REVIEW registry scoring results require review reasons.")

        if self.decision == FinalDecision.REJECT:
            raise ValueError("Source registry scoring cannot reject sources.")

        return self
