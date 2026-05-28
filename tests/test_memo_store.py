from pathlib import Path

from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
)
from services.audit_planning_pipeline_service import run_audit_planning_pipeline
from services.planning_memo_service import generate_planning_memo
from storage.memo_store import save_planning_memo


def test_planning_memo_can_be_saved(tmp_path: Path):
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

    memo = generate_planning_memo(bundle)

    output_path = save_planning_memo(
        bundle=bundle,
        memo_content=memo,
        output_dir=str(tmp_path),
    )

    assert output_path.exists()
    assert output_path.suffix == ".md"

    saved_content = output_path.read_text(encoding="utf-8")

    assert "# Audit Planning Memo" in saved_content
    assert "GreenLeaf Organics" in saved_content
    assert bundle.final_decision.value in saved_content