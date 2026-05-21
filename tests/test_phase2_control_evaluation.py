from manual_controls.all_controls import MANUAL_CONTROLS
from orchestration.planning_orchestrator import run_audit_planning_workflow
from schemas.decisions import FinalDecision


def test_complete_evidence_allows_continue():
    evidence = {
        "target_company": "Example GmbH",
        "kyc_result": "completed",
        "sanctions_result": "clear",
        "independence_result": "clear",
        "acceptance_decision": "preliminarily_acceptable",
        "manual_review_reasons": [],
        "financial_statement_basis": "profit_before_tax",
        "selected_benchmark": "profit_before_tax",
        "benchmark_amount": 1_000_000,
        "materiality_percentage": 0.05,
        "overall_materiality": 50_000,
        "performance_materiality": 37_500,
        "clearly_trivial_threshold": 2_500,
        "entity_understanding": "Documented.",
        "financial_statement_areas": ["Revenue"],
        "assertions": ["Occurrence"],
        "risk_indicators": ["Unusual revenue growth"],
        "identified_risks": [{"area": "Revenue", "risk_level": "Elevated"}],
        "risk_level": "Elevated",
        "affected_assertions": ["Occurrence"],
        "evidence_references": ["sample.csv"],
    }

    bundle = run_audit_planning_workflow(
        target_company="Example GmbH",
        evidence_data=evidence,
    )

    assert len(MANUAL_CONTROLS) >= 3
    assert bundle.final_decision == FinalDecision.CONTINUE


def test_missing_evidence_triggers_manual_review():
    evidence = {
        "target_company": "Example GmbH",
        "kyc_result": "completed",
    }

    bundle = run_audit_planning_workflow(
        target_company="Example GmbH",
        evidence_data=evidence,
    )

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert len(bundle.missing_evidence) > 0
