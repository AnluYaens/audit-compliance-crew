import ast
from datetime import datetime, timezone
import inspect

import pytest

import services.safe_hint_bridge_service as safe_hint_bridge_module
from ai.public_research_agent import run_public_research_mvp
from schemas.client_artifacts import (
    ClientArtifactProvenanceReference,
    ClientArtifactSensitivity,
)
from schemas.sandbox_verifier import (
    SafePublicSearchHintCandidate,
    SafePublicSearchHintSensitivity,
    SafePublicSearchHintType,
    SandboxReviewReasonCode,
    SandboxVerifierOutput,
    SandboxVerifierStatus,
)
from services.safe_hint_bridge_service import filter_safe_public_search_hints


GENERATED_AT = datetime(2026, 7, 14, tzinfo=timezone.utc)
FINAL_OUTCOMES = {"CONTINUE", "MANUAL_REVIEW", "REJECT"}


def synthetic_provenance(
    *,
    source_id: str = "synthetic-local-source-1",
    file_name: str = "synthetic-local-input.csv",
) -> ClientArtifactProvenanceReference:
    return ClientArtifactProvenanceReference(
        source_id=source_id,
        file_name=file_name,
        row_number=2,
        column_name="public_company_name",
    )


def safe_hint(
    *,
    hint_id: str = "synthetic-safe-hint-1",
    hint_text: str = "Synthetic Public Entity annual report",
    hint_type: SafePublicSearchHintType = SafePublicSearchHintType.ANNUAL_REPORT,
    safe_reason: str = "Uses verified synthetic public entity terms only.",
    sensitivity: SafePublicSearchHintSensitivity = SafePublicSearchHintSensitivity.PUBLIC,
    provenance: ClientArtifactProvenanceReference | None = None,
    confidence: float = 0.91,
    human_review_recommended: bool = False,
) -> SafePublicSearchHintCandidate:
    return SafePublicSearchHintCandidate(
        hint_id=hint_id,
        hint_text=hint_text,
        hint_type=hint_type,
        safe_reason=safe_reason,
        sensitivity=sensitivity,
        provenance=provenance,
        confidence=confidence,
        human_review_recommended=human_review_recommended,
    )


def verifier_output(
    hints: list[SafePublicSearchHintCandidate] | None = None,
    *,
    status: SandboxVerifierStatus = SandboxVerifierStatus.SUCCESS,
    missing_evidence_items: list[str] | None = None,
    contradictions: list[str] | None = None,
    tool_errors: list[str] | None = None,
    review_reasons: list[SandboxReviewReasonCode] | None = None,
) -> SandboxVerifierOutput:
    return SandboxVerifierOutput(
        request_id="synthetic-sandbox-request-1",
        artifact_bundle_id="synthetic-artifact-bundle-1",
        verifier_status=status,
        safe_public_search_hint_candidates=hints or [],
        missing_evidence_items=missing_evidence_items or [],
        contradictions=contradictions or [],
        tool_errors=tool_errors or [],
        review_reasons=review_reasons or [],
        generated_at=GENERATED_AT,
    )


def test_clean_output_returns_approved_sanitized_hints():
    original_hints = [
        safe_hint(provenance=synthetic_provenance()),
        safe_hint(
            hint_id="synthetic-safe-hint-2",
            hint_text="Synthetic Public Entity regulator filing",
            hint_type=SafePublicSearchHintType.REGULATOR_SOURCE,
            sensitivity=SafePublicSearchHintSensitivity.NON_SENSITIVE,
            provenance=synthetic_provenance(file_name="synthetic-local-input-2.csv"),
            confidence=0.88,
        ),
    ]
    output = verifier_output(original_hints)

    result = filter_safe_public_search_hints(output)

    assert [hint.hint_id for hint in result] == [
        "synthetic-safe-hint-1",
        "synthetic-safe-hint-2",
    ]
    assert all(returned is not original for returned, original in zip(result, original_hints))
    assert all(hint.provenance is None for hint in result)
    assert all(hint.human_review_recommended is False for hint in result)
    assert output.safe_public_search_hint_candidates == original_hints
    assert all(hint.provenance is not None for hint in original_hints)


def test_review_required_output_returns_no_hints():
    output = verifier_output(
        [safe_hint()],
        status=SandboxVerifierStatus.REVIEW_REQUIRED,
        review_reasons=[SandboxReviewReasonCode.HUMAN_REVIEW_RECOMMENDED],
    )

    assert filter_safe_public_search_hints(output) == []


@pytest.mark.parametrize(
    "status, review_reasons, tool_errors",
    [
        (
            SandboxVerifierStatus.INVALID_INPUT,
            [SandboxReviewReasonCode.INVALID_INPUT],
            [],
        ),
        (
            SandboxVerifierStatus.TOOL_ERROR,
            [SandboxReviewReasonCode.TOOL_ERROR],
            ["Synthetic sandbox verifier tool failure."],
        ),
    ],
)
def test_invalid_input_and_tool_error_outputs_return_no_hints(
    status: SandboxVerifierStatus,
    review_reasons: list[SandboxReviewReasonCode],
    tool_errors: list[str],
):
    output = verifier_output(
        [safe_hint()],
        status=status,
        review_reasons=review_reasons,
        tool_errors=tool_errors,
    )

    assert filter_safe_public_search_hints(output) == []


