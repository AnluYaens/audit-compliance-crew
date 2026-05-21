from schemas.decisions import FinalDecision
from services.acceptance_pipeline_service import run_acceptance_pipeline


def test_quantum_cybernetics_is_rejected_for_independence_conflict():
    bundle = run_acceptance_pipeline("Quantum Cybernetics")

    assert bundle.final_decision == FinalDecision.REJECT
    assert bundle.evidence_data["independence_result"] == "CONFLICT_DETECTED"


def test_vanguard_mining_is_rejected_for_sanctions_hit():
    bundle = run_acceptance_pipeline("Vanguard Mining Corp")

    assert bundle.final_decision == FinalDecision.REJECT
    assert bundle.evidence_data["sanctions_result"] == "SANCTIONS_HIT"


def test_unknown_company_fails_closed_to_manual_review():
    bundle = run_acceptance_pipeline("Unknown Company ABC")

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert "ingestion_result" in bundle.evidence_data


def test_greenleaf_has_no_screening_blockers():
    bundle = run_acceptance_pipeline("GreenLeaf Organics")

    assert bundle.evidence_data["independence_result"] == "CLEAR"
    assert bundle.evidence_data["sanctions_result"] == "CLEAR"
    
def test_apex_energy_group_requires_manual_review_for_high_risk():
    bundle = run_acceptance_pipeline("Apex Energy Group")

    assert bundle.final_decision == FinalDecision.MANUAL_REVIEW
    assert bundle.evidence_data["risk_result"]["severity"] == "HIGH"