from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

DecisionState = Literal["CONTINUE", "REJECT", "MANUAL_REVIEW"]
SeverityState = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RiskState = Literal["High", "Medium", "Low", "INVALID_INPUT"]
ValidRiskState = Literal["High", "Medium", "Low"]


class StrictContractModel(BaseModel):
    """Base configuration shared by all deterministic data contracts."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ContractEnvelope(StrictContractModel):
    schema_version: Literal["1.0"] = Field(
        default="1.0",
        description="Semantic version of the JSON contract emitted by deterministic tools.",
    )
    tool: NonEmptyStr = Field(description="Human-readable tool name that emitted the payload.")
    status: NonEmptyStr = Field(description="Canonical machine-readable processing status.")
    decision: DecisionState = Field(description="Canonical downstream control decision.")
    is_blocker: bool = Field(description="True when the payload blocks automated continuation.")
    severity: SeverityState | None = Field(
        default=None,
        description="Severity of the condition reported by the tool.",
    )
    message: NonEmptyStr | None = Field(
        default=None,
        description="Short deterministic explanation for non-success or empty-result states.",
    )


class ClientCRMReadRequest(StrictContractModel):
    company_name: NonEmptyStr = Field(description="Company name to locate in the CRM datastore.")


class ClientProfile(StrictContractModel):
    company_name: NonEmptyStr = Field(
        alias="Company_Name",
        description="Legal or CRM canonical company name.",
    )
    industry: NonEmptyStr = Field(
        alias="Industry",
        description="CRM industry classification for deterministic risk mapping.",
    )
    ceo_name: NonEmptyStr = Field(
        alias="CEO_Name",
        description="Chief executive name used for watchlist screening.",
    )
    global_offices: list[NonEmptyStr] = Field(
        alias="Global_Offices",
        min_length=1,
        description="Non-empty list of countries or regions where the client operates.",
    )
    annual_revenue_usd: int = Field(
        alias="Annual_Revenue_USD",
        ge=0,
        description="Annual revenue in whole US dollars.",
    )
    financial_stability_rating: Literal["High", "Medium", "Low"] = Field(
        alias="Financial_Stability_Rating",
        description="CRM financial stability rating used for deterministic risk mapping.",
    )


class IngestionTaskOutput(StrictContractModel):
    status: Literal["SUCCESS"] = Field(description="Successful ingestion task status.")
    decision: Literal["CONTINUE"] = Field(description="Downstream continuation decision.")
    company_name: NonEmptyStr = Field(alias="Company_Name", description="Canonical company name.")
    industry: NonEmptyStr = Field(alias="Industry", description="Canonical industry.")
    ceo_name: NonEmptyStr = Field(alias="CEO_Name", description="Canonical CEO name.")
    global_offices: list[NonEmptyStr] = Field(
        alias="Global_Offices",
        min_length=1,
        description="Canonical global office list.",
    )
    annual_revenue_usd: int = Field(
        alias="Annual_Revenue_USD",
        ge=0,
        description="Canonical annual revenue in USD.",
    )
    financial_stability_rating: Literal["High", "Medium", "Low"] = Field(
        alias="Financial_Stability_Rating",
        description="Canonical financial stability rating.",
    )
    match_score: float = Field(
        ge=0.0,
        le=1.0,
        description="CRM name matching confidence from zero to one.",
    )
    match_type: Literal["EXACT", "FUZZY"] = Field(description="CRM name matching mode.")


class IngestionToolOutput(ContractEnvelope):
    tool: Literal["Read Client CRM Data"] = Field(
        default="Read Client CRM Data",
        description="Tool name for CRM ingestion.",
    )
    status: Literal["SUCCESS", "NOT_FOUND", "ERROR"] = Field(
        description="CRM lookup status.",
    )
    source: NonEmptyStr | None = Field(
        default=None,
        description="Source datastore filename for successful ingestion.",
    )
    query: NonEmptyStr | None = Field(default=None, description="Original company name query.")
    matched_company: NonEmptyStr | None = Field(
        default=None,
        description="Canonical matched CRM company name.",
    )
    match_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="CRM fuzzy match score from zero to one.",
    )
    match_type: Literal["EXACT", "FUZZY"] | None = Field(
        default=None,
        description="CRM match type.",
    )
    data: ClientProfile | None = Field(
        default=None,
        description="Validated CRM profile for the matched client.",
    )

    @model_validator(mode="after")
    def require_success_payload(self) -> "IngestionToolOutput":
        if self.status == "SUCCESS" and self.data is None:
            raise ValueError("Successful ingestion requires a validated client profile.")
        return self


class PartnerIndependenceRequest(StrictContractModel):
    company_name: NonEmptyStr = Field(description="Company name to screen against holdings.")


class WatchlistScanRequest(StrictContractModel):
    ceo_name: NonEmptyStr = Field(description="CEO name to screen against individual watchlists.")
    company_name: NonEmptyStr = Field(description="Company name to screen against entity watchlists.")
    global_offices: list[NonEmptyStr] = Field(
        min_length=1,
        description="Office locations to screen against restricted regions.",
    )

    @field_validator("global_offices", mode="before")
    @classmethod
    def reject_empty_offices(cls, value: Any) -> Any:
        if isinstance(value, list) and not value:
            raise ValueError("global_offices must contain at least one location.")
        return value


class ScreeningRequest(StrictContractModel):
    screening_type: Literal["PARTNER_INDEPENDENCE", "WATCHLIST_SCAN"] = Field(
        description="Screening workflow represented by this request.",
    )
    company_name: NonEmptyStr = Field(description="Company name used by the screening workflow.")
    ceo_name: NonEmptyStr | None = Field(
        default=None,
        description="CEO name required for WATCHLIST_SCAN requests.",
    )
    global_offices: list[NonEmptyStr] | None = Field(
        default=None,
        description="Office list required for WATCHLIST_SCAN requests.",
    )

    @model_validator(mode="after")
    def require_watchlist_fields(self) -> "ScreeningRequest":
        if self.screening_type == "WATCHLIST_SCAN":
            if self.ceo_name is None:
                raise ValueError("WATCHLIST_SCAN requires ceo_name.")
            if not self.global_offices:
                raise ValueError("WATCHLIST_SCAN requires non-empty global_offices.")
        return self


class PartnerConflict(StrictContractModel):
    partner: NonEmptyStr = Field(description="Internal partner with a matched holding.")
    asset: NonEmptyStr = Field(description="Held asset that matched the screened company.")


class WatchlistFlag(StrictContractModel):
    type: Literal["INDIVIDUAL_SANCTION", "ENTITY_SANCTION", "GEOGRAPHIC_SANCTION"] = Field(
        description="Type of watchlist hit.",
    )
    matched_term: NonEmptyStr = Field(description="Input value that matched the watchlist.")
    blacklist_record: NonEmptyStr = Field(description="Watchlist record that matched the input.")


class ScreeningResponse(ContractEnvelope):
    tool: Literal["Check Partner Independence", "Scan Sanctions Watchlist"] = Field(
        description="Screening tool that emitted this response.",
    )
    status: Literal["CLEAR", "CONFLICT_DETECTED", "SANCTIONS_HIT", "ERROR", "INVALID_INPUT"] = Field(
        description="Canonical screening result status.",
    )
    screening_type: Literal["PARTNER_INDEPENDENCE", "WATCHLIST_SCAN"] = Field(
        description="Screening workflow represented by this response.",
    )
    conflicts: list[PartnerConflict] = Field(
        default_factory=list,
        description="Validated partner independence conflicts.",
    )
    flags: list[WatchlistFlag] = Field(
        default_factory=list,
        description="Validated sanctions or restricted-region flags.",
    )


class ScreeningAggregateResponse(StrictContractModel):
    company_name: NonEmptyStr = Field(description="Canonical screened company name.")
    independence_result: ScreeningResponse = Field(
        description="Exact validated partner independence tool payload.",
    )
    sanctions_result: ScreeningResponse = Field(
        description="Exact validated sanctions watchlist tool payload.",
    )
    blocking_statuses: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Blocking statuses observed across screening tools.",
    )
    final_screening_decision: DecisionState = Field(
        description="Final deterministic screening decision derived from tool decisions.",
    )


class RiskEvaluationInput(StrictContractModel):
    industry_level: ValidRiskState = Field(description="Mapped industry risk level.")
    geography_level: ValidRiskState = Field(description="Mapped geography risk level.")
    financial_level: ValidRiskState = Field(description="Mapped financial risk level.")


class RiskInputSnapshot(StrictContractModel):
    industry: RiskState = Field(description="Normalized industry risk state.")
    geography: RiskState = Field(description="Normalized geography risk state.")
    financial: RiskState = Field(description="Normalized financial risk state.")


class RiskScoringOutput(ContractEnvelope):
    tool: Literal["Calculate Weighted Risk Score"] = Field(
        default="Calculate Weighted Risk Score",
        description="Risk scoring tool name.",
    )
    status: Literal["SUCCESS", "INVALID_INPUT"] = Field(
        description="Risk scoring execution status.",
    )
    raw_score: float | None = Field(
        default=None,
        ge=0.0,
        description="Weighted deterministic risk score when inputs are valid.",
    )
    classification: NonEmptyStr | None = Field(
        default=None,
        description="Human-readable deterministic risk classification.",
    )
    inputs: RiskInputSnapshot = Field(description="Normalized risk inputs observed by the tool.")
    invalid_inputs: dict[str, NonEmptyStr] = Field(
        default_factory=dict,
        description="Rejected raw risk inputs keyed by risk dimension.",
    )
    allowed_values: list[ValidRiskState] = Field(
        default_factory=lambda: ["High", "Medium", "Low"],
        description="Allowed valid mapped risk states.",
    )

    @model_validator(mode="after")
    def require_success_score(self) -> "RiskScoringOutput":
        if self.status == "SUCCESS" and self.raw_score is None:
            raise ValueError("Successful risk scoring requires raw_score.")
        if self.status == "INVALID_INPUT" and self.decision != "MANUAL_REVIEW":
            raise ValueError("INVALID_INPUT risk scoring must fail closed to MANUAL_REVIEW.")
        return self
