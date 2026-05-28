from __future__ import annotations

from schemas.audit_response import (
    AuditProcedureType,
    AuditResponseProcedure,
    AuditResponseRequest,
    AuditResponseResult,
)
from schemas.decisions import FinalDecision
from schemas.risk_assessment import (
    AssessedRisk,
    FinancialStatementArea,
    RiskLevel,
    RiskType,
)


def base_procedure_for_area(risk: AssessedRisk) -> AuditResponseProcedure:
    if risk.area == FinancialStatementArea.REVENUE:
        return AuditResponseProcedure(
            area=risk.area,
            procedure_type=AuditProcedureType.SUBSTANTIVE_TESTING,
            description="Perform substantive testing over selected revenue transactions and agree samples to supporting documentation.",
            linked_risk_level=risk.risk_level,
            linked_risk_type=risk.risk_type,
        )

    if risk.area == FinancialStatementArea.INVENTORY:
        return AuditResponseProcedure(
            area=risk.area,
            procedure_type=AuditProcedureType.INSPECTION,
            description="Inspect inventory records and perform procedures over valuation and existence where relevant.",
            linked_risk_level=risk.risk_level,
            linked_risk_type=risk.risk_type,
        )

    if risk.area == FinancialStatementArea.CASH:
        return AuditResponseProcedure(
            area=risk.area,
            procedure_type=AuditProcedureType.RECALCULATION,
            description="Reconcile cash balances to supporting bank documentation and recalculate relevant balances.",
            linked_risk_level=risk.risk_level,
            linked_risk_type=risk.risk_type,
        )

    if risk.area == FinancialStatementArea.MANAGEMENT_OVERRIDE:
        return AuditResponseProcedure(
            area=risk.area,
            procedure_type=AuditProcedureType.JOURNAL_ENTRY_TESTING,
            description="Perform journal entry testing and review unusual manual entries for management override risk.",
            linked_risk_level=risk.risk_level,
            linked_risk_type=risk.risk_type,
        )

    if risk.area == FinancialStatementArea.GOING_CONCERN:
        return AuditResponseProcedure(
            area=risk.area,
            procedure_type=AuditProcedureType.ANALYTICAL_PROCEDURE,
            description="Evaluate going concern indicators and review management's assessment and supporting cash flow information.",
            linked_risk_level=risk.risk_level,
            linked_risk_type=risk.risk_type,
        )

    return AuditResponseProcedure(
        area=risk.area,
        procedure_type=AuditProcedureType.INSPECTION,
        description="Inspect relevant supporting documentation for the assessed financial statement area.",
        linked_risk_level=risk.risk_level,
        linked_risk_type=risk.risk_type,
    )


def enhanced_procedure_for_high_risk(risk: AssessedRisk) -> AuditResponseProcedure | None:
    if risk.risk_level not in {RiskLevel.ELEVATED, RiskLevel.SIGNIFICANT}:
        return None

    return AuditResponseProcedure(
        area=risk.area,
        procedure_type=AuditProcedureType.TEST_OF_CONTROLS,
        description="Design enhanced procedures and consider control testing due to elevated or significant assessed risk.",
        linked_risk_level=risk.risk_level,
        linked_risk_type=risk.risk_type,
    )


def fraud_procedure(risk: AssessedRisk) -> AuditResponseProcedure | None:
    if risk.risk_type != RiskType.FRAUD:
        return None

    return AuditResponseProcedure(
        area=risk.area,
        procedure_type=AuditProcedureType.JOURNAL_ENTRY_TESTING,
        description="Perform targeted journal entry testing and professional skepticism procedures due to fraud risk indicator.",
        linked_risk_level=risk.risk_level,
        linked_risk_type=risk.risk_type,
    )


def design_audit_response(request: AuditResponseRequest) -> AuditResponseResult:
    procedures: list[AuditResponseProcedure] = []
    manual_review_reasons: list[str] = []

    for risk in request.assessed_risks:
        procedures.append(base_procedure_for_area(risk))

        enhanced = enhanced_procedure_for_high_risk(risk)
        if enhanced is not None:
            procedures.append(enhanced)
            manual_review_reasons.append(
                f"{risk.area.value}: enhanced audit response required for {risk.risk_level.value} risk."
            )

        fraud = fraud_procedure(risk)
        if fraud is not None:
            procedures.append(fraud)
            manual_review_reasons.append(
                f"{risk.area.value}: fraud response procedures required."
            )

        if risk.risk_type == RiskType.GOING_CONCERN:
            manual_review_reasons.append(
                f"{risk.area.value}: going concern response requires manual review."
            )

    decision = (
        FinalDecision.MANUAL_REVIEW
        if manual_review_reasons
        else FinalDecision.CONTINUE
    )

    return AuditResponseResult(
        decision=decision,
        target_company=request.target_company,
        procedures=procedures,
        manual_review_reasons=manual_review_reasons,
    )