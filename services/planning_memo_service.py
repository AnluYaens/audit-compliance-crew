from __future__ import annotations

from schemas.evidence import AuditPlanningEvidenceBundle


def _format_list(items: list[str]) -> str:
    if not items:
        return "- None"

    return "\n".join(f"- {item}" for item in items)


def _format_money(value: object) -> str:
    if isinstance(value, int | float):
        return f"{value:,.2f}"

    return "Not available"


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

## 8. Conclusion

The planning outcome for **{bundle.target_company}** is **{bundle.final_decision.value}**.

This conclusion is based on the structured evidence bundle and deterministic routing rules.
"""

    return memo