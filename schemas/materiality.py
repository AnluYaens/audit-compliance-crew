from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel
from schemas.decisions import FinalDecision


BenchmarkType = Literal[
    "profit_before_tax",
    "revenue",
    "total_assets",
    "equity",
    "expenses",
]


class MaterialityRequest(StrictContractModel):
    target_company: NonEmptyStr = Field(description="Client or target company name.")
    benchmark_type: BenchmarkType = Field(description="Selected materiality benchmark.")
    benchmark_amount: float = Field(gt=0, description="Positive benchmark amount.")

    overall_materiality_percentage: float = Field(
        gt=0,
        le=1,
        description="Percentage applied to benchmark. Example: 0.05 for 5%.",
    )
    performance_materiality_percentage: float = Field(
        gt=0,
        le=1,
        description="Percentage applied to overall materiality. Example: 0.75 for 75%.",
    )
    clearly_trivial_percentage: float = Field(
        gt=0,
        le=1,
        description="Percentage applied to overall materiality. Example: 0.05 for 5%.",
    )

    rationale: NonEmptyStr = Field(
        description="Documented rationale for benchmark and percentage selection."
    )

    @model_validator(mode="after")
    def validate_threshold_relationships(self) -> "MaterialityRequest":
        if self.clearly_trivial_percentage >= self.performance_materiality_percentage:
            raise ValueError(
                "clearly_trivial_percentage must be lower than performance_materiality_percentage."
            )
        return self


class MaterialityResult(StrictContractModel):
    tool: Literal["Calculate Materiality"] = "Calculate Materiality"
    status: Literal["SUCCESS"] = "SUCCESS"
    decision: FinalDecision

    target_company: NonEmptyStr
    benchmark_type: BenchmarkType
    benchmark_amount: float

    overall_materiality_percentage: float
    performance_materiality_percentage: float
    clearly_trivial_percentage: float

    overall_materiality: float
    performance_materiality: float
    clearly_trivial_threshold: float

    rationale: NonEmptyStr
    manual_review_flags: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision_matches_flags(self) -> "MaterialityResult":
        if self.manual_review_flags and self.decision != FinalDecision.MANUAL_REVIEW:
            raise ValueError("Materiality results with review flags must route to MANUAL_REVIEW.")

        if not self.manual_review_flags and self.decision != FinalDecision.CONTINUE:
            raise ValueError("Materiality results without review flags should route to CONTINUE.")

        return self