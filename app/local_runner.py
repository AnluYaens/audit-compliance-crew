from orchestration.planning_orchestrator import run_audit_planning_workflow
from storage.evidence_store import save_evidence_bundle


def main() -> None:
    sample_evidence = {
        "target_company": "Example GmbH",

        # Acceptance evidence
        "kyc_result": "completed",
        "sanctions_result": "clear",
        "independence_result": "clear",
        "acceptance_decision": "preliminarily_acceptable",
        "manual_review_reasons": [],

        # Materiality evidence
        "financial_statement_basis": "profit_before_tax",
        "selected_benchmark": "profit_before_tax",
        "benchmark_amount": 1_000_000,
        "materiality_percentage": 0.05,
        "overall_materiality": 50_000,
        "performance_materiality": 37_500,
        "clearly_trivial_threshold": 2_500,

        # Risk evidence
        "entity_understanding": "Initial understanding documented.",
        "financial_statement_areas": ["Revenue", "Inventory", "Cash"],
        "assertions": ["Occurrence", "Completeness", "Valuation"],
        "risk_indicators": ["Revenue growth higher than industry average"],
        "identified_risks": [
            {
                "area": "Revenue",
                "assertion": "Occurrence",
                "risk_level": "Elevated",
                "reason": "Unusual revenue growth.",
            }
        ],
        "risk_level": "Elevated",
        "affected_assertions": ["Occurrence"],
        "evidence_references": ["sample_trial_balance.csv"],
    }

    bundle = run_audit_planning_workflow(
        target_company="Example GmbH",
        evidence_data=sample_evidence,
    )

    output_path = save_evidence_bundle(bundle)

    print(f"Run ID: {bundle.run_id}")
    print(f"Final decision: {bundle.final_decision}")
    print(f"Evidence saved to: {output_path}")


if __name__ == "__main__":
    main()
