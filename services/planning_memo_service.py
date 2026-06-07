from __future__ import annotations

from schemas.evidence import AuditPlanningEvidenceBundle
from schemas.source_registry import SourceRecord, SourceRegistryScoringResult


def _format_list(items: list[str]) -> str:
    if not items:
        return "- None"

    return "\n".join(f"- {item}" for item in items)


def _format_money(value: object) -> str:
    if isinstance(value, int | float):
        return f"{value:,.2f}"

    return "Not available"


def _format_yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _format_table_cell(value: object) -> str:
    if value is None:
        return "Not available"

    return str(value).replace("|", "\\|").replace("\n", " ")


def _source_identity(source: SourceRecord) -> str:
    return source.url or source.identifier or "Not available"


def _source_retrieval_date(source: SourceRecord) -> str:
    return source.retrieval_date.date().isoformat()


def _format_source_results_table(
    scoring_result: SourceRegistryScoringResult,
) -> str:
    if not scoring_result.source_results:
        return "- No source records available."

    rows = [
        "| # | Source | Type | Publisher | Retrieved | Status | Decision | Score |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for index, source_result in enumerate(scoring_result.source_results, start=1):
        source = source_result.source
        rows.append(
            (
                f"| {index} "
                f"| {_format_table_cell(_source_identity(source))} "
                f"| {_format_table_cell(source.source_type.value)} "
                f"| {_format_table_cell(source.publisher)} "
                f"| {_format_table_cell(_source_retrieval_date(source))} "
                f"| {_format_table_cell(source_result.status)} "
                f"| {_format_table_cell(source_result.decision.value)} "
                f"| {source_result.total_score:.2f} |"
            )
        )

    return "\n".join(rows)


def _format_source_records_table(source_records: list[SourceRecord]) -> str:
    if not source_records:
        return "- No source records available."

    rows = [
        "| # | Source | Type | Publisher | Retrieved | Confidence | Relevance |",
        "|---|---|---|---|---|---|---|",
    ]
    for index, source in enumerate(source_records, start=1):
        rows.append(
            (
                f"| {index} "
                f"| {_format_table_cell(_source_identity(source))} "
                f"| {_format_table_cell(source.source_type.value)} "
                f"| {_format_table_cell(source.publisher)} "
                f"| {_format_table_cell(_source_retrieval_date(source))} "
                f"| {source.confidence:.2f} "
                f"| {source.relevance:.2f} |"
            )
        )

    return "\n".join(rows)


def _format_source_support_section(bundle: AuditPlanningEvidenceBundle) -> str:
    scoring_result = bundle.source_registry_scoring_result

    if scoring_result is None:
        registry_decision = "Not available"
        registry_status = "Not available"
        manual_review_reasons = []
        source_table = _format_source_records_table(bundle.source_records)
    else:
        registry_decision = scoring_result.decision.value
        registry_status = scoring_result.status
        manual_review_reasons = list(scoring_result.manual_review_reasons)
        source_table = _format_source_results_table(scoring_result)

    return f"""**Source support required:** {_format_yes_no(bundle.source_support_required)}

**Source registry scoring decision:** {registry_decision}

**Source quality/status:** {registry_status}

**Decision impact:** Reported from the evidence bundle only; this memo does not create or override decisions.

**Source registry manual review reasons:**

{_format_list(manual_review_reasons)}

**Source records:**

{source_table}"""


def generate_planning_memo(bundle: AuditPlanningEvidenceBundle) -> str:
    evidence = bundle.evidence_data

    materiality = evidence.get("materiality_result", {})
    risk_assessment = evidence.get("risk_assessment_result", {})
    audit_response = evidence.get("audit_response_result", {})

    assessed_risks = risk_assessment.get("assessed_risks", [])
    procedures = audit_response.get("procedures", [])

    risk_lines = []
    for risk in assessed_risks:
        risk_lines.append(
            (
                f"- {risk.get('area')} / {risk.get('assertion')}: "
                f"{risk.get('risk_level')} ({risk.get('risk_type')}) — "
                f"{risk.get('rationale')}"
            )
        )

    procedure_lines = []
    for procedure in procedures:
        procedure_lines.append(
            (
                f"- {procedure.get('area')} — {procedure.get('procedure_type')}: "
                f"{procedure.get('description')}"
            )
        )

    memo = f"""# Audit Planning Memo

## 1. Engagement Overview

**Target company:** {bundle.target_company}

**Engagement type:** {bundle.engagement_type}

**Run ID:** {bundle.run_id}

**Final decision:** {bundle.final_decision.value}

## 2. Governance Note

This memo was generated from a validated evidence bundle.

The final decision was determined by deterministic Python services, not by an LLM.

The LLM or memo generator may assist with formatting and narrative presentation, but it does not override compliance decisions.

## 3. Manual Review Reasons

{_format_list(bundle.manual_review_reasons)}

## 4. Acceptance and Screening Summary

**KYC result:** {evidence.get("kyc_result", "Not available")}

**Independence result:** {evidence.get("independence_result", "Not available")}

**Sanctions result:** {evidence.get("sanctions_result", "Not available")}

**Acceptance decision:** {evidence.get("acceptance_decision", "Not available")}

## 5. Materiality Summary

**Benchmark type:** {materiality.get("benchmark_type", "Not available")}

**Benchmark amount:** {_format_money(materiality.get("benchmark_amount"))}

**Overall materiality:** {_format_money(materiality.get("overall_materiality"))}

**Performance materiality:** {_format_money(materiality.get("performance_materiality"))}

**Clearly trivial threshold:** {_format_money(materiality.get("clearly_trivial_threshold"))}

**Materiality decision:** {materiality.get("decision", "Not available")}

## 6. Risk Assessment Summary

{chr(10).join(risk_lines) if risk_lines else "- No assessed risks available."}

## 7. Audit Response Plan

{chr(10).join(procedure_lines) if procedure_lines else "- No audit response procedures available."}

## 8. Source Support

{_format_source_support_section(bundle)}

## 9. Conclusion

The planning outcome for **{bundle.target_company}** is **{bundle.final_decision.value}**.

This conclusion is based on the structured evidence bundle and deterministic routing rules.
"""

    return memo
