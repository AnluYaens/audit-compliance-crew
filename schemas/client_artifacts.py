from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TypeAlias

from pydantic import Field, computed_field, model_validator

from schemas.contracts import NonEmptyStr, StrictContractModel


LOW_ARTIFACT_CONFIDENCE_THRESHOLD = 0.75

ArtifactValue: TypeAlias = str | int | float | bool | None


class ClientArtifactFileType(str, Enum):
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"
    XLSX = "xlsx"
    TXT = "txt"
    UNKNOWN = "unknown"


class ClientArtifactSensitivity(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


class ClientArtifactWarningSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ClientArtifactQualityStatus(str, Enum):
    COMPLETE = "COMPLETE"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    INCOMPLETE = "INCOMPLETE"
    MALFORMED = "MALFORMED"


class ClientArtifactSourceMetadata(StrictContractModel):
    source_id: NonEmptyStr = Field(description="Stable identifier for the client-provided artifact.")
    original_filename: NonEmptyStr = Field(description="Original filename supplied by the client.")
    file_type: ClientArtifactFileType = Field(description="Normalized source file type.")
    content_hash: NonEmptyStr | None = Field(
        default=None,
        description="Content checksum or hash when available.",
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the artifact was received or generated.",
    )
    sensitivity: ClientArtifactSensitivity = Field(
        default=ClientArtifactSensitivity.UNKNOWN,
        description="Confidentiality classification for local handling and review.",
    )


class ClientArtifactProvenanceReference(StrictContractModel):
    source_id: NonEmptyStr | None = Field(
        default=None,
        description="Source artifact identifier when available.",
    )
    file_name: NonEmptyStr | None = Field(
        default=None,
        description="Source filename when an identifier is unavailable.",
    )
    page_number: int | None = Field(
        default=None,
        ge=1,
        description="One-based page number for page-based artifacts.",
    )
    sheet_name: NonEmptyStr | None = Field(
        default=None,
        description="Workbook sheet name for spreadsheet artifacts.",
    )
    row_number: int | None = Field(
        default=None,
        ge=1,
        description="One-based row number for tabular artifacts.",
    )
    column_name: NonEmptyStr | None = Field(
        default=None,
        description="Column or field label for tabular artifacts.",
    )
    text_chunk_id: NonEmptyStr | None = Field(
        default=None,
        description="Normalized text chunk identifier when applicable.",
    )
    field_path: NonEmptyStr | None = Field(
        default=None,
        description="Structured field path for JSON or normalized record sources.",
    )

    @model_validator(mode="after")
    def require_source_locator(self) -> "ClientArtifactProvenanceReference":
        if self.source_id is None and self.file_name is None:
            raise ValueError("Provenance references require source_id or file_name.")
        return self


class ClientArtifactParserWarning(StrictContractModel):
    warning_code: NonEmptyStr = Field(description="Stable machine-readable warning code.")
    message: NonEmptyStr = Field(description="Short warning description.")
    severity: ClientArtifactWarningSeverity = Field(description="Warning severity.")
    provenance: ClientArtifactProvenanceReference | None = Field(
        default=None,
        description="Source location associated with the warning when available.",
    )
    human_review_recommended: bool = Field(
        default=True,
        description="True when the warning should be surfaced to an auditor.",
    )


class NormalizedClientArtifactCell(StrictContractModel):
    column_name: NonEmptyStr = Field(description="Normalized column name for this value.")
    value: ArtifactValue = Field(description="Normalized scalar value.")
    raw_value: ArtifactValue = Field(
        default=None,
        description="Original scalar value before normalization when retained.",
    )
    provenance: ClientArtifactProvenanceReference | None = Field(
        default=None,
        description="Source location for this cell value.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Cell-level normalization confidence from zero to one.",
    )


class NormalizedClientArtifactRow(StrictContractModel):
    row_id: NonEmptyStr | None = Field(
        default=None,
        description="Stable normalized row identifier when available.",
    )
    cells: list[NormalizedClientArtifactCell] = Field(
        min_length=1,
        description="Normalized cells in the row.",
    )
    provenance: ClientArtifactProvenanceReference | None = Field(
        default=None,
        description="Source location for the row as a whole.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Row-level normalization confidence from zero to one.",
    )


class NormalizedClientArtifactTable(StrictContractModel):
    table_id: NonEmptyStr = Field(description="Stable normalized table identifier.")
    table_name: NonEmptyStr | None = Field(
        default=None,
        description="Source or normalized table name when available.",
    )
    headers: list[NonEmptyStr] = Field(
        min_length=1,
        description="Normalized table headers.",
    )
    rows: list[NormalizedClientArtifactRow] = Field(
        default_factory=list,
        description="Normalized row records.",
    )
    provenance: ClientArtifactProvenanceReference | None = Field(
        default=None,
        description="Source location for the table as a whole.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Table-level normalization confidence from zero to one.",
    )

    @model_validator(mode="after")
    def validate_cells_match_headers(self) -> "NormalizedClientArtifactTable":
        header_names = set(self.headers)
        for row in self.rows:
            for cell in row.cells:
                if cell.column_name not in header_names:
                    raise ValueError(
                        f"Cell column {cell.column_name} is not present in table headers."
                    )
        return self


class NormalizedClientArtifactTextChunk(StrictContractModel):
    chunk_id: NonEmptyStr = Field(description="Stable normalized text chunk identifier.")
    text: NonEmptyStr = Field(description="Normalized text extracted from the source artifact.")
    provenance: ClientArtifactProvenanceReference = Field(
        description="Source location for the text chunk.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Text chunk normalization confidence from zero to one.",
    )
    sensitivity: ClientArtifactSensitivity = Field(
        default=ClientArtifactSensitivity.UNKNOWN,
        description="Sensitivity classification for this text chunk.",
    )


class NormalizedClientArtifactBundle(StrictContractModel):
    bundle_id: NonEmptyStr = Field(description="Stable identifier for the normalized bundle.")
    source_metadata: list[ClientArtifactSourceMetadata] = Field(
        min_length=1,
        description="Source files included in the normalized bundle.",
    )
    normalized_tables: list[NormalizedClientArtifactTable] = Field(default_factory=list)
    normalized_text_chunks: list[NormalizedClientArtifactTextChunk] = Field(default_factory=list)
    warnings: list[ClientArtifactParserWarning] = Field(default_factory=list)
    missing_required_fields: list[NonEmptyStr] = Field(
        default_factory=list,
        description="Required normalized fields that are absent or unverifiable.",
    )
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Bundle-level normalization confidence from zero to one.",
    )
    quality_status: ClientArtifactQualityStatus = Field(
        default=ClientArtifactQualityStatus.REVIEW_RECOMMENDED,
        description="Non-decisional quality status for later deterministic routing.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the normalized bundle was generated.",
    )

    @computed_field
    @property
    def human_review_recommended(self) -> bool:
        if self.quality_status != ClientArtifactQualityStatus.COMPLETE:
            return True
        if self.missing_required_fields:
            return True
        if self.overall_confidence < LOW_ARTIFACT_CONFIDENCE_THRESHOLD:
            return True
        return any(warning.human_review_recommended for warning in self.warnings)
