from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

from schemas.financial_statements import (
    BalanceSheetStatement,
    CashFlowStatement,
    FinancialLineItemExtraction,
    FinancialStatementBase,
    FinancialStatementNormalizationRequest,
    FinancialStatementNormalizationResult,
    IncomeStatement,
    LineItemExtractionStatus,
    NormalizedLineItem,
    StatementType,
)


STATEMENT_MODELS: dict[StatementType, type[FinancialStatementBase]] = {
    StatementType.BALANCE_SHEET: BalanceSheetStatement,
    StatementType.INCOME_STATEMENT: IncomeStatement,
    StatementType.CASH_FLOW_STATEMENT: CashFlowStatement,
}


def _canonical_key(value: str) -> str:
    normalized = value.replace("&", " and ")
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", normalized)
    return " ".join(normalized.lower().split())


def _snake_case(value: str) -> str:
    return _canonical_key(value).replace(" ", "_")


def _alias_map(labels_by_name: dict[str, tuple[str, ...]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for normalized_name, labels in labels_by_name.items():
        aliases[_canonical_key(normalized_name)] = normalized_name
        for label in labels:
            aliases[_canonical_key(label)] = normalized_name
    return aliases


LINE_ITEM_ALIASES: dict[StatementType, dict[str, str]] = {
    StatementType.BALANCE_SHEET: _alias_map(
        {
            "cash_and_cash_equivalents": (
                "cash",
                "cash and cash equivalents",
                "cash and bank balances",
                "cash at bank and in hand",
            ),
            "total_assets": (
                "assets",
                "total assets",
            ),
            "total_liabilities": (
                "liabilities",
                "total liabilities",
            ),
            "total_equity": (
                "equity",
                "total equity",
                "shareholders equity",
                "shareholders' equity",
                "stockholders equity",
            ),
        }
    ),
    StatementType.INCOME_STATEMENT: _alias_map(
        {
            "revenue": (
                "revenue",
                "sales",
                "turnover",
                "total revenue",
            ),
            "expenses": (
                "expenses",
                "total expenses",
                "operating expenses",
            ),
            "profit_before_tax": (
                "profit before tax",
                "income before tax",
                "earnings before tax",
                "pbt",
            ),
            "net_income": (
                "net income",
                "net profit",
                "profit for the year",
            ),
        }
    ),
    StatementType.CASH_FLOW_STATEMENT: _alias_map(
        {
            "net_cash_from_operating_activities": (
                "net cash from operating activities",
                "net cash provided by operating activities",
                "cash flows from operating activities",
            ),
            "net_cash_from_investing_activities": (
                "net cash from investing activities",
                "net cash used in investing activities",
                "cash flows from investing activities",
            ),
            "net_cash_from_financing_activities": (
                "net cash from financing activities",
                "net cash used in financing activities",
                "cash flows from financing activities",
            ),
            "cash_and_cash_equivalents_end_of_period": (
                "cash and cash equivalents at end of period",
                "cash and cash equivalents end of period",
                "cash at end of period",
                "closing cash and cash equivalents",
            ),
        }
    ),
}


def _normalize_name(statement_type: StatementType, source_label: str) -> str:
    aliases = LINE_ITEM_ALIASES[statement_type]
    key = _canonical_key(source_label)
    return aliases.get(key, _snake_case(source_label))


def _missing_line_item(normalized_name: str) -> NormalizedLineItem:
    return NormalizedLineItem(
        normalized_name=normalized_name,
        source_label=normalized_name.replace("_", " ").title(),
        extraction_status=LineItemExtractionStatus.MISSING,
        amount=None,
        confidence=1.0,
        missing_reason=f"{normalized_name} was not present in the extracted statement data.",
    )


def _normalize_line_item(
    statement_type: StatementType,
    item: FinancialLineItemExtraction,
) -> NormalizedLineItem:
    return NormalizedLineItem(
        normalized_name=_normalize_name(statement_type, item.source_label),
        source_label=item.source_label,
        amount=item.amount,
        extraction_status=item.extraction_status,
        source_reference=item.source_reference,
        confidence=item.confidence,
        missing_reason=item.missing_reason,
    )


def _collapse_duplicates(
    line_items: list[NormalizedLineItem],
) -> tuple[list[NormalizedLineItem], list[str]]:
    by_name: dict[str, list[NormalizedLineItem]] = defaultdict(list)
    for item in line_items:
        by_name[item.normalized_name].append(item)

    collapsed: list[NormalizedLineItem] = []
    contradiction_flags: list[str] = []

    for normalized_name, items in by_name.items():
        if len(items) > 1:
            contradiction_flags.append(
                f"Duplicate values for {normalized_name} were extracted and collapsed."
            )

        present_amounts = [
            item.amount
            for item in items
            if item.extraction_status
            in {LineItemExtractionStatus.PRESENT, LineItemExtractionStatus.ESTIMATED}
        ]
        distinct_amounts = sorted({amount for amount in present_amounts if amount is not None})
        if len(distinct_amounts) > 1:
            formatted_amounts = ", ".join(str(amount) for amount in distinct_amounts)
            contradiction_flags.append(
                f"Contradictory values for {normalized_name}: {formatted_amounts}."
            )

        collapsed.append(items[0])

    return collapsed, contradiction_flags


def _amount_by_name(line_items: list[NormalizedLineItem]) -> dict[str, Decimal]:
    return {
        item.normalized_name: item.amount
        for item in line_items
        if item.amount is not None
        and item.extraction_status
        in {LineItemExtractionStatus.PRESENT, LineItemExtractionStatus.ESTIMATED}
    }


def _balance_sheet_consistency_flags(line_items: list[NormalizedLineItem]) -> list[str]:
    amounts = _amount_by_name(line_items)
    required_names = {"total_assets", "total_liabilities", "total_equity"}

    if not required_names.issubset(amounts):
        return []

    expected_assets = amounts["total_liabilities"] + amounts["total_equity"]
    if amounts["total_assets"] == expected_assets:
        return []

    return [
        (
            "Contradictory balance sheet equation: total_assets "
            f"{amounts['total_assets']} does not equal total_liabilities plus "
            f"total_equity {expected_assets}."
        )
    ]


def _contradiction_flags(
    statement_type: StatementType,
    line_items: list[NormalizedLineItem],
) -> list[str]:
    if statement_type == StatementType.BALANCE_SHEET:
        return _balance_sheet_consistency_flags(line_items)

    return []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)

    return deduped


def normalize_financial_statement(
    request: FinancialStatementNormalizationRequest,
) -> FinancialStatementNormalizationResult:
    statement_model = STATEMENT_MODELS[request.statement_type]

    normalized_items = [
        _normalize_line_item(request.statement_type, item)
        for item in request.line_items
        if item.extraction_status != LineItemExtractionStatus.NOT_APPLICABLE
    ]
    normalized_items, duplicate_flags = _collapse_duplicates(normalized_items)

    represented_names = {item.normalized_name for item in normalized_items}
    for required_name in statement_model.required_line_items:
        if required_name not in represented_names:
            normalized_items.append(_missing_line_item(required_name))

    statement = statement_model(
        period=request.period,
        currency=request.currency,
        source_reference=request.source_reference,
        confidence=request.confidence,
        missing_fields=request.missing_fields,
        line_items=normalized_items,
    )

    manual_review_flags = _dedupe(
        statement.manual_review_reasons
        + duplicate_flags
        + _contradiction_flags(request.statement_type, normalized_items)
    )

    return FinancialStatementNormalizationResult(
        status="REVIEW_REQUIRED" if manual_review_flags else "SUCCESS",
        statement=statement,
        manual_review_flags=manual_review_flags,
    )
