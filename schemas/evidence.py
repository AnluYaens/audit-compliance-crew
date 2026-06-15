from datetime import datetime, timezone
from pydantic import BaseModel, Field, model_validator

from schemas.decisions import ControlStatus, FinalDecision
from schemas.source_registry import SourceRecord, SourceRegistryScoringResult


class ControlEvaluation(BaseModel):
    control_id: str
    status: ControlStatus
    missing_inputs: list[str] = Field(default_factory=list)
    missing_outputs: list[str] = Field(default_factory=list)
    notes: str | None = None


class ToolError(BaseModel):
    tool_name: str
    error_message: str


class AIOutputRecord(BaseModel):
    task_name: str
    model_used: str
    input_bundle_id: str
    human_review_required: bool = True


class AuditPlanningEvidenceBundle(BaseModel):
    run_id: str
    manual_version: str = "Demo Audit Planning Control Set 2025.01"
    target_company: str
    engagement_type: str = "Financial Statement Audit"

    evidence_data: dict = Field(default_factory=dict)
    controls_evaluated: list[ControlEvaluation] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    tool_errors: list[ToolError] = Field(default_factory=list)
    ai_outputs: list[AIOutputRecord] = Field(default_factory=list)
    source_records: list[SourceRecord] = Field(default_factory=list)
    source_registry_scoring_result: SourceRegistryScoringResult | None = None
    source_support_required: bool = False

    final_decision: FinalDecision = FinalDecision.MANUAL_REVIEW
    manual_review_reasons: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_source_support_before_continue(self) -> "AuditPlanningEvidenceBundle":
        if self.final_decision != FinalDecision.CONTINUE:
            return self

        if (
            (self.source_support_required or self.source_records)
            and self.source_registry_scoring_result is None
        ):
            raise ValueError(
                "CONTINUE evidence bundles with required source support need source scoring."
            )

        if (
            self.source_registry_scoring_result is not None
            and self.source_registry_scoring_result.decision != FinalDecision.CONTINUE
        ):
            raise ValueError(
                "CONTINUE evidence bundles cannot include weak source scoring results."
            )

        return self
