from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schemas.contracts import (
    ClientProfile,
    IngestionToolOutput,
    ScreeningResponse,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

CRM_PATH = DATA_DIR / "client_crm.json"
CSV_PATH = DATA_DIR / "internal_holdings.csv"
JSON_PATH = DATA_DIR / "sanctions.json"

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
    if not CRM_PATH.exists():
        raise FileNotFoundError("File data/client_crm.json not found.")

    raw_clients = json.loads(CRM_PATH.read_text(encoding="utf-8"))

    if not isinstance(raw_clients, list):
        raise ValueError("CRM datastore must contain a JSON list of client records.")

    return [ClientProfile.model_validate(record) for record in raw_clients]
