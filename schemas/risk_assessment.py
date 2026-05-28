from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel
from schemas.decisions import FinalDecision


class FinancialStatementArea(str, Enum):
    REVENUE = "Revenue"
    INVENTORY = "Inventory"
    CASH = "Cash"
    EXPENSES = "Expenses"
    RECEIVABLES = "Receivables"
    PAYABLES = "Payables"
    MANAGEMENT_OVERRIDE = "Management Override"
    GOING_CONCERN = "Going Concern"


class AuditAssertion(str, Enum):
    OCCURRENCE = "Occurrence"
    COMPLETENESS = "Completeness"
    ACCURACY = "Accuracy"
    CUT_OFF = "Cut-off"
    CLASSIFICATION = "Classification"
    EXISTENCE = "Existence"
    RIGHTS_AND_OBLIGATIONS = "Rights and Obligations"
    VALUATION = "Valuation"
    PRESENTATION = "Presentation"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    SIGNIFICANT = "SIGNIFICANT"


class RiskType(str, Enum):
    NORMAL = "NORMAL"
    FRAUD = "FRAUD"
    GOING_CONCERN = "GOING_CONCERN"
    FINANCIAL_STATEMENT_LEVEL = "FINANCIAL_STATEMENT_LEVEL"


class RiskIndicator(StrictContractModel):
    area: FinancialStatementArea
    assertion: AuditAssertion
    description: NonEmptyStr
    likelihood: int = Field(ge=1, le=5)
    magnitude: int = Field(ge=1, le=5)
    fraud_indicator: bool = False
    going_concern_indicator: bool = False


class RiskAssessmentRequest(StrictContractModel):
    target_company: NonEmptyStr
    indicators: list[RiskIndicator] = Field(min_length=1)


class AssessedRisk(StrictContractModel):
    area: FinancialStatementArea
    assertion: AuditAssertion
    risk_level: RiskLevel
    risk_type: RiskType
    score: int
    rationale: NonEmptyStr
    manual_review_required: bool


class RiskAssessmentResult(StrictContractModel):
    tool: str = "Assess Audit Risks"
    status: str = "SUCCESS"
    decision: FinalDecision
    target_company: NonEmptyStr
    assessed_risks: list[AssessedRisk] = Field(min_length=1)
    manual_review_reasons: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision(self) -> "RiskAssessmentResult":
        if self.manual_review_reasons and self.decision != FinalDecision.MANUAL_REVIEW:
            raise ValueError("Risk assessment with review reasons must route to MANUAL_REVIEW.")

        if not self.manual_review_reasons and self.decision != FinalDecision.CONTINUE:
            raise ValueError("Risk assessment without review reasons should route to CONTINUE.")

        return self