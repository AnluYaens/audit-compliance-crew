from __future__ import annotations

import json

from schemas.contracts import (
    IngestionToolOutput,
    RiskScoringOutput,
    ScreeningAggregateResponse,
    ScreeningResponse,
)
from schemas.decisions import FinalDecision
from schemas.evidence import AuditPlanningEvidenceBundle
from services.ingestion_service import read_client_crm_data_service
from services.risk_scoring_service import calculate_weighted_risk_score_service
from services.screening_service import (
    check_partner_independence_service,
    scan_sanctions_watchlist_service,
)


BLOCKING_SCREENING_STATUSES = {
    "CONFLICT_DETECTED",
    "SANCTIONS_HIT",
    "ERROR",
    "INVALID_INPUT",
    "NOT_FOUND",
}


def parse_ingestion_output(raw_json: str) -> IngestionToolOutput:
    return IngestionToolOutput.model_validate(json.loads(raw_json))


def parse_screening_output(raw_json: str) -> ScreeningResponse:
    return ScreeningResponse.model_validate(json.loads(raw_json))


def parse_risk_output(raw_json: str) -> RiskScoringOutput:
    return RiskScoringOutput.model_validate(json.loads(raw_json))


def map_industry_risk(industry: str) -> str:
    mapping = {
        "technology": "Medium",
        "extractives": "High",
        "energy": "High",
        "agriculture": "Low",
    }
    return mapping.get(industry.strip().lower(), "INVALID_INPUT")


def map_geography_risk(global_offices: list[str]) -> str:
    high_risk_regions = {"iraq", "libya", "venezuela"}

    normalized_offices = {
        office.strip().lower()
        for office in global_offices
    }

    if normalized_offices.intersection(high_risk_regions):
        return "High"

    return "Low"


def map_financial_risk(financial_stability_rating: str) -> str:
    mapping = {
        "High": "Low",
        "Medium": "Medium",
        "Low": "High",
    }
    return mapping.get(financial_stability_rating, "INVALID_INPUT")


def aggregate_screening_results(
    company_name: str,
    independence_result: ScreeningResponse,
    sanctions_result: ScreeningResponse,
) -> ScreeningAggregateResponse:
    blocking_statuses = [
        result.status
        for result in [independence_result, sanctions_result]
        if result.status in BLOCKING_SCREENING_STATUSES
    ]

    decisions = {
        independence_result.decision,
        sanctions_result.decision,
    }

    if "REJECT" in decisions:
        final_screening_decision = "REJECT"
    elif "MANUAL_REVIEW" in decisions:
        final_screening_decision = "MANUAL_REVIEW"
    else:
        final_screening_decision = "CONTINUE"

    return ScreeningAggregateResponse(
        company_name=company_name,
        independence_result=independence_result,
        sanctions_result=sanctions_result,
        blocking_statuses=blocking_statuses,
        final_screening_decision=final_screening_decision,
    )


def determine_acceptance_decision(
    ingestion_result: IngestionToolOutput,
    screening_result: ScreeningAggregateResponse | None,
    risk_result: RiskScoringOutput | None,
) -> FinalDecision:
    if ingestion_result.decision != "CONTINUE":
        return FinalDecision.MANUAL_REVIEW

    if screening_result is None:
        return FinalDecision.MANUAL_REVIEW

    if screening_result.final_screening_decision == "REJECT":
        return FinalDecision.REJECT

    if screening_result.final_screening_decision == "MANUAL_REVIEW":
        return FinalDecision.MANUAL_REVIEW

    if risk_result is None:
        return FinalDecision.MANUAL_REVIEW

    if risk_result.decision == "MANUAL_REVIEW":
        return FinalDecision.MANUAL_REVIEW

    if risk_result.severity == "HIGH":
        return FinalDecision.MANUAL_REVIEW

    return FinalDecision.CONTINUE


def run_acceptance_pipeline(company_name: str) -> AuditPlanningEvidenceBundle:
    raw_ingestion = read_client_crm_data_service(company_name)
    ingestion_result = parse_ingestion_output(raw_ingestion)

    evidence_data: dict = {
        "target_company": company_name,
        "ingestion_result": ingestion_result.model_dump(mode="json", by_alias=True),
    }

    manual_review_reasons: list[str] = []

    screening_result: ScreeningAggregateResponse | None = None
    risk_result: RiskScoringOutput | None = None

    if ingestion_result.decision != "CONTINUE" or ingestion_result.data is None:
        manual_review_reasons.append(
            f"Ingestion did not continue: {ingestion_result.status}"
        )
    else:
        client = ingestion_result.data

        raw_independence = check_partner_independence_service(client.company_name)
        independence_result = parse_screening_output(raw_independence)

        raw_sanctions = scan_sanctions_watchlist_service(
            ceo_name=client.ceo_name,
            company_name=client.company_name,
            global_offices=client.global_offices,
        )
        sanctions_result = parse_screening_output(raw_sanctions)

        screening_result = aggregate_screening_results(
            company_name=client.company_name,
            independence_result=independence_result,
            sanctions_result=sanctions_result,
        )

        industry_level = map_industry_risk(client.industry)
        geography_level = map_geography_risk(client.global_offices)
        financial_level = map_financial_risk(client.financial_stability_rating)

        raw_risk = calculate_weighted_risk_score_service(
            industry_level=industry_level,
            geography_level=geography_level,
            financial_level=financial_level,
        )
        risk_result = parse_risk_output(raw_risk)

        evidence_data.update(
            {
                "kyc_result": "completed",
                "sanctions_result": sanctions_result.status,
                "independence_result": independence_result.status,
                "acceptance_decision": screening_result.final_screening_decision,
                "screening_result": screening_result.model_dump(mode="json"),
                "risk_result": risk_result.model_dump(mode="json"),
                "risk_level": risk_result.classification,
                "risk_raw_score": risk_result.raw_score,
            }
        )

        if screening_result.blocking_statuses:
            manual_review_reasons.extend(
                f"Blocking screening status: {status}"
                for status in screening_result.blocking_statuses
            )

        if risk_result.severity == "HIGH":
            manual_review_reasons.append(
                f"High engagement risk: {risk_result.classification}"
            )

    final_decision = determine_acceptance_decision(
        ingestion_result=ingestion_result,
        screening_result=screening_result,
        risk_result=risk_result,
    )

    if final_decision == FinalDecision.REJECT:
        manual_review_reasons.append("At least one screening control requires rejection.")

    if final_decision == FinalDecision.MANUAL_REVIEW and not manual_review_reasons:
        manual_review_reasons.append("Manual review required by fail-closed logic.")

    return AuditPlanningEvidenceBundle(
        run_id=f"LOCAL-{company_name.lower().replace(' ', '-')}",
        target_company=company_name,
        engagement_type="Client Acceptance / Audit Planning",
        evidence_data=evidence_data,
        final_decision=final_decision,
        manual_review_reasons=manual_review_reasons,
    )
