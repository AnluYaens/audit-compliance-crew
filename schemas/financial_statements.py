from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, ClassVar

from pydantic import Field, StringConstraints, computed_field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel


LOW_CONFIDENCE_THRESHOLD = 0.75

CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class StatementType(str, Enum):
    BALANCE_SHEET = "BALANCE_SHEET"
    INCOME_STATEMENT = "INCOME_STATEMENT"
    CASH_FLOW_STATEMENT = "CASH_FLOW_STATEMENT"
    NOTES = "NOTES"


class LineItemExtractionStatus(str, Enum):
    PRESENT = "PRESENT"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SourceReference(StrictContractModel):
    document_id: NonEmptyStr = Field(description="Stable identifier for the source document.")
    page_number: int | None = Field(
        default=None,
        ge=1,
        description="One-based source page number when available.",
    )
    section: NonEmptyStr | None = Field(
        default=None,
        description="Statement, note, or table section used as the source reference.",
    )
    locator: NonEmptyStr | None = Field(
        default=None,
        description="Optional cell, paragraph, or bounding-box locator from extraction.",
    )


class FinancialStatementPeriod(StrictContractModel):
    end_date: date = Field(description="Reporting period end date.")
    start_date: date | None = Field(
        default=None,
        description="Reporting period start date when applicable.",
    )
    fiscal_year: int | None = Field(
        default=None,
        ge=1900,
        le=9999,
        description="Fiscal year label when available.",
    )

    @model_validator(mode="after")
    def validate_date_order(self) -> "FinancialStatementPeriod":
        if self.start_date is not None and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date.")
        return self


class NormalizedLineItem(StrictContractModel):
    normalized_name: NonEmptyStr = Field(
        description="Canonical snake_case name used by deterministic services.",
    )
    source_label: NonEmptyStr | None = Field(
        default=None,
        description="Original line item caption from the financial statements.",
    )
    amount: Decimal | None = Field(
        default=None,
        description="Normalized monetary amount in the parent statement currency.",
    )
    extraction_status: LineItemExtractionStatus = Field(
        default=LineItemExtractionStatus.PRESENT,
        description="Whether the line item was extracted, estimated, missing, or not applicable.",
    )
    source_reference: SourceReference | None = Field(
        default=None,
        description="Source location for this specific line item.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Line-item extraction confidence from zero to one.",
    )
    missing_reason: NonEmptyStr | None = Field(
        default=None,
        description="Reason a required or expected line item could not be extracted.",
    )

    @model_validator(mode="after")
    def validate_amount_for_status(self) -> "NormalizedLineItem":
        if self.extraction_status in {
            LineItemExtractionStatus.PRESENT,
            LineItemExtractionStatus.ESTIMATED,
        } and self.amount is None:
            raise ValueError("Present or estimated line items require an amount.")

        if self.extraction_status == LineItemExtractionStatus.MISSING:
            if self.amount is not None:
                raise ValueError("Missing line items cannot include an amount.")
            if self.missing_reason is None:
                raise ValueError("Missing line items require a missing_reason.")

        return self


class FinancialStatementBase(StrictContractModel):
    required_line_items: ClassVar[tuple[str, ...]] = ()

    statement_type: StatementType
    period: FinancialStatementPeriod = Field(description="Validated reporting period.")
    currency: CurrencyCode = Field(description="ISO 4217 statement currency code.")
    source_reference: SourceReference = Field(
        description="Source document reference for the statement as a whole.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall statement extraction confidence from zero to one.",
    )
    missing_fields: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Statement-level fields that extraction could not validate.",
    )
    line_items: list[NormalizedLineItem] = Field(
        min_length=1,
        description="Normalized statement line items, including explicit missing items.",
    )

    @computed_field
    @property
    def missing_required_line_items(self) -> list[str]:
        represented_names = {item.normalized_name for item in self.line_items}
        missing_names = {
            item.normalized_name
            for item in self.line_items
            if item.extraction_status == LineItemExtractionStatus.MISSING
        }
        absent_required_names = set(self.required_line_items) - represented_names

        return sorted(missing_names | absent_required_names)

    @computed_field
    @property
    def manual_review_reasons(self) -> list[str]:
        reasons: list[str] = []

        if self.confidence < LOW_CONFIDENCE_THRESHOLD:
            reasons.append(
                f"Statement confidence {self.confidence:.2f} is below "
                f"{LOW_CONFIDENCE_THRESHOLD:.2f}."
            )

        for field_name in self.missing_fields:
            reasons.append(f"Missing statement field: {field_name}.")

        for line_item_name in self.missing_required_line_items:
            reasons.append(f"Missing required line item: {line_item_name}.")

        for item in self.line_items:
            if item.confidence < LOW_CONFIDENCE_THRESHOLD:
                reasons.append(
                    f"Line item {item.normalized_name} confidence {item.confidence:.2f} "
                    f"is below {LOW_CONFIDENCE_THRESHOLD:.2f}."
                )

        return reasons

    @computed_field
    @property
    def manual_review_required(self) -> bool:
        return bool(self.manual_review_reasons)


