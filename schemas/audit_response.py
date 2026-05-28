from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel
from schemas.decisions import FinalDecision
from schemas.risk_assessment import (
    AssessedRisk,
    FinancialStatementArea,
    RiskLevel,
    RiskType,
)


class AuditProcedureType(str, Enum):
    INQUIRY = "INQUIRY"
    INSPECTION = "INSPECTION"
    OBSERVATION = "OBSERVATION"
    RECALCULATION = "RECALCULATION"
    REPERFORMANCE = "REPERFORMANCE"
    ANALYTICAL_PROCEDURE = "ANALYTICAL_PROCEDURE"
    SUBSTANTIVE_TESTING = "SUBSTANTIVE_TESTING"
    TEST_OF_CONTROLS = "TEST_OF_CONTROLS"
    JOURNAL_ENTRY_TESTING = "JOURNAL_ENTRY_TESTING"


class AuditResponseProcedure(StrictContractModel):
    area: FinancialStatementArea
    procedure_type: AuditProcedureType
    description: NonEmptyStr
    linked_risk_level: RiskLevel
    linked_risk_type: RiskType


class AuditResponseRequest(StrictContractModel):
    target_company: NonEmptyStr
    assessed_risks: list[AssessedRisk] = Field(min_length=1)


class AuditResponseResult(StrictContractModel):
    tool: str = "Design Audit Response"
    status: str = "SUCCESS"
    decision: FinalDecision
    target_company: NonEmptyStr
    procedures: list[AuditResponseProcedure] = Field(min_length=1)
    manual_review_reasons: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision(self) -> "AuditResponseResult":
        if self.manual_review_reasons and self.decision != FinalDecision.MANUAL_REVIEW:
            raise ValueError("Audit response with manual review reasons must route to MANUAL_REVIEW.")

        if not self.manual_review_reasons and self.decision != FinalDecision.CONTINUE:
            raise ValueError("Audit response without manual review reasons should route to CONTINUE.")

        return self