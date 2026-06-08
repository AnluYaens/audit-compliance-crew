from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas.financial_statements import (
    BalanceSheetStatement,
    CashFlowStatement,
    FinancialStatementNote,
    FinancialStatementPeriod,
    FinancialStatementSet,
    IncomeStatement,
    LineItemExtractionStatus,
    NormalizedLineItem,
    NotesToFinancialStatements,
    SourceReference,
)


def source_reference() -> SourceReference:
    return SourceReference(
        document_id="FS-2025-AUDITED",
        page_number=3,
        section="Audited financial statements",
    )


def reporting_period() -> FinancialStatementPeriod:
    return FinancialStatementPeriod(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        fiscal_year=2025,
    )


def line_item(name: str, amount: str) -> NormalizedLineItem:
    return NormalizedLineItem(
        normalized_name=name,
        source_label=name.replace("_", " ").title(),
        amount=Decimal(amount),
        confidence=0.95,
    )


def note(name: str) -> FinancialStatementNote:
    return FinancialStatementNote(
        normalized_name=name,
        source_label=name.replace("_", " ").title(),
        source_reference=source_reference(),
        confidence=0.95,
        summary=f"{name.replace('_', ' ').title()} disclosure was extracted.",
    )


def valid_balance_sheet() -> BalanceSheetStatement:
    return BalanceSheetStatement(
        period=reporting_period(),
        currency="EUR",
        source_reference=source_reference(),
        confidence=0.95,
        missing_fields=[],
        line_items=[
            line_item("cash_and_cash_equivalents", "100000"),
            line_item("total_assets", "1000000"),
            line_item("total_liabilities", "400000"),
            line_item("total_equity", "600000"),
        ],
    )


def valid_income_statement() -> IncomeStatement:
    return IncomeStatement(
        period=reporting_period(),
        currency="EUR",
        source_reference=source_reference(),
        confidence=0.95,
        missing_fields=[],
        line_items=[
            line_item("revenue", "2500000"),
            line_item("expenses", "2200000"),
            line_item("profit_before_tax", "300000"),
            line_item("net_income", "210000"),
        ],
    )


def valid_cash_flow_statement() -> CashFlowStatement:
    return CashFlowStatement(
        period=reporting_period(),
        currency="EUR",
        source_reference=source_reference(),
        confidence=0.95,
        missing_fields=[],
        line_items=[
            line_item("net_cash_from_operating_activities", "325000"),
            line_item("net_cash_from_investing_activities", "-125000"),
            line_item("net_cash_from_financing_activities", "-50000"),
            line_item("cash_and_cash_equivalents_end_of_period", "100000"),
        ],
    )


def valid_notes() -> NotesToFinancialStatements:
    return NotesToFinancialStatements(
        period=reporting_period(),
        currency="EUR",
        source_reference=source_reference(),
        confidence=0.95,
        missing_fields=[],
        notes=[
            note("accounting_policies"),
            note("going_concern"),
            note("related_party_transactions"),
            note("commitments_and_contingencies"),
        ],
    )


def test_valid_statement_schema_passes():
    statements = FinancialStatementSet(
        target_company="Example GmbH",
        balance_sheet=valid_balance_sheet(),
        income_statement=valid_income_statement(),
        cash_flow_statement=valid_cash_flow_statement(),
        notes=valid_notes(),
    )

    assert statements.manual_review_required is False
    assert statements.balance_sheet.currency == "EUR"
    assert statements.income_statement.period.end_date == date(2025, 12, 31)
    assert statements.cash_flow_statement.source_reference.document_id == "FS-2025-AUDITED"
    assert statements.notes.missing_fields == []


def test_missing_period_fails_validation():
    with pytest.raises(ValidationError):
        BalanceSheetStatement(
            currency="EUR",
            source_reference=source_reference(),
            confidence=0.95,
            missing_fields=[],
            line_items=[
                line_item("cash_and_cash_equivalents", "100000"),
                line_item("total_assets", "1000000"),
                line_item("total_liabilities", "400000"),
                line_item("total_equity", "600000"),
            ],
        )


def test_missing_required_line_item_is_represented():
    missing_total_assets = NormalizedLineItem(
        normalized_name="total_assets",
        source_label="Total Assets",
        extraction_status=LineItemExtractionStatus.MISSING,
        amount=None,
        confidence=0.95,
        missing_reason="The balance sheet total assets caption was not extracted.",
    )

    statement = BalanceSheetStatement(
        period=reporting_period(),
        currency="EUR",
        source_reference=source_reference(),
        confidence=0.95,
        missing_fields=[],
        line_items=[
            line_item("cash_and_cash_equivalents", "100000"),
            missing_total_assets,
            line_item("total_liabilities", "400000"),
            line_item("total_equity", "600000"),
        ],
    )

    assert statement.line_items[1].amount is None
    assert statement.missing_required_line_items == ["total_assets"]
    assert statement.manual_review_required is True
    assert "Missing required line item: total_assets." in statement.manual_review_reasons


def test_low_confidence_extraction_can_be_represented():
    statement = valid_income_statement().model_copy(
        update={
            "confidence": 0.50,
            "missing_fields": ["comparative_period"],
        }
    )

    assert statement.confidence == 0.50
    assert statement.missing_fields == ["comparative_period"]
    assert statement.manual_review_required is True
    assert "Statement confidence 0.50 is below 0.75." in statement.manual_review_reasons
    assert "Missing statement field: comparative_period." in statement.manual_review_reasons
