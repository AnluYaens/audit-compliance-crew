from __future__ import annotations

from crewai.tools import tool

from services.ingestion_service import read_client_crm_data_service
from services.risk_scoring_service import calculate_weighted_risk_score_service
from services.screening_service import (
    check_partner_independence_service,
    scan_sanctions_watchlist_service,
)


@tool("Read Client CRM Data")
def read_client_crm_data(company_name: str) -> str:
    """
    CrewAI wrapper for deterministic CRM ingestion.
    Input: company_name (str)
    """
    return read_client_crm_data_service(company_name)


@tool("Check Partner Independence")
def check_partner_independence(company_name: str) -> str:
    """
    CrewAI wrapper for deterministic partner independence screening.
    Input: company_name (str)
    """
    return check_partner_independence_service(company_name)


@tool("Scan Sanctions Watchlist")
def scan_sanctions_watchlist(
    ceo_name: str,
    company_name: str,
    global_offices: list[str],
) -> str:
    """
    CrewAI wrapper for deterministic sanctions and restricted-region screening.
    Inputs: ceo_name (str), company_name (str), global_offices (list[str])
    """
    return scan_sanctions_watchlist_service(
        ceo_name=ceo_name,
        company_name=company_name,
        global_offices=global_offices,
    )


@tool("Calculate Weighted Risk Score")
def calculate_weighted_risk_score(
    industry_level: str,
    geography_level: str,
    financial_level: str,
) -> str:
    """
    CrewAI wrapper for deterministic weighted risk scoring.
    Inputs: industry_level, geography_level, financial_level.
    """
    return calculate_weighted_risk_score_service(
        industry_level=industry_level,
        geography_level=geography_level,
        financial_level=financial_level,
    )


# Backward-compatible names for existing imports and notebooks.
read_client_crm = read_client_crm_data
check_independence = check_partner_independence
check_sanctions = scan_sanctions_watchlist
calculate_risk_score = calculate_weighted_risk_score
