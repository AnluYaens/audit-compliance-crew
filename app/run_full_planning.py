from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.evidence import AuditPlanningEvidenceBundle
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
from storage.evidence_store import save_evidence_bundle
from storage.memo_store import save_planning_memo
from storage.source_registry_store import save_source_registry


@dataclass(frozen=True)
class FullPlanningRunResult:
    bundle: AuditPlanningEvidenceBundle
    evidence_path: Path
    source_registry_path: Path
    memo_path: Path


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


def _company_slug(company_name: str) -> str:
    return (
        company_name.strip()
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("\\", "-")
    )


def build_default_source_records(company_name: str) -> list[SourceRecord]:
    source_slug = _company_slug(company_name)

    return [
        SourceRecord(
            identifier=f"{source_slug}-audited-financial-statements-2026",
            source_type=SourceType.AUDITED_FINANCIAL_STATEMENT,
            publisher="Sample Audit Archive",
            retrieval_date=datetime(2026, 5, 20, tzinfo=timezone.utc),
            confidence=0.95,
            freshness_days=5_000,
            relevance=0.92,
            notes="Sample audited financial statement metadata for local smoke runs.",
        ),
        SourceRecord(
            identifier=f"{source_slug}-company-registry-extract-2026",
            source_type=SourceType.GOVERNMENT_REGISTRY,
            publisher="Sample Company Registry",
            retrieval_date=datetime(2026, 5, 21, tzinfo=timezone.utc),
            confidence=0.93,
            freshness_days=5_000,
            relevance=0.88,
            notes="Sample registry metadata for deterministic source scoring.",
        ),
    ]


def run_for_company(
    company_name: str,
    evidence_output_dir: str = "output/evidence",
    source_registry_output_dir: str = "output/evidence/source_registry",
    memo_output_dir: str = "memos",
) -> FullPlanningRunResult:
    materiality_request = build_default_materiality_request(company_name)
    risk_assessment_request = build_default_risk_assessment_request(company_name)
    source_records = build_default_source_records(company_name)

    bundle = run_audit_planning_pipeline(
        company_name=company_name,
        materiality_request=materiality_request,
        risk_assessment_request=risk_assessment_request,
        source_records=source_records,
        require_source_support=True,
    )

    evidence_path = save_evidence_bundle(
        bundle=bundle,
        output_dir=evidence_output_dir,
    )
    source_registry_path = save_source_registry(
        bundle=bundle,
        output_dir=source_registry_output_dir,
    )

    memo_content = generate_planning_memo(bundle)
    memo_path = save_planning_memo(
        bundle=bundle,
        memo_content=memo_content,
        output_dir=memo_output_dir,
    )

    scoring_result = bundle.source_registry_scoring_result

    print("=" * 80)
    print(f"Company: {company_name}")
    print(f"Run ID: {bundle.run_id}")
    print(f"Final decision: {bundle.final_decision}")
    print(f"Manual review reasons: {bundle.manual_review_reasons}")
    print(f"Source records: {len(bundle.source_records)}")
    print(
        "Source registry decision: "
        f"{scoring_result.decision if scoring_result is not None else 'Not scored'}"
    )
    print(
        "Source registry status: "
        f"{scoring_result.status if scoring_result is not None else 'Not scored'}"
    )
    print(f"Evidence saved to: {evidence_path}")
    print(f"Source registry saved to: {source_registry_path}")
    print(f"Memo saved to: {memo_path}")
    print("=" * 80)

    return FullPlanningRunResult(
        bundle=bundle,
        evidence_path=evidence_path,
        source_registry_path=source_registry_path,
        memo_path=memo_path,
    )


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