@pytest.mark.parametrize(
    "output",
    [
        verifier_output(
            [safe_hint()],
            missing_evidence_items=["Synthetic public support is missing."],
        ),
        verifier_output(
            [safe_hint()],
            contradictions=["Synthetic public support values conflict."],
        ),
    ],
)
def test_missing_evidence_and_contradiction_outputs_return_no_hints(
    output: SandboxVerifierOutput,
):
    assert filter_safe_public_search_hints(output) == []


def test_low_confidence_hint_is_filtered_out():
    output = verifier_output(
        [safe_hint(confidence=0.74), safe_hint(hint_id="synthetic-safe-hint-2", confidence=0.75)]
    )

    result = filter_safe_public_search_hints(output)

    assert [hint.hint_id for hint in result] == ["synthetic-safe-hint-2"]


def test_review_flagged_hint_fails_closed_for_the_output():
    output = verifier_output(
        [
            safe_hint(),
            safe_hint(
                hint_id="synthetic-review-hint-2",
                human_review_recommended=True,
            ),
        ]
    )

    assert output.human_review_required is True
    assert filter_safe_public_search_hints(output) == []


@pytest.mark.parametrize(
    "unsafe_sensitivity",
    [ClientArtifactSensitivity.CONFIDENTIAL, ClientArtifactSensitivity.RESTRICTED],
)
def test_confidential_and_restricted_hint_like_values_are_filtered_out(
    unsafe_sensitivity: ClientArtifactSensitivity,
):
    unsafe_hint = safe_hint().model_copy(update={"sensitivity": unsafe_sensitivity})
    output = verifier_output([unsafe_hint])

    assert filter_safe_public_search_hints(output) == []


@pytest.mark.parametrize(
    "update",
    [
        {"hint_id": "synthetic-confidential-hint"},
        {"hint_text": "Synthetic restricted entity report"},
        {"safe_reason": "Uses an internal-only label."},
        {"hint_text": "Synthetic raw_client source"},
        {"safe_reason": "Derived from a client-artifact label."},
        {"hint_text": "Synthetic private filing"},
        {"safe_reason": "Contains a secret descriptor."},
        {"hint_id": "synthetic-password-hint"},
        {"hint_text": "Synthetic access_token filing"},
        {"safe_reason": "Contains an API-key label."},
        {"hint_id": "synthetic-credential-hint"},
    ],
)
def test_unsafe_lexical_markers_in_public_fields_are_filtered_out(
    update: dict[str, object],
):
    output = verifier_output([safe_hint().model_copy(update=update)])

    assert filter_safe_public_search_hints(output) == []


@pytest.mark.parametrize(
    "provenance",
    [
        synthetic_provenance(source_id="synthetic-confidential-source"),
        synthetic_provenance(file_name="synthetic-private-client-artifact.csv"),
        ClientArtifactProvenanceReference(
            source_id="synthetic-local-source-2",
            sheet_name="restricted_internal-only_sheet",
        ),
        ClientArtifactProvenanceReference(
            source_id="synthetic-local-source-3",
            field_path="credentials.api_token",
        ),
    ],
)
def test_unsafe_lexical_markers_in_provenance_are_filtered_out(
    provenance: ClientArtifactProvenanceReference,
):
    output = verifier_output([safe_hint(provenance=provenance)])

    assert filter_safe_public_search_hints(output) == []


def test_invalid_input_object_and_invalid_hint_type_fail_closed():
    invalid_hint_type = safe_hint().model_copy(update={"hint_type": "annual_report"})

    assert filter_safe_public_search_hints(object()) == []  # type: ignore[arg-type]
    assert filter_safe_public_search_hints(verifier_output([invalid_hint_type])) == []


def test_clean_bridge_output_is_accepted_by_public_research_mvp():
    hints = filter_safe_public_search_hints(
        verifier_output([safe_hint(provenance=synthetic_provenance())])
    )

    public_research_output = run_public_research_mvp(hints)

    assert public_research_output.candidate_sources
    assert public_research_output.extracted_evidence


def test_bridge_output_has_no_decisions_or_final_outcomes():
    result = filter_safe_public_search_hints(verifier_output([safe_hint()]))
    payload = [hint.model_dump(mode="json") for hint in result]
    payload_text = repr(payload)

    assert "final_decision" not in SafePublicSearchHintCandidate.model_fields
    assert "decision" not in SafePublicSearchHintCandidate.model_fields
    assert all("final_decision" not in hint for hint in payload)
    assert all("decision" not in hint for hint in payload)
    assert all(outcome not in payload_text for outcome in FINAL_OUTCOMES)


def test_bridge_source_introduces_no_external_or_unsafe_runtime_behavior():
    source = inspect.getsource(safe_hint_bridge_module)
    parsed_source = ast.parse(source)
    imported_roots: set[str] = set()
    called_names: set[str] = set()

    for node in ast.walk(parsed_source):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0].lower() for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".")[0].lower())
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id.lower())
            if isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr.lower())

    forbidden_imports = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "openai",
        "crewai",
        "azure",
        "pytesseract",
        "pypdf",
        "pdfplumber",
        "openpyxl",
        "pandas",
    }
    assert imported_roots.isdisjoint(forbidden_imports)
    assert called_names.isdisjoint({"open", "exec", "eval", "compile"})
    assert all(
        term not in source.lower()
        for term in {"docker", "virtualmachine", "virtual machine"}
    )


def test_bridge_test_data_is_synthetic_only():
    payload_text = repr(
        filter_safe_public_search_hints(verifier_output([safe_hint()]))[0].model_dump(mode="json")
    )

    assert "Synthetic" in payload_text
    assert "Acme" not in payload_text
    assert "Contoso" not in payload_text
    assert "Globex" not in payload_text
