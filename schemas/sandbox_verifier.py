from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import Field, computed_field, model_validator

from schemas.client_artifacts import (
    ClientArtifactProvenanceReference,
    ClientArtifactSensitivity,
    ClientArtifactSourceMetadata,
)
from schemas.contracts import NonEmptyStr, StrictContractModel


LOW_SANDBOX_CONFIDENCE_THRESHOLD = 0.75


class SandboxFindingType(str, Enum):
    SUPPORTED_CLAIM = "supported_claim"
    MISSING_EVIDENCE = "missing_evidence"
    CONTRADICTION = "contradiction"
    ANOMALY = "anomaly"
    LOW_CONFIDENCE = "low_confidence"
    UNSUPPORTED_CLAIM = "unsupported_claim"


class SandboxReviewReasonCode(str, Enum):
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    CONTRADICTION = "CONTRADICTION"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ANOMALY = "ANOMALY"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    INVALID_INPUT = "INVALID_INPUT"
    TOOL_ERROR = "TOOL_ERROR"
    HUMAN_REVIEW_RECOMMENDED = "HUMAN_REVIEW_RECOMMENDED"


class SafePublicSearchHintType(str, Enum):
    OFFICIAL_WEBSITE = "official_website"
    ANNUAL_REPORT = "annual_report"
    FINANCIAL_STATEMENT = "financial_statement"
    SANCTIONS_LIST = "sanctions_list"
    REGULATOR_SOURCE = "regulator_source"
    RELIABLE_NEWS = "reliable_news"


class SafePublicSearchHintSensitivity(str, Enum):
    PUBLIC = "PUBLIC"
    NON_SENSITIVE = "NON_SENSITIVE"


class SandboxVerifierStatus(str, Enum):
    SUCCESS = "success"
    REVIEW_REQUIRED = "review_required"
    INVALID_INPUT = "invalid_input"
    TOOL_ERROR = "tool_error"


