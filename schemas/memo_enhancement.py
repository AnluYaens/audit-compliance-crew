from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import Field, computed_field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel
from schemas.decisions import FinalDecision
from schemas.evidence import AuditPlanningEvidenceBundle


class MemoEnhancementStatus(str, Enum):
    ENHANCED = "ENHANCED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"


class MemoEnhancementChangeType(str, Enum):
    READABILITY_EDIT = "READABILITY_EDIT"
    STRUCTURAL_EDIT = "STRUCTURAL_EDIT"
    FACTUAL_ADDITION = "FACTUAL_ADDITION"


class MemoEvidenceReference(StrictContractModel):
    field_path: NonEmptyStr = Field(
        description=(
            "Dot-delimited field path in the AuditPlanningEvidenceBundle that supports "
            "the memo language, such as final_decision or evidence_data.materiality_result."
        ),
    )
    label: NonEmptyStr | None = Field(
        default=None,
        description="Short human-readable label for the referenced evidence field.",
    )
    quoted_value: NonEmptyStr | None = Field(
        default=None,
        description="Short value copied or summarized from the referenced evidence field.",
    )


class MemoEnhancementChange(StrictContractModel):
    change_type: MemoEnhancementChangeType = Field(
        description="Type of edit proposed by the enhancement step.",
    )
    summary: NonEmptyStr = Field(description="Short summary of the proposed edit.")
    evidence_references: list[MemoEvidenceReference] = Field(
        default_factory=list,
        description=(
            "Evidence bundle references supporting factual additions. Readability-only "
            "edits may leave this empty."
        ),
    )


class MemoEnhancementRequest(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: NonEmptyStr = Field(description="Evidence bundle run identifier.")
    target_company: NonEmptyStr = Field(description="Client or target company name.")
    original_memo: NonEmptyStr = Field(
        description="Deterministic planning memo draft. This remains authoritative.",
    )
    evidence_bundle: AuditPlanningEvidenceBundle = Field(
        description="Validated evidence bundle. This is the enhancement source of truth.",
    )
    enhancement_instructions: NonEmptyStr | None = Field(
        default=None,
        description="Optional auditor-facing readability instructions.",
    )
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_request_matches_bundle(self) -> "MemoEnhancementRequest":
        if self.run_id != self.evidence_bundle.run_id:
            raise ValueError("Memo enhancement request run_id must match the evidence bundle.")

        if self.target_company != self.evidence_bundle.target_company:
            raise ValueError(
                "Memo enhancement request target_company must match the evidence bundle."
            )

        return self


class MemoEnhancementResponse(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: NonEmptyStr = Field(description="Evidence bundle run identifier.")
    target_company: NonEmptyStr = Field(description="Client or target company name.")
    status: MemoEnhancementStatus = Field(
        description="Whether the enhancement was accepted, routed to review, or rejected.",
    )
    original_final_decision: FinalDecision = Field(
        description="Final decision from the deterministic memo or evidence bundle.",
    )
    preserved_final_decision: FinalDecision = Field(
        description="Final decision reported after enhancement. It must not change.",
    )
    preserved_manual_review_reasons: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Manual review reasons copied from the evidence bundle without suppression.",
    )
    enhanced_memo: NonEmptyStr | None = Field(
        default=None,
        description="Enhanced memo language. It cannot replace the deterministic memo without review.",
    )
    evidence_references: list[MemoEvidenceReference] = Field(
        default_factory=list,
        description="Evidence bundle references preserved or cited by the enhanced memo.",
    )
    changes: list[MemoEnhancementChange] = Field(
        default_factory=list,
        description="Structured list of readability edits or factual additions.",
    )
    unsupported_additions: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Facts or claims added without evidence bundle support.",
    )
    guardrail_flags: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Decision-boundary, provenance, or review guardrail issues.",
    )
    human_review_required: bool = Field(
        default=True,
        description="Memo enhancements always require human review before use.",
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_review_and_status_detail(self) -> "MemoEnhancementResponse":
        if not self.human_review_required:
            raise ValueError("Enhanced memos must be marked human_review_required.")

        if self.status == MemoEnhancementStatus.ENHANCED and self.enhanced_memo is None:
            raise ValueError("Enhanced memo responses require enhanced_memo content.")

        if self.status in {
            MemoEnhancementStatus.REJECTED,
            MemoEnhancementStatus.REVIEW_REQUIRED,
        } and not (self.unsupported_additions or self.guardrail_flags):
            raise ValueError(
                "Rejected or review-required memo enhancements require guardrail detail."
            )

        return self

    @computed_field
    @property
    def manual_review_reasons(self) -> list[str]:
        reasons = ["Memo enhancement output requires human review before use."]

        for reason in self.preserved_manual_review_reasons:
            reasons.append(f"Preserved evidence bundle manual review reason: {reason}.")

        for addition in self.unsupported_additions:
            reasons.append(f"Memo enhancement unsupported addition: {addition}.")

        for flag in self.guardrail_flags:
            reasons.append(f"Memo enhancement guardrail: {flag}.")

        return reasons
