import json
import subprocess
import sys
from pathlib import Path

from app.run_full_planning import run_for_company
from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
)
from services.audit_planning_pipeline_service import run_audit_planning_pipeline
from storage.evidence_store import save_evidence_bundle


def test_full_planning_runner_imports_when_executed_as_script_path():
    project_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy; "
                "runpy.run_path('run_full_planning.py', "
                "run_name='direct_script_import_smoke')"
            ),
        ],
        cwd=project_root / "app",
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


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


def test_full_planning_runner_persists_source_registry_smoke_output(tmp_path: Path):
    result = run_for_company(
        "GreenLeaf Organics",
        evidence_output_dir=str(tmp_path / "evidence"),
        source_registry_output_dir=str(tmp_path / "source_registry"),
        memo_output_dir=str(tmp_path / "memos"),
    )

    assert result.evidence_path.exists()
    assert result.source_registry_path.exists()
    assert result.memo_path.exists()

    evidence_payload = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence_payload["source_support_required"] is True
    assert len(evidence_payload["source_records"]) == 2
    assert evidence_payload["source_records"][0]["publisher"] == "Sample Audit Archive"
    assert evidence_payload["source_registry_scoring_result"]["decision"] == "CONTINUE"
    assert (
        evidence_payload["evidence_data"]["source_registry_scoring_result"]["decision"]
        == "CONTINUE"
    )

    source_registry_payload = json.loads(
        result.source_registry_path.read_text(encoding="utf-8")
    )
    assert source_registry_payload["target_company"] == "GreenLeaf Organics"
    assert len(source_registry_payload["records"]) == 2

    memo_content = result.memo_path.read_text(encoding="utf-8")
    assert "## 8. Source Support" in memo_content
    assert "**Source registry scoring decision:** CONTINUE" in memo_content
    assert "Sample Audit Archive" in memo_content
