from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import Field, computed_field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel
from schemas.evidence import AuditPlanningEvidenceBundle


class AuditorAssistantResponseStatus(str, Enum):
    ANSWERED = "ANSWERED"
    REFUSED = "REFUSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class AuditorAssistantCitation(StrictContractModel):
    field_path: NonEmptyStr = Field(
        description=(
            "Dot-delimited field path in the AuditPlanningEvidenceBundle that supports "
            "the answer, such as evidence_data.materiality_result.decision."
        ),
    )
    label: NonEmptyStr | None = Field(
        default=None,
        description="Short human-readable description of the cited evidence field.",
    )
    quoted_value: NonEmptyStr | None = Field(
        default=None,
        description="Short value copied or summarized from the cited evidence field.",
    )


class AuditorAssistantRequest(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: NonEmptyStr = Field(description="Evidence bundle run identifier.")
    target_company: NonEmptyStr = Field(description="Client or target company name.")
    question: NonEmptyStr = Field(description="Auditor question to answer from the evidence bundle.")
    evidence_bundle: AuditPlanningEvidenceBundle = Field(
        description="Validated evidence bundle. This is the assistant source of truth.",
    )
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_request_matches_bundle(self) -> "AuditorAssistantRequest":
        if self.run_id != self.evidence_bundle.run_id:
            raise ValueError("Auditor assistant request run_id must match the evidence bundle.")

        if self.target_company != self.evidence_bundle.target_company:
            raise ValueError(
                "Auditor assistant request target_company must match the evidence bundle."
            )

        return self


class AuditorAssistantResponse(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: NonEmptyStr = Field(description="Evidence bundle run identifier.")
    target_company: NonEmptyStr = Field(description="Client or target company name.")
    question: NonEmptyStr = Field(description="Auditor question that was answered or refused.")
    status: AuditorAssistantResponseStatus = Field(
        description="Whether the assistant answered, refused, or routed to review.",
    )
    answer: NonEmptyStr = Field(
        description=(
            "Auditor-facing answer. It may explain cited evidence fields, but must not "
            "assign or override final decisions."
        ),
    )
    citations: list[AuditorAssistantCitation] = Field(
        default_factory=list,
        description="Evidence bundle field citations supporting the answer.",
    )
    unsupported_claims: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Claims or requested conclusions not supported by the evidence bundle.",
    )
    guardrail_flags: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Decision-boundary or support issues identified by guardrails.",
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_status_support(self) -> "AuditorAssistantResponse":
        if self.status == AuditorAssistantResponseStatus.ANSWERED:
            if not self.citations:
                raise ValueError("Answered auditor assistant responses require citations.")
            if self.unsupported_claims:
                raise ValueError("Answered auditor assistant responses cannot include unsupported claims.")
            if self.guardrail_flags:
                raise ValueError("Answered auditor assistant responses cannot include guardrail flags.")

        if self.status in {
            AuditorAssistantResponseStatus.REFUSED,
            AuditorAssistantResponseStatus.REVIEW_REQUIRED,
        } and not (self.unsupported_claims or self.guardrail_flags):
            raise ValueError("Refused or review-required responses require guardrail detail.")

        return self

    @computed_field
    @property
    def manual_review_reasons(self) -> list[str]:
        reasons: list[str] = []

        for claim in self.unsupported_claims:
            reasons.append(f"Auditor assistant unsupported claim: {claim}.")

        for flag in self.guardrail_flags:
            reasons.append(f"Auditor assistant guardrail: {flag}.")

        if self.status == AuditorAssistantResponseStatus.REVIEW_REQUIRED and not reasons:
            reasons.append("Auditor assistant routed the question to manual review.")

        if self.status == AuditorAssistantResponseStatus.REFUSED and not reasons:
            reasons.append("Auditor assistant refused an unsupported or disallowed request.")

        return reasons

    @computed_field
    @property
    def human_review_required(self) -> bool:
        return self.status != AuditorAssistantResponseStatus.ANSWERED or bool(
            self.manual_review_reasons
        )
