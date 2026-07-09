from __future__ import annotations

import hashlib
import inspect

from schemas.client_artifacts import (
    ClientArtifactFileType,
    ClientArtifactQualityStatus,
    ClientArtifactSensitivity,
    NormalizedClientArtifactBundle,
)
from services import client_artifact_normalization_service
from services.client_artifact_normalization_service import normalize_client_artifact_file


def warning_codes(bundle: NormalizedClientArtifactBundle) -> set[str]:
    return {warning.warning_code for warning in bundle.warnings}


def test_valid_csv_normalizes_table_with_source_metadata_and_provenance(tmp_path):
    path = tmp_path / "synthetic-control-listing.csv"
    path.write_text(
        "control_id,owner,status\n"
        "CTRL-SYN-001,Synthetic Owner,Performed\n"
        "CTRL-SYN-002,Synthetic Reviewer,Pending\n",
        encoding="utf-8",
    )

    bundle = normalize_client_artifact_file(path)

    assert bundle.quality_status == ClientArtifactQualityStatus.COMPLETE
    assert bundle.human_review_recommended is False
    assert bundle.overall_confidence > 0.9
    assert bundle.warnings == []
    assert bundle.source_metadata[0].original_filename == "synthetic-control-listing.csv"
    assert bundle.source_metadata[0].file_type == ClientArtifactFileType.CSV
    assert bundle.source_metadata[0].sensitivity == ClientArtifactSensitivity.CONFIDENTIAL
    assert bundle.source_metadata[0].content_hash == (
        "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    )

    table = bundle.normalized_tables[0]
    assert table.headers == ["control_id", "owner", "status"]
    assert table.confidence > 0.9
    assert len(table.rows) == 2
    assert table.rows[0].provenance is not None
    assert table.rows[0].provenance.row_number == 2
    assert table.rows[0].cells[0].value == "CTRL-SYN-001"
    assert table.rows[0].cells[0].raw_value == "CTRL-SYN-001"
    assert table.rows[0].cells[0].confidence > 0.9
    assert table.rows[0].cells[0].provenance is not None
    assert table.rows[0].cells[0].provenance.row_number == 2
    assert table.rows[0].cells[0].provenance.column_name == "control_id"


def test_valid_json_normalizes_scalar_fields_with_field_path_provenance(tmp_path):
    path = tmp_path / "synthetic-client-profile.json"
    path.write_text(
        """
        {
          "client": {
            "name": "Synthetic Client LLC",
            "locations": ["Synthetic City", "Synthetic Region"]
          },
          "controls": [
            {"id": "CTRL-SYN-001", "effective": true}
          ]
        }
        """,
        encoding="utf-8",
    )

    bundle = normalize_client_artifact_file(
        path,
        sensitivity=ClientArtifactSensitivity.INTERNAL,
    )

    assert bundle.quality_status == ClientArtifactQualityStatus.COMPLETE
    assert bundle.human_review_recommended is False
    assert bundle.source_metadata[0].file_type == ClientArtifactFileType.JSON
    assert bundle.source_metadata[0].sensitivity == ClientArtifactSensitivity.INTERNAL

    table = bundle.normalized_tables[0]
    assert table.headers == ["field_path", "value", "value_type"]
    paths = {row.cells[0].value for row in table.rows}
    assert "$.client.name" in paths
    assert "$.controls[0].effective" in paths
    assert "$.client.locations[1]" in paths

    name_row = next(row for row in table.rows if row.cells[0].value == "$.client.name")
    assert name_row.cells[1].value == "Synthetic Client LLC"
    assert name_row.provenance is not None
    assert name_row.provenance.field_path == "$.client.name"
    assert name_row.cells[1].provenance is not None
    assert name_row.cells[1].provenance.field_path == "$.client.name"


def test_content_hash_and_source_id_are_deterministic(tmp_path):
    path = tmp_path / "synthetic-ledger.csv"
    path.write_text("account,balance\nSynthetic Cash,100\n", encoding="utf-8")

    first = normalize_client_artifact_file(path)
    second = normalize_client_artifact_file(path)

    assert first.source_metadata[0].content_hash == second.source_metadata[0].content_hash
    assert first.source_metadata[0].source_id == second.source_metadata[0].source_id
    assert first.bundle_id == second.bundle_id


def test_blank_and_duplicate_csv_headers_warn_and_recommend_review(tmp_path):
    path = tmp_path / "synthetic-ambiguous-headers.csv"
    path.write_text(
        "control_id,,control_id\nCTRL-SYN-001,Synthetic Owner,Duplicate Synthetic ID\n",
        encoding="utf-8",
    )

    bundle = normalize_client_artifact_file(path)

    assert bundle.quality_status == ClientArtifactQualityStatus.REVIEW_RECOMMENDED
    assert bundle.human_review_recommended is True
    assert bundle.overall_confidence < 0.75
    assert {"BLANK_CSV_HEADER", "DUPLICATE_CSV_HEADER"}.issubset(warning_codes(bundle))
    assert bundle.normalized_tables[0].headers == [
        "control_id",
        "unnamed_column_2",
        "control_id__duplicate_2",
    ]


def test_empty_file_warns_and_recommends_review_without_crashing(tmp_path):
    path = tmp_path / "synthetic-empty.csv"
    path.write_text("", encoding="utf-8")

    bundle = normalize_client_artifact_file(path)

    assert bundle.quality_status == ClientArtifactQualityStatus.INCOMPLETE
    assert bundle.human_review_recommended is True
    assert "EMPTY_FILE" in warning_codes(bundle)
    assert bundle.missing_required_fields == ["csv_headers", "csv_rows"]
    assert bundle.normalized_tables == []


def test_malformed_json_warns_and_recommends_review_without_crashing(tmp_path):
    path = tmp_path / "synthetic-malformed.json"
    path.write_text('{"client": "Synthetic", ', encoding="utf-8")

    bundle = normalize_client_artifact_file(path)

    assert bundle.quality_status == ClientArtifactQualityStatus.MALFORMED
    assert bundle.human_review_recommended is True
    assert "MALFORMED_JSON" in warning_codes(bundle)
    assert bundle.missing_required_fields == ["valid_json"]
    assert bundle.normalized_tables == []


def test_unsupported_extension_warns_and_recommends_review_without_crashing(tmp_path):
    path = tmp_path / "synthetic-workbook.xlsx"
    path.write_bytes(b"synthetic workbook bytes")

    bundle = normalize_client_artifact_file(path)

    assert bundle.source_metadata[0].file_type == ClientArtifactFileType.XLSX
    assert bundle.quality_status == ClientArtifactQualityStatus.REVIEW_RECOMMENDED
    assert bundle.human_review_recommended is True
    assert "UNSUPPORTED_FILE_TYPE" in warning_codes(bundle)
    assert bundle.missing_required_fields == ["supported_file_type"]
    assert bundle.normalized_tables == []


def test_output_has_no_final_decision_or_decision_field(tmp_path):
    path = tmp_path / "synthetic-control-listing.csv"
    path.write_text("control_id,status\nCTRL-SYN-001,Performed\n", encoding="utf-8")

    bundle = normalize_client_artifact_file(path)
    payload = bundle.model_dump()

    assert "final_decision" not in NormalizedClientArtifactBundle.model_fields
    assert "decision" not in NormalizedClientArtifactBundle.model_fields
    assert "final_decision" not in payload
    assert "decision" not in payload
    assert "CONTINUE" not in repr(payload)
    assert "MANUAL_REVIEW" not in repr(payload)
    assert "REJECT" not in repr(payload)


def test_tests_use_only_synthetic_client_data(tmp_path):
    path = tmp_path / "synthetic-client-data.json"
    path.write_text(
        '{"client_name": "Synthetic Client LLC", "owner": "Synthetic Owner"}',
        encoding="utf-8",
    )

    bundle = normalize_client_artifact_file(path)
    payload = bundle.model_dump()

    assert "synthetic" in repr(payload).lower()
    assert "Synthetic Client LLC" in repr(payload)
    assert "Acme" not in repr(payload)
    assert "Contoso" not in repr(payload)


def test_service_does_not_introduce_network_model_ocr_pdf_or_excel_behavior():
    source = inspect.getsource(client_artifact_normalization_service)

    forbidden_tokens = [
        "requests",
        "urllib",
        "http.client",
        "openai",
        "crewai",
        "pandas",
        "openpyxl",
        "pypdf",
        "pdfplumber",
        "pytesseract",
        "azure",
    ]
    for token in forbidden_tokens:
        assert token not in source.lower()
