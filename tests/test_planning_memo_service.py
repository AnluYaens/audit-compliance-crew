from datetime import datetime, timezone

from schemas.materiality import MaterialityRequest
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskIndicator,
)
from schemas.source_registry import SourceRecord, SourceType
from services.audit_planning_pipeline_service import run_audit_planning_pipeline
from services.planning_memo_service import generate_planning_memo


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


def test_planning_memo_contains_core_sections():
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

    assert "# Audit Planning Memo" in memo
    assert "Engagement Overview" in memo
    assert "Governance Note" in memo
    assert "Materiality Summary" in memo
    assert "Risk Assessment Summary" in memo
    assert "Audit Response Plan" in memo
    assert "Source Support" in memo
    assert "GreenLeaf Organics" in memo
    assert bundle.final_decision.value in memo


def test_planning_memo_states_llm_did_not_decide():
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

    assert "not by an LLM" in memo
    assert "does not override compliance decisions" in memo


def test_planning_memo_reports_source_registry_support():
    company_name = "GreenLeaf Organics"
    source = reliable_source()

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
        source_records=[source],
    )

    memo = generate_planning_memo(bundle)

    assert "**Source support required:** Yes" in memo
    assert "**Source registry scoring decision:** CONTINUE" in memo
    assert "**Source quality/status:** SUCCESS" in memo
    assert "| # | Source | Type | Publisher | Retrieved | Status | Decision | Score |" in memo
    assert "https://example.com/regulatory-filing" in memo
    assert "Example Regulator" in memo
    assert "| 1 | https://example.com/regulatory-filing | REGULATORY | Example Regulator | 2025-01-01 | SUCCESS | CONTINUE |" in memo
    assert "**Source registry manual review reasons:**\n\n- None" in memo


def test_planning_memo_reports_source_manual_review_reasons_without_new_decision():
    company_name = "GreenLeaf Organics"
    weak_source = reliable_source().model_copy(update={"confidence": 0.5})

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
        source_records=[weak_source],
    )

    memo = generate_planning_memo(bundle)

    assert "**Source registry scoring decision:** MANUAL_REVIEW" in memo
    assert "**Source quality/status:** REVIEW_REQUIRED" in memo
    assert "Source 1: Source confidence 0.50 is below 0.75." in memo
    assert "| 1 | https://example.com/regulatory-filing | REGULATORY | Example Regulator | 2025-01-01 | REVIEW_REQUIRED | MANUAL_REVIEW |" in memo
    assert f"The planning outcome for **{company_name}** is **{bundle.final_decision.value}**." in memo
    assert "**Decision impact:** Reported from the evidence bundle only; this memo does not create or override decisions." in memo
