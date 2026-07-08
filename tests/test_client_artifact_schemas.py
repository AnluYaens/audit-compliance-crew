from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from schemas.client_artifacts import (
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
    NormalizedClientArtifactTextChunk,
)


GENERATED_AT = datetime(2026, 7, 8, tzinfo=timezone.utc)


def source_metadata() -> ClientArtifactSourceMetadata:
    return ClientArtifactSourceMetadata(
        source_id="synthetic-source-1",
        original_filename="synthetic-control-listing.csv",
        file_type=ClientArtifactFileType.CSV,
        content_hash="sha256:synthetic-test-hash",
        received_at=GENERATED_AT,
        sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
    )


def csv_provenance() -> ClientArtifactProvenanceReference:
    return ClientArtifactProvenanceReference(
        source_id="synthetic-source-1",
        file_name="synthetic-control-listing.csv",
        row_number=2,
        column_name="control_id",
    )


def pdf_provenance() -> ClientArtifactProvenanceReference:
    return ClientArtifactProvenanceReference(
        source_id="synthetic-source-2",
        file_name="synthetic-policy-excerpt.pdf",
        page_number=4,
        text_chunk_id="chunk-policy-1",
    )


def normalized_table() -> NormalizedClientArtifactTable:
    return NormalizedClientArtifactTable(
        table_id="table-controls",
        table_name="Synthetic Controls",
        headers=["control_id", "owner", "status"],
        provenance=ClientArtifactProvenanceReference(
            source_id="synthetic-source-1",
            file_name="synthetic-control-listing.csv",
        ),
        confidence=0.93,
        rows=[
            NormalizedClientArtifactRow(
                row_id="row-1",
                provenance=ClientArtifactProvenanceReference(
                    source_id="synthetic-source-1",
                    file_name="synthetic-control-listing.csv",
                    row_number=2,
                ),
                confidence=0.91,
                cells=[
                    NormalizedClientArtifactCell(
                        column_name="control_id",
                        value="CTRL-001",
                        raw_value="CTRL-001",
                        provenance=csv_provenance(),
                        confidence=0.96,
                    ),
                    NormalizedClientArtifactCell(
                        column_name="owner",
                        value="Synthetic Owner",
                        raw_value="Synthetic Owner",
                        confidence=0.90,
                    ),
                    NormalizedClientArtifactCell(
                        column_name="status",
                        value="performed",
                        raw_value="Performed",
                        confidence=0.88,
                    ),
                ],
            )
        ],
    )


def text_chunk() -> NormalizedClientArtifactTextChunk:
    return NormalizedClientArtifactTextChunk(
        chunk_id="chunk-policy-1",
        text="Synthetic policy text prepared for schema validation only.",
        provenance=pdf_provenance(),
        confidence=0.89,
        sensitivity=ClientArtifactSensitivity.INTERNAL,
    )


def parser_warning() -> ClientArtifactParserWarning:
    return ClientArtifactParserWarning(
        warning_code="AMBIGUOUS_HEADER",
        message="A synthetic column heading needs human confirmation.",
        severity=ClientArtifactWarningSeverity.MEDIUM,
        provenance=csv_provenance(),
        human_review_recommended=True,
    )


def valid_bundle() -> NormalizedClientArtifactBundle:
    return NormalizedClientArtifactBundle(
        bundle_id="bundle-synthetic-1",
        source_metadata=[
            source_metadata(),
            ClientArtifactSourceMetadata(
                source_id="synthetic-source-2",
                original_filename="synthetic-policy-excerpt.pdf",
                file_type=ClientArtifactFileType.PDF,
                received_at=GENERATED_AT,
                sensitivity=ClientArtifactSensitivity.INTERNAL,
            ),
        ],
        normalized_tables=[normalized_table()],
        normalized_text_chunks=[text_chunk()],
        warnings=[parser_warning()],
        missing_required_fields=["approval_date"],
        overall_confidence=0.86,
        quality_status=ClientArtifactQualityStatus.REVIEW_RECOMMENDED,
        generated_at=GENERATED_AT,
    )


