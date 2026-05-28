from pathlib import Path

from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
)
from services.audit_planning_pipeline_service import run_audit_planning_pipeline
from storage.evidence_store import save_evidence_bundle


def test_full_planning_bundle_can_be_saved(tmp_path: Path):
    company_name = "GreenLeaf Organics"

    materiality_request = MaterialityRequest(
        target_company=company_name,
        benchmark_type="profit_before_tax",
        benchmark_amount=1_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Prototype planning materiality calculation.",
    )

    risk_assessment_request = RiskAssessmentRequest(
        target_company=company_name,
        indicators=[
            RiskIndicator(
                area=FinancialStatementArea.CASH,
                assertion=AuditAssertion.EXISTENCE,
                description="Cash balance is simple and reconciled.",
                likelihood=1,
                magnitude=2,
            )
        ],
    )

    bundle = run_audit_planning_pipeline(
        company_name=company_name,
        materiality_request=materiality_request,
        risk_assessment_request=risk_assessment_request,
    )

    output_path = save_evidence_bundle(
        bundle=bundle,
        output_dir=str(tmp_path),
    )

    assert output_path.exists()
    assert output_path.suffix == ".json"

    saved_content = output_path.read_text(encoding="utf-8")

    assert "GreenLeaf Organics" in saved_content
    assert "materiality_result" in saved_content
    assert "risk_assessment_result" in saved_content
    assert "audit_response_result" in saved_content