class SandboxVerifierRequest(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: NonEmptyStr = Field(description="Stable identifier for this verifier request.")
    artifact_bundle_id: NonEmptyStr | None = Field(
        default=None,
        description="Normalized artifact bundle identifier when the whole bundle is in scope.",
    )
    normalized_artifact_references: list[ClientArtifactProvenanceReference] = Field(
        default_factory=list,
        description="Specific normalized artifact locations in scope for verification.",
    )
    allowed_artifact_metadata: list[ClientArtifactSourceMetadata] = Field(
        min_length=1,
        description="Allowed normalized artifact metadata for local verifier access.",
    )
    verifier_objective: NonEmptyStr | None = Field(
        default=None,
        description="Objective the offline verifier should inspect.",
    )
    checklist_name: NonEmptyStr | None = Field(
        default=None,
        description="Named checklist the offline verifier should apply.",
    )
    sensitivity: ClientArtifactSensitivity = Field(
        description="Maximum sensitivity classification for the verifier request.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the verifier request was created.",
    )
    safe_public_search_hint_policy_ref: NonEmptyStr | None = Field(
        default=None,
        description="Optional deterministic policy reference for later safe hint filtering.",
    )

    @model_validator(mode="after")
    def require_bundle_or_artifact_reference(self) -> "SandboxVerifierRequest":
        if self.artifact_bundle_id is None and not self.normalized_artifact_references:
            raise ValueError(
                "Sandbox verifier requests require artifact_bundle_id or "
                "normalized_artifact_references."
            )
        return self

    @model_validator(mode="after")
    def require_objective_or_checklist(self) -> "SandboxVerifierRequest":
        if self.verifier_objective is None and self.checklist_name is None:
            raise ValueError("Sandbox verifier requests require verifier_objective or checklist_name.")
        return self


class LocalEvidenceFinding(StrictContractModel):
    finding_id: NonEmptyStr = Field(description="Stable identifier for the local finding.")
    finding_type: SandboxFindingType = Field(description="Structured local finding category.")
    claim_summary: NonEmptyStr = Field(description="Claim or finding summary.")
    provenance_references: list[ClientArtifactProvenanceReference] = Field(
        default_factory=list,
        description="Normalized artifact provenance supporting the finding.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Verifier confidence in the finding from zero to one.",
    )
    sensitivity: ClientArtifactSensitivity = Field(
        description="Sensitivity classification for the local finding.",
    )
    human_review_recommended: bool = Field(
        default=False,
        description="True when the finding should be surfaced to an auditor.",
    )
    review_reason_codes: list[SandboxReviewReasonCode] = Field(
        default_factory=list,
        description="Machine-readable reasons for auditor review.",
    )

    @model_validator(mode="after")
    def validate_review_guardrails(self) -> "LocalEvidenceFinding":
        required_reasons_by_type = {
            SandboxFindingType.MISSING_EVIDENCE: SandboxReviewReasonCode.MISSING_EVIDENCE,
            SandboxFindingType.CONTRADICTION: SandboxReviewReasonCode.CONTRADICTION,
            SandboxFindingType.LOW_CONFIDENCE: SandboxReviewReasonCode.LOW_CONFIDENCE,
            SandboxFindingType.UNSUPPORTED_CLAIM: SandboxReviewReasonCode.UNSUPPORTED_CLAIM,
            SandboxFindingType.ANOMALY: SandboxReviewReasonCode.ANOMALY,
        }

        required_reason = required_reasons_by_type.get(self.finding_type)
        if required_reason is not None:
            if not self.human_review_recommended:
                raise ValueError(f"{self.finding_type.value} findings require human review.")
            if required_reason not in self.review_reason_codes:
                raise ValueError(
                    f"{self.finding_type.value} findings require {required_reason.value}."
                )

        if self.confidence < LOW_SANDBOX_CONFIDENCE_THRESHOLD:
            if not self.human_review_recommended:
                raise ValueError("Low-confidence findings require human review.")
            if SandboxReviewReasonCode.LOW_CONFIDENCE not in self.review_reason_codes:
                raise ValueError("Low-confidence findings require LOW_CONFIDENCE.")

        if self.finding_type == SandboxFindingType.SUPPORTED_CLAIM and not self.provenance_references:
            raise ValueError("Supported findings require normalized artifact provenance.")

        return self


class SafePublicSearchHintCandidate(StrictContractModel):
    hint_id: NonEmptyStr = Field(description="Stable identifier for the safe search hint.")
    hint_text: NonEmptyStr = Field(description="Public-safe text or query terms.")
    hint_type: SafePublicSearchHintType = Field(description="Structured safe hint category.")
    safe_reason: NonEmptyStr = Field(description="Reason this hint is safe to consider publicly.")
    sensitivity: SafePublicSearchHintSensitivity = Field(
        description="Public or non-sensitive classification for the hint.",
    )
    provenance: ClientArtifactProvenanceReference | None = Field(
        default=None,
        description="Normalized artifact location that produced the hint, when available.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Verifier confidence in the safe hint from zero to one.",
    )
    human_review_recommended: bool = Field(
        default=False,
        description="True when an auditor should inspect the hint before use.",
    )


class SandboxVerifierOutput(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: NonEmptyStr = Field(description="Verifier request identifier.")
    artifact_bundle_id: NonEmptyStr = Field(description="Normalized artifact bundle identifier.")
    verifier_status: SandboxVerifierStatus = Field(
        description="Non-decisional verifier processing status.",
    )
    findings: list[LocalEvidenceFinding] = Field(default_factory=list)
    safe_public_search_hint_candidates: list[SafePublicSearchHintCandidate] = Field(
        default_factory=list,
        description="Public-safe hint candidates for later deterministic filtering.",
    )
    missing_evidence_items: list[NonEmptyStr] = Field(default_factory=list)
    contradictions: list[NonEmptyStr] = Field(default_factory=list)
    tool_errors: list[NonEmptyStr] = Field(default_factory=list)
    review_reasons: list[SandboxReviewReasonCode] = Field(default_factory=list)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the verifier output was generated.",
    )

    @computed_field
    @property
    def human_review_required(self) -> bool:
        if self.verifier_status in {
            SandboxVerifierStatus.REVIEW_REQUIRED,
            SandboxVerifierStatus.INVALID_INPUT,
            SandboxVerifierStatus.TOOL_ERROR,
        }:
            return True

        if self.missing_evidence_items or self.contradictions or self.tool_errors:
            return True

        if self.review_reasons:
            return True

        if any(finding.human_review_recommended for finding in self.findings):
            return True

        return any(hint.human_review_recommended for hint in self.safe_public_search_hint_candidates)