def test_valid_normalized_artifact_payload_instantiates():
    bundle = valid_bundle()

    assert bundle.bundle_id == "bundle-synthetic-1"
    assert bundle.source_metadata[0].file_type == ClientArtifactFileType.CSV
    assert bundle.normalized_tables[0].table_id == "table-controls"
    assert bundle.normalized_text_chunks[0].chunk_id == "chunk-policy-1"
    assert bundle.human_review_recommended is True


def test_provenance_represents_csv_row_and_column_reference():
    provenance = csv_provenance()

    assert provenance.file_name == "synthetic-control-listing.csv"
    assert provenance.row_number == 2
    assert provenance.column_name == "control_id"


def test_provenance_represents_pdf_page_reference_without_parsing():
    provenance = pdf_provenance()

    assert provenance.file_name == "synthetic-policy-excerpt.pdf"
    assert provenance.page_number == 4
    assert provenance.text_chunk_id == "chunk-policy-1"


def test_parser_warning_can_recommend_human_review():
    warning = parser_warning()

    assert warning.human_review_recommended is True
    assert warning.severity == ClientArtifactWarningSeverity.MEDIUM
    assert warning.provenance is not None
    assert warning.provenance.row_number == 2


def test_sensitivity_classification_is_represented():
    bundle = valid_bundle()

    assert bundle.source_metadata[0].sensitivity == ClientArtifactSensitivity.CONFIDENTIAL
    assert bundle.normalized_text_chunks[0].sensitivity == ClientArtifactSensitivity.INTERNAL


def test_final_decision_and_decision_fields_are_not_accepted():
    payload = valid_bundle().model_dump()
    payload["final_decision"] = "CONTINUE"

    with pytest.raises(ValidationError) as exc_info:
        NormalizedClientArtifactBundle.model_validate(payload)

    assert any(error["loc"] == ("final_decision",) for error in exc_info.value.errors())
    assert "final_decision" not in NormalizedClientArtifactBundle.model_fields

    payload = valid_bundle().model_dump()
    payload["decision"] = "MANUAL_REVIEW"

    with pytest.raises(ValidationError) as exc_info:
        NormalizedClientArtifactBundle.model_validate(payload)

    assert any(error["loc"] == ("decision",) for error in exc_info.value.errors())
    assert "decision" not in NormalizedClientArtifactBundle.model_fields


def test_malformed_required_fields_fail_validation():
    with pytest.raises(ValidationError):
        ClientArtifactSourceMetadata(
            source_id="",
            original_filename="synthetic-control-listing.csv",
            file_type=ClientArtifactFileType.CSV,
        )

    with pytest.raises(ValidationError):
        ClientArtifactProvenanceReference(row_number=1, column_name="control_id")

    with pytest.raises(ValidationError):
        NormalizedClientArtifactTable(
            table_id="table-controls",
            headers=["control_id"],
            rows=[
                NormalizedClientArtifactRow(
                    confidence=0.95,
                    cells=[
                        NormalizedClientArtifactCell(
                            column_name="unexpected_column",
                            value="synthetic value",
                            confidence=0.95,
                        )
                    ],
                )
            ],
            confidence=0.95,
        )


def test_tables_and_text_chunks_preserve_confidence_and_provenance():
    bundle = valid_bundle()
    table = bundle.normalized_tables[0]
    chunk = bundle.normalized_text_chunks[0]

    assert table.confidence == 0.93
    assert table.rows[0].confidence == 0.91
    assert table.rows[0].cells[0].confidence == 0.96
    assert table.rows[0].cells[0].provenance is not None
    assert table.rows[0].cells[0].provenance.column_name == "control_id"
    assert chunk.confidence == 0.89
    assert chunk.provenance.page_number == 4


def test_test_payload_uses_synthetic_data_only():
    bundle = valid_bundle()

    assert all(
        metadata.original_filename.startswith("synthetic-")
        for metadata in bundle.source_metadata
    )
    assert all(metadata.source_id.startswith("synthetic-") for metadata in bundle.source_metadata)
    assert "Synthetic" in bundle.normalized_text_chunks[0].text
