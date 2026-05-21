from __future__ import annotations

import csv
import json

from pydantic import ValidationError

from schemas.contracts import (
    PartnerConflict,
    PartnerIndependenceRequest,
    ScreeningResponse,
    WatchlistFlag,
    WatchlistScanRequest,
)
from services.compliance_common import (
    CSV_PATH,
    JSON_PATH,
    coerce_string_list,
    contract_json,
    normalize_string,
    standard_screening_error,
)


def check_partner_independence_service(company_name: str) -> str:
    """
    Scans the internal partner holdings registry using normalized string lookups.
    This is deterministic service logic with no CrewAI dependency.
    """
    try:
        request = PartnerIndependenceRequest(company_name=company_name)

        if not CSV_PATH.exists():
            return standard_screening_error(
                "Check Partner Independence",
                "PARTNER_INDEPENDENCE",
                "File data/internal_holdings.csv not found.",
            )

        normalized_target = normalize_string(request.company_name)
        conflicts: list[PartnerConflict] = []

        with CSV_PATH.open(mode="r", encoding="utf-8", newline="") as handle:
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


def scan_sanctions_watchlist_service(
    ceo_name: str,
    company_name: str,
    global_offices: list[str],
) -> str:
    """
    Cross-references corporate metadata against global sanctions records.
    This is deterministic service logic with no CrewAI dependency.
    """
    try:
        request = WatchlistScanRequest(
            ceo_name=ceo_name,
            company_name=company_name,
            global_offices=coerce_string_list(global_offices),
        )

        if not JSON_PATH.exists():
            return standard_screening_error(
                "Scan Sanctions Watchlist",
                "WATCHLIST_SCAN",
                "File data/sanctions.json not found.",
            )

        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

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