class BalanceSheetStatement(FinancialStatementBase):
    required_line_items: ClassVar[tuple[str, ...]] = (
        "cash_and_cash_equivalents",
        "total_assets",
        "total_liabilities",
        "total_equity",
    )

    statement_type: StatementType = StatementType.BALANCE_SHEET


class IncomeStatement(FinancialStatementBase):
    required_line_items: ClassVar[tuple[str, ...]] = (
        "revenue",
        "expenses",
        "profit_before_tax",
        "net_income",
    )

    statement_type: StatementType = StatementType.INCOME_STATEMENT


class CashFlowStatement(FinancialStatementBase):
    required_line_items: ClassVar[tuple[str, ...]] = (
        "net_cash_from_operating_activities",
        "net_cash_from_investing_activities",
        "net_cash_from_financing_activities",
        "cash_and_cash_equivalents_end_of_period",
    )

    statement_type: StatementType = StatementType.CASH_FLOW_STATEMENT


class FinancialStatementNote(StrictContractModel):
    normalized_name: NonEmptyStr = Field(
        description="Canonical snake_case note name used by deterministic services.",
    )
    source_label: NonEmptyStr | None = Field(
        default=None,
        description="Original note caption from the financial statements.",
    )
    note_number: NonEmptyStr | None = Field(
        default=None,
        description="Source note number or label when available.",
    )
    extraction_status: LineItemExtractionStatus = Field(
        default=LineItemExtractionStatus.PRESENT,
        description="Whether the note was extracted, missing, or not applicable.",
    )
    source_reference: SourceReference | None = Field(
        default=None,
        description="Source location for this note.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Note extraction confidence from zero to one.",
    )
    summary: NonEmptyStr | None = Field(
        default=None,
        description="Normalized summary of the note content.",
    )
    related_line_items: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Normalized line items this note supports.",
    )
    missing_reason: NonEmptyStr | None = Field(
        default=None,
        description="Reason an expected note could not be extracted.",
    )

    @model_validator(mode="after")
    def validate_note_content_for_status(self) -> "FinancialStatementNote":
        if self.extraction_status == LineItemExtractionStatus.PRESENT and self.summary is None:
            raise ValueError("Present notes require a summary.")

        if self.extraction_status == LineItemExtractionStatus.MISSING:
            if self.summary is not None:
                raise ValueError("Missing notes cannot include a summary.")
            if self.missing_reason is None:
                raise ValueError("Missing notes require a missing_reason.")

        return self


class NotesToFinancialStatements(StrictContractModel):
    required_notes: ClassVar[tuple[str, ...]] = (
        "accounting_policies",
        "going_concern",
        "related_party_transactions",
        "commitments_and_contingencies",
    )

    statement_type: StatementType = StatementType.NOTES
    period: FinancialStatementPeriod = Field(description="Validated reporting period.")
    currency: CurrencyCode = Field(description="ISO 4217 statement currency code.")
    source_reference: SourceReference = Field(
        description="Source document reference for notes as a whole.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall notes extraction confidence from zero to one.",
    )
    missing_fields: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Notes-level fields that extraction could not validate.",
    )
    notes: list[FinancialStatementNote] = Field(
        default_factory=list,
        description="Normalized financial statement notes.",
    )

    @computed_field
    @property
    def missing_required_notes(self) -> list[str]:
        represented_names = {note.normalized_name for note in self.notes}
        missing_names = {
            note.normalized_name
            for note in self.notes
            if note.extraction_status == LineItemExtractionStatus.MISSING
        }
        absent_required_names = set(self.required_notes) - represented_names

        return sorted(missing_names | absent_required_names)

    @computed_field
    @property
    def manual_review_reasons(self) -> list[str]:
        reasons: list[str] = []

        if self.confidence < LOW_CONFIDENCE_THRESHOLD:
            reasons.append(
                f"Notes confidence {self.confidence:.2f} is below "
                f"{LOW_CONFIDENCE_THRESHOLD:.2f}."
            )

        for field_name in self.missing_fields:
            reasons.append(f"Missing notes field: {field_name}.")

        for note_name in self.missing_required_notes:
            reasons.append(f"Missing required note: {note_name}.")

        for note in self.notes:
            if note.confidence < LOW_CONFIDENCE_THRESHOLD:
                reasons.append(
                    f"Note {note.normalized_name} confidence {note.confidence:.2f} "
                    f"is below {LOW_CONFIDENCE_THRESHOLD:.2f}."
                )

        return reasons

    @computed_field
    @property
    def manual_review_required(self) -> bool:
        return bool(self.manual_review_reasons)


class FinancialStatementSet(StrictContractModel):
    target_company: NonEmptyStr = Field(description="Client or target company name.")
    balance_sheet: BalanceSheetStatement
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement
    notes: NotesToFinancialStatements

    @computed_field
    @property
    def manual_review_reasons(self) -> list[str]:
        reasons: list[str] = []

        for statement in (
            self.balance_sheet,
            self.income_statement,
            self.cash_flow_statement,
            self.notes,
        ):
            reasons.extend(statement.manual_review_reasons)

        return reasons

    @computed_field
    @property
    def manual_review_required(self) -> bool:
        return bool(self.manual_review_reasons)
