from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schemas.client_artifacts import (
    ArtifactValue,
    ClientArtifactFileType,
    ClientArtifactParserWarning,
    ClientArtifactProvenanceReference,
    ClientArtifactQualityStatus,
    ClientArtifactSensitivity,
    ClientArtifactSourceMetadata,
    ClientArtifactWarningSeverity,
    NormalizedClientArtifactBundle,
    NormalizedClientArtifactCell,
    NormalizedClientArtifactRow,
    NormalizedClientArtifactTable,
)


CSV_CONFIDENCE = 0.98
JSON_CONFIDENCE = 0.97
REVIEW_CONFIDENCE = 0.65
MALFORMED_CONFIDENCE = 0.0


def _file_type_for_path(path: Path) -> ClientArtifactFileType:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return ClientArtifactFileType.CSV
    if suffix == ".json":
        return ClientArtifactFileType.JSON
    if suffix == ".pdf":
        return ClientArtifactFileType.PDF
    if suffix == ".xlsx":
        return ClientArtifactFileType.XLSX
    if suffix == ".txt":
        return ClientArtifactFileType.TXT
    return ClientArtifactFileType.UNKNOWN


def _content_hash(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _source_id(filename: str, content_hash: str | None) -> str:
    if content_hash is not None:
        return f"source-{content_hash.removeprefix('sha256:')[:16]}"
    fallback = hashlib.sha256(filename.encode("utf-8")).hexdigest()
    return f"source-{fallback[:16]}"


def _source_metadata(
    path: Path,
    file_type: ClientArtifactFileType,
    content_hash: str | None,
    sensitivity: ClientArtifactSensitivity,
    generated_at: datetime,
) -> ClientArtifactSourceMetadata:
    return ClientArtifactSourceMetadata(
        source_id=_source_id(path.name, content_hash),
        original_filename=path.name or "unnamed-client-artifact",
        file_type=file_type,
        content_hash=content_hash,
        received_at=generated_at,
        sensitivity=sensitivity,
    )


def _provenance(
    metadata: ClientArtifactSourceMetadata,
    *,
    row_number: int | None = None,
    column_name: str | None = None,
    field_path: str | None = None,
) -> ClientArtifactProvenanceReference:
    return ClientArtifactProvenanceReference(
        source_id=metadata.source_id,
        file_name=metadata.original_filename,
        row_number=row_number,
        column_name=column_name,
        field_path=field_path,
    )


def _warning(
    code: str,
    message: str,
    severity: ClientArtifactWarningSeverity,
    metadata: ClientArtifactSourceMetadata,
    *,
    row_number: int | None = None,
    column_name: str | None = None,
    field_path: str | None = None,
) -> ClientArtifactParserWarning:
    return ClientArtifactParserWarning(
        warning_code=code,
        message=message,
        severity=severity,
        provenance=_provenance(
            metadata,
            row_number=row_number,
            column_name=column_name,
            field_path=field_path,
        ),
        human_review_recommended=True,
    )


def _quality_status(
    warnings: list[ClientArtifactParserWarning],
    missing_required_fields: list[str],
    *,
    malformed: bool = False,
    incomplete: bool = False,
) -> ClientArtifactQualityStatus:
    if malformed:
        return ClientArtifactQualityStatus.MALFORMED
    if incomplete:
        return ClientArtifactQualityStatus.INCOMPLETE
    if warnings or missing_required_fields:
        return ClientArtifactQualityStatus.REVIEW_RECOMMENDED
    return ClientArtifactQualityStatus.COMPLETE


def _confidence(
    warnings: list[ClientArtifactParserWarning],
    *,
    malformed: bool = False,
    incomplete: bool = False,
    base_confidence: float,
) -> float:
    if malformed:
        return MALFORMED_CONFIDENCE
    if incomplete:
        return 0.25
    if warnings:
        return REVIEW_CONFIDENCE
    return base_confidence


def _bundle(
    metadata: ClientArtifactSourceMetadata,
    *,
    normalized_tables: list[NormalizedClientArtifactTable] | None = None,
    warnings: list[ClientArtifactParserWarning] | None = None,
    missing_required_fields: list[str] | None = None,
    overall_confidence: float,
    quality_status: ClientArtifactQualityStatus,
    generated_at: datetime,
) -> NormalizedClientArtifactBundle:
    return NormalizedClientArtifactBundle(
        bundle_id=f"bundle-{metadata.source_id}",
        source_metadata=[metadata],
        normalized_tables=normalized_tables or [],
        normalized_text_chunks=[],
        warnings=warnings or [],
        missing_required_fields=missing_required_fields or [],
        overall_confidence=overall_confidence,
        quality_status=quality_status,
        generated_at=generated_at,
    )


def _normalized_header(raw_header: str | None, index: int, seen: Counter[str]) -> str:
    stripped = (raw_header or "").strip()
    base = stripped if stripped else f"unnamed_column_{index}"
    seen[base] += 1
    if seen[base] == 1:
        return base
    return f"{base}__duplicate_{seen[base]}"


def _csv_warnings_for_headers(
    raw_headers: list[str],
    normalized_headers: list[str],
    metadata: ClientArtifactSourceMetadata,
) -> list[ClientArtifactParserWarning]:
    warnings: list[ClientArtifactParserWarning] = []
    stripped_headers = [(header or "").strip() for header in raw_headers]
    counts = Counter(header for header in stripped_headers if header)

    for index, header in enumerate(stripped_headers, start=1):
        normalized_header = normalized_headers[index - 1]
        if not header:
            warnings.append(
                _warning(
                    "BLANK_CSV_HEADER",
                    f"CSV column {index} has a missing or blank header.",
                    ClientArtifactWarningSeverity.HIGH,
                    metadata,
                    row_number=1,
                    column_name=normalized_header,
                )
            )
        elif counts[header] > 1:
            warnings.append(
                _warning(
                    "DUPLICATE_CSV_HEADER",
                    f"CSV header '{header}' appears more than once.",
                    ClientArtifactWarningSeverity.MEDIUM,
                    metadata,
                    row_number=1,
                    column_name=normalized_header,
                )
            )

    return warnings


def _normalize_csv(
    content: bytes,
    metadata: ClientArtifactSourceMetadata,
    generated_at: datetime,
) -> NormalizedClientArtifactBundle:
    if not content:
        warnings = [
            _warning(
                "EMPTY_FILE",
                "Client artifact file is empty.",
                ClientArtifactWarningSeverity.HIGH,
                metadata,
            )
        ]
        return _bundle(
            metadata,
            warnings=warnings,
            missing_required_fields=["csv_headers", "csv_rows"],
            overall_confidence=_confidence(warnings, incomplete=True, base_confidence=CSV_CONFIDENCE),
            quality_status=_quality_status(warnings, ["csv_headers", "csv_rows"], incomplete=True),
            generated_at=generated_at,
        )

    decoded = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(decoded.splitlines())
    records = list(reader)
    if not records:
        warnings = [
            _warning(
                "EMPTY_FILE",
                "Client artifact file has no CSV records.",
                ClientArtifactWarningSeverity.HIGH,
                metadata,
            )
        ]
        return _bundle(
            metadata,
            warnings=warnings,
            missing_required_fields=["csv_headers", "csv_rows"],
            overall_confidence=_confidence(warnings, incomplete=True, base_confidence=CSV_CONFIDENCE),
            quality_status=_quality_status(warnings, ["csv_headers", "csv_rows"], incomplete=True),
            generated_at=generated_at,
        )

    raw_headers = records[0]
    if not raw_headers:
        warnings = [
            _warning(
                "MISSING_CSV_HEADERS",
                "CSV file does not contain headers.",
                ClientArtifactWarningSeverity.HIGH,
                metadata,
                row_number=1,
            )
        ]
        return _bundle(
            metadata,
            warnings=warnings,
            missing_required_fields=["csv_headers"],
            overall_confidence=_confidence(warnings, incomplete=True, base_confidence=CSV_CONFIDENCE),
            quality_status=_quality_status(warnings, ["csv_headers"], incomplete=True),
            generated_at=generated_at,
        )

    seen_headers: Counter[str] = Counter()
    headers = [
        _normalized_header(raw_header, index, seen_headers)
        for index, raw_header in enumerate(raw_headers, start=1)
    ]
    warnings = _csv_warnings_for_headers(raw_headers, headers, metadata)
    rows: list[NormalizedClientArtifactRow] = []

    for record_index, record in enumerate(records[1:], start=2):
        if len(record) != len(headers):
            warnings.append(
                _warning(
                    "CSV_ROW_LENGTH_MISMATCH",
                    (
                        f"CSV row {record_index} has {len(record)} value(s), "
                        f"expected {len(headers)}."
                    ),
                    ClientArtifactWarningSeverity.MEDIUM,
                    metadata,
                    row_number=record_index,
                )
            )

        cells: list[NormalizedClientArtifactCell] = []
        for column_index, header in enumerate(headers):
            raw_value: ArtifactValue = record[column_index] if column_index < len(record) else None
            value: ArtifactValue = raw_value.strip() if isinstance(raw_value, str) else raw_value
            if value == "":
                warnings.append(
                    _warning(
                        "BLANK_CSV_VALUE",
                        f"CSV row {record_index} has a blank value for '{header}'.",
                        ClientArtifactWarningSeverity.LOW,
                        metadata,
                        row_number=record_index,
                        column_name=header,
                    )
                )
                value = None

            cells.append(
                NormalizedClientArtifactCell(
                    column_name=header,
                    value=value,
                    raw_value=raw_value,
                    provenance=_provenance(
                        metadata,
                        row_number=record_index,
                        column_name=header,
                    ),
                    confidence=CSV_CONFIDENCE,
                )
            )

        rows.append(
            NormalizedClientArtifactRow(
                row_id=f"{metadata.source_id}-row-{record_index - 1}",
                cells=cells,
                provenance=_provenance(metadata, row_number=record_index),
                confidence=CSV_CONFIDENCE if len(record) == len(headers) else REVIEW_CONFIDENCE,
            )
        )

    if not rows:
        warnings.append(
            _warning(
                "EMPTY_CSV_ROWS",
                "CSV file contains headers but no data rows.",
                ClientArtifactWarningSeverity.MEDIUM,
                metadata,
                row_number=1,
            )
        )

    table_confidence = _confidence(warnings, base_confidence=CSV_CONFIDENCE)
    table = NormalizedClientArtifactTable(
        table_id=f"table-{metadata.source_id}",
        table_name=metadata.original_filename,
        headers=headers,
        rows=rows,
        provenance=_provenance(metadata),
        confidence=table_confidence,
    )
    missing_required_fields = [] if rows else ["csv_rows"]
    quality_status = _quality_status(warnings, missing_required_fields)

    return _bundle(
        metadata,
        normalized_tables=[table],
        warnings=warnings,
        missing_required_fields=missing_required_fields,
        overall_confidence=table_confidence,
        quality_status=quality_status,
        generated_at=generated_at,
    )


def _json_scalar_rows(
    value: Any,
    path: str,
) -> list[tuple[str, ArtifactValue, str]]:
    if isinstance(value, dict):
        rows: list[tuple[str, ArtifactValue, str]] = []
        for key in sorted(value):
            child_path = f"{path}.{key}" if path else f"$.{key}"
            rows.extend(_json_scalar_rows(value[key], child_path))
        return rows

    if isinstance(value, list):
        rows = []
        for index, child_value in enumerate(value):
            child_path = f"{path}[{index}]"
            rows.extend(_json_scalar_rows(child_value, child_path))
        return rows

    if path == "":
        path = "$"

    value_type = "null" if value is None else type(value).__name__
    return [(path, value, value_type)]


def _normalize_json(
    content: bytes,
    metadata: ClientArtifactSourceMetadata,
    generated_at: datetime,
) -> NormalizedClientArtifactBundle:
    if not content:
        warnings = [
            _warning(
                "EMPTY_FILE",
                "Client artifact file is empty.",
                ClientArtifactWarningSeverity.HIGH,
                metadata,
            )
        ]
        return _bundle(
            metadata,
            warnings=warnings,
            missing_required_fields=["valid_json"],
            overall_confidence=_confidence(warnings, incomplete=True, base_confidence=JSON_CONFIDENCE),
            quality_status=_quality_status(warnings, ["valid_json"], incomplete=True),
            generated_at=generated_at,
        )

    try:
        parsed = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        warnings = [
            _warning(
                "MALFORMED_JSON",
                f"JSON artifact could not be parsed: {exc.msg if hasattr(exc, 'msg') else exc}.",
                ClientArtifactWarningSeverity.HIGH,
                metadata,
            )
        ]
        return _bundle(
            metadata,
            warnings=warnings,
            missing_required_fields=["valid_json"],
            overall_confidence=_confidence(warnings, malformed=True, base_confidence=JSON_CONFIDENCE),
            quality_status=_quality_status(warnings, ["valid_json"], malformed=True),
            generated_at=generated_at,
        )

    scalar_rows = _json_scalar_rows(parsed, "$")
    warnings: list[ClientArtifactParserWarning] = []
    if not scalar_rows:
        warnings.append(
            _warning(
                "NO_JSON_SCALAR_FIELDS",
                "JSON artifact contains no scalar fields to normalize.",
                ClientArtifactWarningSeverity.MEDIUM,
                metadata,
                field_path="$",
            )
        )

    headers = ["field_path", "value", "value_type"]
    rows: list[NormalizedClientArtifactRow] = []
    for index, (field_path, value, value_type) in enumerate(scalar_rows, start=1):
        source_provenance = _provenance(metadata, field_path=field_path)
        rows.append(
            NormalizedClientArtifactRow(
                row_id=f"{metadata.source_id}-field-{index}",
                cells=[
                    NormalizedClientArtifactCell(
                        column_name="field_path",
                        value=field_path,
                        raw_value=field_path,
                        provenance=source_provenance,
                        confidence=JSON_CONFIDENCE,
                    ),
                    NormalizedClientArtifactCell(
                        column_name="value",
                        value=value,
                        raw_value=value,
                        provenance=source_provenance,
                        confidence=JSON_CONFIDENCE,
                    ),
                    NormalizedClientArtifactCell(
                        column_name="value_type",
                        value=value_type,
                        raw_value=value_type,
                        provenance=source_provenance,
                        confidence=JSON_CONFIDENCE,
                    ),
                ],
                provenance=source_provenance,
                confidence=JSON_CONFIDENCE,
            )
        )

    table_confidence = _confidence(warnings, base_confidence=JSON_CONFIDENCE)
    table = NormalizedClientArtifactTable(
        table_id=f"table-{metadata.source_id}",
        table_name=metadata.original_filename,
        headers=headers,
        rows=rows,
        provenance=_provenance(metadata),
        confidence=table_confidence,
    )
    missing_required_fields = [] if rows else ["json_scalar_fields"]

    return _bundle(
        metadata,
        normalized_tables=[table],
        warnings=warnings,
        missing_required_fields=missing_required_fields,
        overall_confidence=table_confidence,
        quality_status=_quality_status(warnings, missing_required_fields),
        generated_at=generated_at,
    )


def normalize_client_artifact_file(
    path: Path | str,
    sensitivity: ClientArtifactSensitivity = ClientArtifactSensitivity.CONFIDENTIAL,
) -> NormalizedClientArtifactBundle:
    artifact_path = Path(path)
    generated_at = datetime.now(timezone.utc)
    file_type = _file_type_for_path(artifact_path)

    try:
        content = artifact_path.read_bytes()
        content_hash = _content_hash(content)
    except OSError:
        metadata = _source_metadata(
            artifact_path,
            file_type,
            None,
            sensitivity,
            generated_at,
        )
        warnings = [
            _warning(
                "FILE_READ_ERROR",
                "Client artifact file could not be read from the local path.",
                ClientArtifactWarningSeverity.HIGH,
                metadata,
            )
        ]
        return _bundle(
            metadata,
            warnings=warnings,
            missing_required_fields=["readable_file"],
            overall_confidence=0.0,
            quality_status=ClientArtifactQualityStatus.INCOMPLETE,
            generated_at=generated_at,
        )

    metadata = _source_metadata(
        artifact_path,
        file_type,
        content_hash,
        sensitivity,
        generated_at,
    )

    if file_type == ClientArtifactFileType.CSV:
        return _normalize_csv(content, metadata, generated_at)
    if file_type == ClientArtifactFileType.JSON:
        return _normalize_json(content, metadata, generated_at)

    warnings = [
        _warning(
            "UNSUPPORTED_FILE_TYPE",
            f"File type '{file_type.value}' is not supported for client artifact normalization.",
            ClientArtifactWarningSeverity.HIGH,
            metadata,
        )
    ]
    return _bundle(
        metadata,
        warnings=warnings,
        missing_required_fields=["supported_file_type"],
        overall_confidence=0.0,
        quality_status=ClientArtifactQualityStatus.REVIEW_RECOMMENDED,
        generated_at=generated_at,
    )
