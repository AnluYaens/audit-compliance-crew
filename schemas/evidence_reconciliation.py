from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import Field, computed_field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel


class EvidenceReconciliationStatus(str, Enum):
    ALIGNED = "aligned"
    REVIEW_REQUIRED = "review_required"
    MISSING_INTERNAL_EVIDENCE = "missing_internal_evidence"
    MISSING_PUBLIC_EVIDENCE = "missing_public_evidence"
    WEAK_PUBLIC_EVIDENCE = "weak_public_evidence"
    STALE_PUBLIC_EVIDENCE = "stale_public_evidence"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    SOURCE_ERROR = "source_error"
    INVALID_INPUT = "invalid_input"


class EvidenceReconciliationIssueType(str, Enum):
    MISSING_INTERNAL_EVIDENCE = "missing_internal_evidence"
    MISSING_PUBLIC_EVIDENCE = "missing_public_evidence"
    LOW_CONFIDENCE = "low_confidence"
    STALE_SOURCE = "stale_source"
    CONTRADICTION = "contradiction"
    TOOL_ERROR = "tool_error"
    INVALID_INPUT = "invalid_input"
    UNSAFE_PUBLIC_HINT = "unsafe_public_hint"
    REVIEW_REQUIRED = "review_required"


class EvidenceReconciliationSourceLane(str, Enum):
    SANDBOX = "sandbox"
    INTERNAL = "internal"
    PUBLIC = "public"
    RECONCILIATION = "reconciliation"


class EvidenceReconciliationReasonCode(str, Enum):
    MISSING_INTERNAL_EVIDENCE = "MISSING_INTERNAL_EVIDENCE"
    MISSING_PUBLIC_EVIDENCE = "MISSING_PUBLIC_EVIDENCE"
    LOW_PUBLIC_CONFIDENCE = "LOW_PUBLIC_CONFIDENCE"
    STALE_PUBLIC_SOURCE = "STALE_PUBLIC_SOURCE"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    SANDBOX_TOOL_ERROR = "SANDBOX_TOOL_ERROR"
    PUBLIC_TOOL_ERROR = "PUBLIC_TOOL_ERROR"
    INVALID_SANDBOX_INPUT = "INVALID_SANDBOX_INPUT"
    INVALID_PUBLIC_INPUT = "INVALID_PUBLIC_INPUT"
    UNSAFE_PUBLIC_HINT = "UNSAFE_PUBLIC_HINT"
    SANDBOX_REVIEW_REQUIRED = "SANDBOX_REVIEW_REQUIRED"
    PUBLIC_REVIEW_REQUIRED = "PUBLIC_REVIEW_REQUIRED"


class EvidenceReconciliationIssue(StrictContractModel):
    issue_id: NonEmptyStr = Field(description="Stable reconciliation issue identifier.")
    issue_type: EvidenceReconciliationIssueType = Field(
        description="Structured category for the detected reconciliation issue."
    )
    summary: NonEmptyStr = Field(
        description="Generic, synthetic-safe issue summary without local artifact values."
    )
    source_lane: EvidenceReconciliationSourceLane = Field(
        description="Lane whose structured output produced the issue signal."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the deterministic issue classification.",
    )
    human_review_required: bool = Field(
        default=True,
        description="True when an auditor must review the issue.",
    )
    reason_code: EvidenceReconciliationReasonCode = Field(
        description="Machine-readable reason for the issue."
    )


class EvidenceReconciliationResult(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    reconciliation_id: NonEmptyStr = Field(
        description="Stable identifier for this reconciliation."
    )
    sandbox_request_id: NonEmptyStr = Field(
        description="Sandbox verifier request identifier."
    )
    artifact_bundle_id: NonEmptyStr = Field(
        description="Normalized internal artifact bundle identifier."
    )
    public_research_run_id: NonEmptyStr = Field(
        description="Public research run identifier."
    )
    status: EvidenceReconciliationStatus = Field(
        description="Non-decisional deterministic reconciliation status."
    )
    issues: list[EvidenceReconciliationIssue] = Field(default_factory=list)
    aligned_evidence_summaries: list[NonEmptyStr] = Field(default_factory=list)
    missing_evidence_summaries: list[NonEmptyStr] = Field(default_factory=list)
    contradiction_summaries: list[NonEmptyStr] = Field(default_factory=list)
    source_error_summaries: list[NonEmptyStr] = Field(default_factory=list)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when reconciliation completed."
    )

    @computed_field
    @property
    def human_review_required(self) -> bool:
        return self.status is not EvidenceReconciliationStatus.ALIGNED or any(
            issue.human_review_required for issue in self.issues
        )

    @model_validator(mode="after")
    def validate_aligned_result(self) -> "EvidenceReconciliationResult":
        if self.status is EvidenceReconciliationStatus.ALIGNED:
            if self.issues:
                raise ValueError("Aligned reconciliation results cannot contain issues.")
            if not self.aligned_evidence_summaries:
                raise ValueError("Aligned reconciliation results require aligned summaries.")
            if (
                self.missing_evidence_summaries
                or self.contradiction_summaries
                or self.source_error_summaries
            ):
                raise ValueError("Aligned reconciliation results cannot contain review summaries.")
        return self
