from __future__ import annotations

import ast
import inspect

from ai.sandbox_verifier_agent import (
    MockSandboxVerifier,
    MockSandboxVerifierScenario,
    run_mock_sandbox_verifier,
)
import ai.sandbox_verifier_agent as sandbox_verifier_agent_module
from schemas.client_artifacts import (
    ClientArtifactFileType,
    ClientArtifactProvenanceReference,
    ClientArtifactQualityStatus,
    ClientArtifactSensitivity,
    ClientArtifactSourceMetadata,
    NormalizedClientArtifactBundle,
    NormalizedClientArtifactCell,
    NormalizedClientArtifactRow,
    NormalizedClientArtifactTable,
    NormalizedClientArtifactTextChunk,
)
from schemas.sandbox_verifier import (
    SafePublicSearchHintSensitivity,
    SandboxReviewReasonCode,
    SandboxVerifierOutput,
    SandboxVerifierRequest,
    SandboxVerifierStatus,
)


CONFIDENTIAL_VALUES = {
    "CONFIDENTIAL-CONTROL-7788",
    "Confidential Synthetic Owner",
    "Confidential internal covenant value",
    "confidential-client-artifact.csv",
    "confidential-policy-excerpt.txt",
}


def source_metadata() -> list[ClientArtifactSourceMetadata]:
    return [
        ClientArtifactSourceMetadata(
            source_id="synthetic-source-1",
            original_filename="confidential-client-artifact.csv",
            file_type=ClientArtifactFileType.CSV,
            sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
        ),
        ClientArtifactSourceMetadata(
            source_id="synthetic-source-2",
            original_filename="confidential-policy-excerpt.txt",
            file_type=ClientArtifactFileType.TXT,
            sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
        ),
    ]


def table_provenance() -> ClientArtifactProvenanceReference:
    return ClientArtifactProvenanceReference(
        source_id="synthetic-source-1",
        file_name="confidential-client-artifact.csv",
        row_number=2,
        column_name="control_id",
    )


def text_provenance() -> ClientArtifactProvenanceReference:
    return ClientArtifactProvenanceReference(
        source_id="synthetic-source-2",
        file_name="confidential-policy-excerpt.txt",
        text_chunk_id="synthetic-chunk-1",
    )


def valid_bundle() -> NormalizedClientArtifactBundle:
    return NormalizedClientArtifactBundle(
        bundle_id="synthetic-bundle-1",
        source_metadata=source_metadata(),
        normalized_tables=[
            NormalizedClientArtifactTable(
                table_id="synthetic-table-1",
                table_name="Synthetic Controls",
                headers=["control_id", "owner", "status"],
                provenance=ClientArtifactProvenanceReference(
                    source_id="synthetic-source-1",
                    file_name="confidential-client-artifact.csv",
                ),
                confidence=0.95,
                rows=[
                    NormalizedClientArtifactRow(
                        row_id="synthetic-row-1",
                        provenance=ClientArtifactProvenanceReference(
                            source_id="synthetic-source-1",
                            file_name="confidential-client-artifact.csv",
                            row_number=2,
                        ),
                        confidence=0.94,
                        cells=[
                            NormalizedClientArtifactCell(
                                column_name="control_id",
                                value="CONFIDENTIAL-CONTROL-7788",
                                raw_value="CONFIDENTIAL-CONTROL-7788",
                                provenance=table_provenance(),
                                confidence=0.96,
                            ),
                            NormalizedClientArtifactCell(
                                column_name="owner",
                                value="Confidential Synthetic Owner",
                                raw_value="Confidential Synthetic Owner",
                                confidence=0.93,
                            ),
                            NormalizedClientArtifactCell(
                                column_name="status",
                                value="performed",
                                raw_value="Performed",
                                confidence=0.94,
                            ),
                        ],
                    )
                ],
            )
        ],
        normalized_text_chunks=[
            NormalizedClientArtifactTextChunk(
                chunk_id="synthetic-chunk-1",
                text="Confidential internal covenant value",
                provenance=text_provenance(),
                confidence=0.95,
                sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
            )
        ],
        overall_confidence=0.95,
        quality_status=ClientArtifactQualityStatus.COMPLETE,
    )


def valid_request() -> SandboxVerifierRequest:
    return SandboxVerifierRequest(
        request_id="synthetic-sandbox-request-1",
        artifact_bundle_id="synthetic-bundle-1",
        allowed_artifact_metadata=source_metadata(),
        verifier_objective="Verify synthetic normalized artifact support.",
        sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
        safe_public_search_hint_policy_ref="synthetic-safe-hint-policy-v1",
    )


def output_for(scenario: MockSandboxVerifierScenario | str) -> SandboxVerifierOutput:
    return run_mock_sandbox_verifier(valid_request(), valid_bundle(), scenario)


def assert_schema_valid(output: SandboxVerifierOutput) -> None:
    assert isinstance(output, SandboxVerifierOutput)
    payload = output.model_dump(exclude={"human_review_required"})
    assert SandboxVerifierOutput.model_validate(payload) == output


