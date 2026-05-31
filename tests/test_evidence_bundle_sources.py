from datetime import datetime, timezone
from pathlib import Path

from schemas.decisions import FinalDecision
from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
)
from schemas.source_registry import SourceRecord, SourceType
from services.audit_planning_pipeline_service import run_audit_planning_pipeline
from storage.evidence_store import load_evidence_bundle, save_evidence_bundle


def valid_materiality_request(company_name: str = "GreenLeaf Organics") -> MaterialityRequest:
    return MaterialityRequest(
        target_company=company_name,
        benchmark_type="profit_before_tax",
        benchmark_amount=1_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Profit before tax is stable and appropriate for this prototype.",
    )


def low_risk_assessment_request(company_name: str = "GreenLeaf Organics") -> RiskAssessmentRequest:
    return RiskAssessmentRequest(
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


def reliable_source() -> SourceRecord:
    return SourceRecord(
        url="https://example.com/regulatory-filing",
        source_type=SourceType.REGULATORY,
        publisher="Example Regulator",
        retrieval_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        confidence=0.95,
        freshness_days=5_000,
        relevance=0.9,
        notes="Regulatory filing metadata captured for deterministic scoring.",
    )


def test_evidence_bundle_stores_source_references():
    source = reliable_source()

    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=valid_materiality_request(),
        risk_assessment_request=low_risk_assessment_request(),
        source_records=[source],
    )

    assert bundle.final_decision == FinalDecision.CONTINUE
    assert bundle.source_records == [source]
    assert bundle.source_registry_scoring_result is not None
    assert bundle.source_registry_scoring_result.decision == FinalDecision.CONTINUE
    assert bundle.source_registry_scoring_result.source_results[0].source == source


def test_weak_source_creates_manual_review_reason():
    weak_source = reliable_source().model_copy(update={"confidence": 0.5})

    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=valid_materiality_request(),
        risk_assessment_request=low_risk_assessment_request(),
        source_records=[weak_source],
    )

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert bundle.source_registry_scoring_result is not None
    assert bundle.source_registry_scoring_result.decision == FinalDecision.MANUAL_REVIEW
    assert any("Source confidence" in reason for reason in bundle.manual_review_reasons)


def test_missing_source_support_does_not_allow_continue():
    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=valid_materiality_request(),
        risk_assessment_request=low_risk_assessment_request(),
        require_source_support=True,
    )

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert bundle.source_support_required is True
    assert bundle.source_records == []
    assert bundle.source_registry_scoring_result is not None
    assert "Source registry contains no source records." in bundle.manual_review_reasons


def test_stored_bundle_can_be_reloaded_with_source_metadata(tmp_path: Path):
    source = reliable_source()
    bundle = run_audit_planning_pipeline(
        company_name="GreenLeaf Organics",
        materiality_request=valid_materiality_request(),
        risk_assessment_request=low_risk_assessment_request(),
        source_records=[source],
    )

    output_path = save_evidence_bundle(bundle=bundle, output_dir=str(tmp_path))
    reloaded_bundle = load_evidence_bundle(output_path)

    assert reloaded_bundle.source_records == [source]
    assert reloaded_bundle.source_registry_scoring_result is not None
    assert reloaded_bundle.source_registry_scoring_result.decision == FinalDecision.CONTINUE
    assert (
        reloaded_bundle.source_registry_scoring_result.source_results[0].source.url
        == source.url
    )
