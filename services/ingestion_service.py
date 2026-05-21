from __future__ import annotations

import difflib
import json

from pydantic import ValidationError

from schemas.contracts import ClientCRMReadRequest, IngestionToolOutput
from services.compliance_common import (
    contract_json,
    load_client_profiles,
    normalize_string,
    standard_ingestion_error,
)


def read_client_crm_data_service(company_name: str) -> str:
    """
    Reads the client_crm.json database file and returns a validated CRM contract.
    This is deterministic service logic with no CrewAI dependency.
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
