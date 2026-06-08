from datetime import date
from decimal import Decimal

from schemas.financial_statements import (
    FinancialLineItemExtraction,
    FinancialStatementNormalizationRequest,
    FinancialStatementPeriod,
    LineItemExtractionStatus,
    SourceReference,
    StatementType,
)
from services.financial_normalization_service import normalize_financial_statement


def source_reference(section: str = "Balance sheet") -> SourceReference:
    return SourceReference(
        document_id="FS-2025-AUDITED",
        page_number=4,
        section=section,
    )


def reporting_period() -> FinancialStatementPeriod:
    return FinancialStatementPeriod(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        fiscal_year=2025,
    )


def extraction(
    source_label: str,
    amount: str,
    confidence: float = 0.95,
) -> FinancialLineItemExtraction:
    return FinancialLineItemExtraction(
        source_label=source_label,
        amount=Decimal(amount),
        source_reference=source_reference(),
        confidence=confidence,
    )


def balance_sheet_request(
    line_items: list[FinancialLineItemExtraction],
    confidence: float = 0.95,
) -> FinancialStatementNormalizationRequest:
    return FinancialStatementNormalizationRequest(
        statement_type=StatementType.BALANCE_SHEET,
        period=reporting_period(),
        currency="EUR",
        source_reference=source_reference(),
        confidence=confidence,
        missing_fields=[],
        line_items=line_items,
    )


def test_normalizes_complete_statement_input():
    request = balance_sheet_request(
        [
            extraction("Cash and bank balances", "100000"),
            extraction("Total assets", "1000000"),
            extraction("Total liabilities", "400000"),
            extraction("Shareholders' equity", "600000"),
        ]
    )

    result = normalize_financial_statement(request)

    assert result.status == "SUCCESS"
    assert result.manual_review_flags == []
    assert [
        item.normalized_name for item in result.statement.line_items
    ] == [
        "cash_and_cash_equivalents",
        "total_assets",
        "total_liabilities",
        "total_equity",
    ]
    assert result.statement.line_items[0].amount == Decimal("100000")
    assert result.statement.line_items[0].source_reference == source_reference()
    assert result.statement.line_items[0].confidence == 0.95


def test_flags_missing_key_line_items():
    request = balance_sheet_request(
        [
            extraction("Cash and bank balances", "100000"),
            extraction("Total liabilities", "400000"),
            extraction("Shareholders' equity", "600000"),
        ]
    )

    result = normalize_financial_statement(request)

    assert result.status == "REVIEW_REQUIRED"
    missing_total_assets = next(
        item
        for item in result.statement.line_items
        if item.normalized_name == "total_assets"
    )
    assert missing_total_assets.extraction_status == LineItemExtractionStatus.MISSING
    assert "Missing required line item: total_assets." in result.manual_review_flags


def test_flags_contradictory_values():
    request = balance_sheet_request(
        [
            extraction("Cash and bank balances", "100000"),
            extraction("Total assets", "1000000"),
            extraction("Assets", "900000"),
            extraction("Total liabilities", "400000"),
            extraction("Shareholders' equity", "600000"),
        ]
    )

    result = normalize_financial_statement(request)

    assert result.status == "REVIEW_REQUIRED"
    assert any(
        flag.startswith("Contradictory values for total_assets:")
        for flag in result.manual_review_flags
    )
    assert [
        item.normalized_name for item in result.statement.line_items
    ].count("total_assets") == 1


def test_flags_duplicate_values():
    request = balance_sheet_request(
        [
            extraction("Cash and bank balances", "100000"),
            extraction("Cash", "100000"),
            extraction("Total assets", "1000000"),
            extraction("Total liabilities", "400000"),
            extraction("Shareholders' equity", "600000"),
        ]
    )

    result = normalize_financial_statement(request)

    assert result.status == "REVIEW_REQUIRED"
    assert (
        "Duplicate values for cash_and_cash_equivalents were extracted and collapsed."
        in result.manual_review_flags
    )
    assert [
        item.normalized_name for item in result.statement.line_items
    ].count("cash_and_cash_equivalents") == 1


def test_flags_low_confidence():
    request = balance_sheet_request(
        [
            extraction("Cash and bank balances", "100000", confidence=0.50),
            extraction("Total assets", "1000000"),
            extraction("Total liabilities", "400000"),
            extraction("Shareholders' equity", "600000"),
        ]
    )

    result = normalize_financial_statement(request)

    assert result.status == "REVIEW_REQUIRED"
    assert (
        "Line item cash_and_cash_equivalents confidence 0.50 is below 0.75."
        in result.manual_review_flags
    )
