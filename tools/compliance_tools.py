from __future__ import annotations

import csv
import difflib
import json
import os
from typing import Any

from crewai.tools import tool
from pydantic import ValidationError

from models import (
    ClientCRMReadRequest,
    ClientProfile,
    IngestionToolOutput,
    PartnerConflict,
    PartnerIndependenceRequest,
    RiskEvaluationInput,
    RiskInputSnapshot,
    RiskScoringOutput,
    ScreeningResponse,
    WatchlistFlag,
    WatchlistScanRequest,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRM_PATH = os.path.join(BASE_DIR, "data", "client_crm.json")
CSV_PATH = os.path.join(BASE_DIR, "data", "internal_holdings.csv")
JSON_PATH = os.path.join(BASE_DIR, "data", "sanctions.json")

RISK_VALUES = {"Low": 1.0, "Medium": 2.0, "High": 3.0}
ALLOWED_RISK_VALUES = ["High", "Medium", "Low"]


def normalize_string(value: Any) -> str:
    """Remove repeated whitespace and normalize casing for deterministic matching."""
    return " ".join(str(value).strip().lower().split())


def contract_json(model: Any) -> str:
    """Serialize Pydantic contracts in one predictable JSON shape."""
    return json.dumps(model.model_dump(by_alias=True, exclude_none=True), ensure_ascii=False)


def standard_ingestion_error(error_msg: str) -> str:
    payload = IngestionToolOutput(
        status="ERROR",
        decision="MANUAL_REVIEW",
        is_blocker=True,
        severity="HIGH",
        message=f"Execution failed: {error_msg}",
    )
    return contract_json(payload)


def standard_screening_error(tool_name: str, screening_type: str, error_msg: str) -> str:
    payload = ScreeningResponse(
        tool=tool_name,
        status="ERROR",
        decision="MANUAL_REVIEW",
        is_blocker=True,
        severity="HIGH",
        message=f"Execution failed: {error_msg}",
        screening_type=screening_type,
    )
    return contract_json(payload)


def normalize_risk_state(value: Any) -> str:
    normalized = " ".join(str(value).strip().split()).title()
    return normalized if normalized in RISK_VALUES else "INVALID_INPUT"


def invalid_value_label(value: Any) -> str:
    label = str(value).strip()
    return label if label else "<EMPTY>"


def coerce_string_list(value: Any) -> list[str]:
    """Accept list-like tool arguments when an LLM serializes them as text."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

        return [part.strip() for part in stripped.split(",") if part.strip()]

    return []


def load_client_profiles() -> list[ClientProfile]:
    if not os.path.exists(CRM_PATH):
        raise FileNotFoundError("File data/client_crm.json not found.")

    with open(CRM_PATH, mode="r", encoding="utf-8") as handle:
        raw_clients = json.load(handle)

    if not isinstance(raw_clients, list):
        raise ValueError("CRM datastore must contain a JSON list of client records.")

    return [ClientProfile.model_validate(record) for record in raw_clients]


@tool("Read Client CRM Data")
def read_client_crm_data(company_name: str) -> str:
    """
    Reads the client_crm.json database file and returns a validated CRM contract.
    Input: company_name (str)
    """
    try:
        request = ClientCRMReadRequest(company_name=company_name)
        clients = load_client_profiles()

        normalized_target = normalize_string(request.company_name)
        normalized_names = [normalize_string(client.company_name) for client in clients]
        matches = difflib.get_close_matches(normalized_target, normalized_names, n=1, cutoff=0.7)

        if not matches:
            payload = IngestionToolOutput(
                status="NOT_FOUND",
                decision="MANUAL_REVIEW",
                is_blocker=True,
                severity="HIGH",
                message=f"No records found matching '{request.company_name}'.",
            )
            return contract_json(payload)

        matched_normalized_name = matches[0]
        for client in clients:
            if normalize_string(client.company_name) == matched_normalized_name:
                match_score = difflib.SequenceMatcher(
                    None,
                    normalized_target,
                    matched_normalized_name,
                ).ratio()
                payload = IngestionToolOutput(
                    status="SUCCESS",
                    decision="CONTINUE",
                    is_blocker=False,
                    severity="LOW",
                    source="client_crm.json",
                    query=request.company_name,
                    matched_company=client.company_name,
                    match_score=round(match_score, 3),
                    match_type="EXACT" if match_score == 1.0 else "FUZZY",
                    data=client,
                )
                return contract_json(payload)

        payload = IngestionToolOutput(
            status="NOT_FOUND",
            decision="MANUAL_REVIEW",
            is_blocker=True,
            severity="HIGH",
            message=f"Company '{request.company_name}' resolved but record lost.",
        )
        return contract_json(payload)
    except (ValidationError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        return standard_ingestion_error(str(exc))
    except Exception as exc:
        return standard_ingestion_error(f"Unexpected error: {exc}")


@tool("Check Partner Independence")
def check_partner_independence(company_name: str) -> str:
    """
    Scans the internal partner holdings registry using normalized string lookups.
    Input: company_name (str)
    """
    try:
        request = PartnerIndependenceRequest(company_name=company_name)

        if not os.path.exists(CSV_PATH):
            return standard_screening_error(
                "Check Partner Independence",
                "PARTNER_INDEPENDENCE",
                "File data/internal_holdings.csv not found.",
            )

        normalized_target = normalize_string(request.company_name)
        conflicts: list[PartnerConflict] = []

        with open(CSV_PATH, mode="r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required_columns = {"Partner_Name", "Stock_Holding"}
            if not required_columns.issubset(set(reader.fieldnames or [])):
                raise ValueError("internal_holdings.csv is missing required columns.")

            for row in reader:
                partner_name = str(row.get("Partner_Name", "")).strip()
                stock_holding = str(row.get("Stock_Holding", "")).strip()
                if not partner_name or not stock_holding:
                    continue

                normalized_holding = normalize_string(stock_holding)
                if normalized_target in normalized_holding or normalized_holding in normalized_target:
                    conflicts.append(
                        PartnerConflict(partner=partner_name, asset=stock_holding)
                    )

        if conflicts:
            payload = ScreeningResponse(
                tool="Check Partner Independence",
                status="CONFLICT_DETECTED",
                decision="REJECT",
                is_blocker=True,
                severity="CRITICAL",
                screening_type="PARTNER_INDEPENDENCE",
                conflicts=conflicts,
            )
            return contract_json(payload)

        payload = ScreeningResponse(
            tool="Check Partner Independence",
            status="CLEAR",
            decision="CONTINUE",
            is_blocker=False,
            severity="LOW",
            message="No internal partner equity conflicts located.",
            screening_type="PARTNER_INDEPENDENCE",
        )
        return contract_json(payload)
    except (ValidationError, ValueError) as exc:
        return standard_screening_error("Check Partner Independence", "PARTNER_INDEPENDENCE", str(exc))
    except Exception as exc:
        return standard_screening_error(
            "Check Partner Independence",
            "PARTNER_INDEPENDENCE",
            f"Unexpected error: {exc}",
        )


@tool("Scan Sanctions Watchlist")
def scan_sanctions_watchlist(ceo_name: str, company_name: str, global_offices: list[str]) -> str:
    """
    Cross-references corporate metadata against global sanctions records.
    Inputs: ceo_name (str), company_name (str), global_offices (list[str])
    """
    try:
        request = WatchlistScanRequest(
            ceo_name=ceo_name,
            company_name=company_name,
            global_offices=coerce_string_list(global_offices),
        )

        if not os.path.exists(JSON_PATH):
            return standard_screening_error(
                "Scan Sanctions Watchlist",
                "WATCHLIST_SCAN",
                "File data/sanctions.json not found.",
            )

        with open(JSON_PATH, mode="r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise ValueError("sanctions.json must contain a JSON object.")

        flags: list[WatchlistFlag] = []
        norm_ceo = normalize_string(request.ceo_name)
        norm_company = normalize_string(request.company_name)

        blacklisted_individuals = coerce_string_list(data.get("blacklisted_individuals", []))
        blacklisted_entities = coerce_string_list(data.get("blacklisted_entities", []))
        restricted_regions = coerce_string_list(data.get("restricted_regions", []))

        for individual in blacklisted_individuals:
            normalized_individual = normalize_string(individual)
            if norm_ceo in normalized_individual or normalized_individual in norm_ceo:
                flags.append(
                    WatchlistFlag(
                        type="INDIVIDUAL_SANCTION",
                        matched_term=request.ceo_name,
                        blacklist_record=str(individual).strip(),
                    )
                )

        for entity in blacklisted_entities:
            normalized_entity = normalize_string(entity)
            if norm_company in normalized_entity or normalized_entity in norm_company:
                flags.append(
                    WatchlistFlag(
                        type="ENTITY_SANCTION",
                        matched_term=request.company_name,
                        blacklist_record=str(entity).strip(),
                    )
                )

        for office in request.global_offices:
            norm_office = normalize_string(office)
            for region in restricted_regions:
                normalized_region = normalize_string(region)
                if norm_office == normalized_region:
                    flags.append(
                        WatchlistFlag(
                            type="GEOGRAPHIC_SANCTION",
                            matched_term=office,
                            blacklist_record=region,
                        )
                    )

        if flags:
            payload = ScreeningResponse(
                tool="Scan Sanctions Watchlist",
                status="SANCTIONS_HIT",
                decision="REJECT",
                is_blocker=True,
                severity="CRITICAL",
                screening_type="WATCHLIST_SCAN",
                flags=flags,
            )
            return contract_json(payload)

        payload = ScreeningResponse(
            tool="Scan Sanctions Watchlist",
            status="CLEAR",
            decision="CONTINUE",
            is_blocker=False,
            severity="LOW",
            message="Sanctions clearance granted. Zero watchlist matches found.",
            screening_type="WATCHLIST_SCAN",
        )
        return contract_json(payload)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        return standard_screening_error("Scan Sanctions Watchlist", "WATCHLIST_SCAN", str(exc))
    except Exception as exc:
        return standard_screening_error(
            "Scan Sanctions Watchlist",
            "WATCHLIST_SCAN",
            f"Unexpected error: {exc}",
        )


@tool("Calculate Weighted Risk Score")
def calculate_weighted_risk_score(
    industry_level: str,
    geography_level: str,
    financial_level: str,
) -> str:
    """
    Runs the deterministic weighted risk equation framework.
    Inputs must map to 'Low', 'Medium', or 'High'; all other inputs fail closed.
    """
    inputs = RiskInputSnapshot(
        industry=normalize_risk_state(industry_level),
        geography=normalize_risk_state(geography_level),
        financial=normalize_risk_state(financial_level),
    )

    invalid_inputs = {
        key: invalid_value_label(value)
        for key, value in {
            "industry": industry_level,
            "geography": geography_level,
            "financial": financial_level,
        }.items()
        if getattr(inputs, key) == "INVALID_INPUT"
    }

    if invalid_inputs:
        payload = RiskScoringOutput(
            status="INVALID_INPUT",
            decision="MANUAL_REVIEW",
            is_blocker=True,
            severity="HIGH",
            message="Risk levels must be exactly High, Medium, or Low.",
            inputs=inputs,
            invalid_inputs=invalid_inputs,
            allowed_values=ALLOWED_RISK_VALUES,
        )
        return contract_json(payload)

    try:
        validated = RiskEvaluationInput(
            industry_level=inputs.industry,
            geography_level=inputs.geography,
            financial_level=inputs.financial,
        )

        score = (
            RISK_VALUES[validated.industry_level] * 0.5
            + RISK_VALUES[validated.geography_level] * 0.3
            + RISK_VALUES[validated.financial_level] * 0.2
        )

        if score < 1.8:
            classification = "Low Risk Engagement"
        elif score <= 2.5:
            classification = "Moderate Risk Engagement"
        else:
            classification = "High Risk Engagement (Requires Enhanced Due Diligence)"

        payload = RiskScoringOutput(
            status="SUCCESS",
            decision="CONTINUE",
            is_blocker=False,
            severity="HIGH" if score > 2.5 else "MEDIUM" if score >= 1.8 else "LOW",
            raw_score=round(score, 2),
            classification=classification,
            inputs=inputs,
            allowed_values=ALLOWED_RISK_VALUES,
        )
        return contract_json(payload)
    except Exception as exc:
        payload = RiskScoringOutput(
            status="INVALID_INPUT",
            decision="MANUAL_REVIEW",
            is_blocker=True,
            severity="HIGH",
            message=f"Risk scoring failed closed: {exc}",
            inputs=inputs,
            invalid_inputs={
                "industry": invalid_value_label(industry_level),
                "geography": invalid_value_label(geography_level),
                "financial": invalid_value_label(financial_level),
            },
            allowed_values=ALLOWED_RISK_VALUES,
        )
        return contract_json(payload)


# Backward-compatible names for existing imports and notebooks.
read_client_crm = read_client_crm_data
check_independence = check_partner_independence
check_sanctions = scan_sanctions_watchlist
calculate_risk_score = calculate_weighted_risk_score
