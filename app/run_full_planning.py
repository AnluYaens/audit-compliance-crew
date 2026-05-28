from __future__ import annotations

from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
)
from services.audit_planning_pipeline_service import run_audit_planning_pipeline
from storage.evidence_store import save_evidence_bundle


def build_default_materiality_request(company_name: str) -> MaterialityRequest:
    return MaterialityRequest(
        target_company=company_name,
        benchmark_type="profit_before_tax",
        benchmark_amount=1_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Prototype planning materiality calculation using profit before tax.",
    )


def build_default_risk_assessment_request(company_name: str) -> RiskAssessmentRequest:
    return RiskAssessmentRequest(
        target_company=company_name,
        indicators=[
            RiskIndicator(
                area=FinancialStatementArea.CASH,
                assertion=AuditAssertion.EXISTENCE,
                description="Cash balance is simple and reconciled for the prototype scenario.",
                likelihood=1,
                magnitude=2,
            )
        ],
    )


def run_for_company(company_name: str) -> None:
    materiality_request = build_default_materiality_request(company_name)
    risk_assessment_request = build_default_risk_assessment_request(company_name)

    bundle = run_audit_planning_pipeline(
        company_name=company_name,
        materiality_request=materiality_request,
        risk_assessment_request=risk_assessment_request,
    )

    output_path = save_evidence_bundle(bundle)

    print("=" * 80)
    print(f"Company: {company_name}")
    print(f"Run ID: {bundle.run_id}")
    print(f"Final decision: {bundle.final_decision}")
    print(f"Manual review reasons: {bundle.manual_review_reasons}")
    print(f"Evidence saved to: {output_path}")
    print("=" * 80)


def main() -> None:
    companies = [
        "Quantum Cybernetics",
        "Vanguard Mining Corp",
        "Apex Energy Group",
        "GreenLeaf Organics",
        "Unknown Company ABC",
    ]

    for company in companies:
        run_for_company(company)


if __name__ == "__main__":
    main()