def test_clean_scenario_returns_schema_valid_output_without_human_review():
    output = MockSandboxVerifier().run(
        valid_request(),
        valid_bundle(),
        MockSandboxVerifierScenario.CLEAN,
    )

    assert_schema_valid(output)
    assert output.verifier_status == SandboxVerifierStatus.SUCCESS
    assert output.human_review_required is False
    assert output.findings[0].human_review_recommended is False


def test_missing_evidence_scenario_requires_human_review():
    output = output_for(MockSandboxVerifierScenario.MISSING_EVIDENCE)

    assert_schema_valid(output)
    assert output.human_review_required is True
    assert SandboxReviewReasonCode.MISSING_EVIDENCE in output.review_reasons
    assert output.missing_evidence_items


def test_contradiction_scenario_requires_human_review():
    output = output_for(MockSandboxVerifierScenario.CONTRADICTION)

    assert_schema_valid(output)
    assert output.human_review_required is True
    assert SandboxReviewReasonCode.CONTRADICTION in output.review_reasons
    assert output.contradictions


def test_low_confidence_scenario_requires_human_review():
    output = output_for(MockSandboxVerifierScenario.LOW_CONFIDENCE)

    assert_schema_valid(output)
    assert output.human_review_required is True
    assert SandboxReviewReasonCode.LOW_CONFIDENCE in output.review_reasons
    assert output.findings[0].confidence < 0.75


def test_tool_error_scenario_requires_human_review():
    output = output_for(MockSandboxVerifierScenario.TOOL_ERROR)

    assert_schema_valid(output)
    assert output.verifier_status == SandboxVerifierStatus.TOOL_ERROR
    assert output.human_review_required is True
    assert SandboxReviewReasonCode.TOOL_ERROR in output.review_reasons
    assert output.tool_errors


def test_invalid_input_scenario_requires_human_review():
    output = output_for(MockSandboxVerifierScenario.INVALID_INPUT)

    assert_schema_valid(output)
    assert output.verifier_status == SandboxVerifierStatus.INVALID_INPUT
    assert output.human_review_required is True
    assert SandboxReviewReasonCode.INVALID_INPUT in output.review_reasons


def test_safe_hint_scenario_emits_only_public_or_non_sensitive_hint_candidates():
    output = output_for(MockSandboxVerifierScenario.SAFE_HINT)

    assert_schema_valid(output)
    assert output.human_review_required is False
    assert output.safe_public_search_hint_candidates
    assert {
        hint.sensitivity for hint in output.safe_public_search_hint_candidates
    }.issubset(
        {
            SafePublicSearchHintSensitivity.PUBLIC,
            SafePublicSearchHintSensitivity.NON_SENSITIVE,
        }
    )


def test_safe_hints_do_not_leak_confidential_artifact_values():
    output = output_for(MockSandboxVerifierScenario.SAFE_HINT)
    hint_payload = [
        hint.model_dump(mode="json") for hint in output.safe_public_search_hint_candidates
    ]
    hint_text = repr(hint_payload)

    assert output.safe_public_search_hint_candidates
    for confidential_value in CONFIDENTIAL_VALUES:
        assert confidential_value not in hint_text


def test_output_contains_no_final_decision_or_decision_field():
    output = output_for(MockSandboxVerifierScenario.CLEAN)
    payload = output.model_dump(mode="json")

    assert "final_decision" not in SandboxVerifierOutput.model_fields
    assert "decision" not in SandboxVerifierOutput.model_fields
    assert "final_decision" not in payload
    assert "decision" not in payload


def test_output_does_not_use_final_decision_values_as_verifier_outcomes():
    final_decision_values = {"CONTINUE", "MANUAL_REVIEW", "REJECT"}

    for scenario in MockSandboxVerifierScenario:
        payload_text = repr(output_for(scenario).model_dump(mode="json"))
        assert final_decision_values.isdisjoint(payload_text.split())
        assert all(value not in payload_text for value in final_decision_values)


def test_mock_verifier_source_does_not_introduce_external_or_runtime_behavior():
    source = inspect.getsource(sandbox_verifier_agent_module)
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
    forbidden_calls = {"open", "exec", "eval", "compile"}
    forbidden_runtime_terms = [
        "docker",
        "virtualmachine",
        "virtual machine",
        "subprocess",
        "network",
        "ocr",
        "pdf parsing",
        "excel parsing",
    ]

    assert imported_roots.isdisjoint(forbidden_imports)
    assert called_names.isdisjoint(forbidden_calls)
    assert all(term not in source.lower() for term in forbidden_runtime_terms)


def test_test_data_is_synthetic_only():
    output = output_for(MockSandboxVerifierScenario.SAFE_HINT)
    payload_text = repr(output.model_dump(mode="json"))

    assert "Synthetic" in payload_text
    assert "Acme" not in payload_text
    assert "Contoso" not in payload_text
    assert "Globex" not in payload_text
