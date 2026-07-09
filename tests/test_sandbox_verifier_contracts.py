import ast
from datetime import datetime, timezone
import inspect

import pytest
from pydantic import ValidationError

import schemas.sandbox_verifier as sandbox_verifier_module
from schemas.client_artifacts import (
    ClientArtifactFileType,
    ClientArtifactProvenanceReference,
    ClientArtifactSensitivity,
    ClientArtifactSourceMetadata,
)
from schemas.sandbox_verifier import (
    LocalEvidenceFinding,
    SafePublicSearchHintCandidate,
    SafePublicSearchHintSensitivity,
    SafePublicSearchHintType,
    SandboxFindingType,
    SandboxReviewReasonCode,
    SandboxVerifierOutput,
    SandboxVerifierRequest,
    SandboxVerifierStatus,
)


GENERATED_AT = datetime(2026, 7, 9, tzinfo=timezone.utc)


def source_metadata() -> ClientArtifactSourceMetadata:
    return ClientArtifactSourceMetadata(
        source_id="synthetic-source-1",
        original_filename="synthetic-verifier-artifact.csv",
        file_type=ClientArtifactFileType.CSV,
        content_hash="sha256:synthetic-verifier-hash",
        received_at=GENERATED_AT,
        sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
    )


def provenance() -> ClientArtifactProvenanceReference:
    return ClientArtifactProvenanceReference(
        source_id="synthetic-source-1",
        file_name="synthetic-verifier-artifact.csv",
        row_number=3,
        column_name="synthetic_claim",
    )


def valid_request() -> SandboxVerifierRequest:
    return SandboxVerifierRequest(
        request_id="sandbox-request-1",
        artifact_bundle_id="synthetic-bundle-1",
        allowed_artifact_metadata=[source_metadata()],
        verifier_objective="Verify synthetic client-provided evidence support.",
        sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
        created_at=GENERATED_AT,
        safe_public_search_hint_policy_ref="policy-safe-public-hints-v1",
    )


def supported_finding() -> LocalEvidenceFinding:
    return LocalEvidenceFinding(
        finding_id="finding-supported-1",
        finding_type=SandboxFindingType.SUPPORTED_CLAIM,
        claim_summary="Synthetic evidence supports the sample control owner.",
        provenance_references=[provenance()],
        confidence=0.91,
        sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
    )


def review_finding(
    finding_type: SandboxFindingType,
    review_reason: SandboxReviewReasonCode,
    confidence: float = 0.91,
) -> LocalEvidenceFinding:
    return LocalEvidenceFinding(
        finding_id=f"finding-{finding_type.value}",
        finding_type=finding_type,
        claim_summary=f"Synthetic {finding_type.value} requires auditor review.",
        provenance_references=[provenance()],
        confidence=confidence,
        sensitivity=ClientArtifactSensitivity.INTERNAL,
        human_review_recommended=True,
        review_reason_codes=[review_reason],
    )


def safe_hint() -> SafePublicSearchHintCandidate:
    return SafePublicSearchHintCandidate(
        hint_id="hint-1",
        hint_text="Synthetic Example Company annual report",
        hint_type=SafePublicSearchHintType.ANNUAL_REPORT,
        safe_reason="The terms contain only synthetic public company-style descriptors.",
        sensitivity=SafePublicSearchHintSensitivity.PUBLIC,
        provenance=provenance(),
        confidence=0.88,
    )


def valid_output() -> SandboxVerifierOutput:
    return SandboxVerifierOutput(
        request_id="sandbox-request-1",
        artifact_bundle_id="synthetic-bundle-1",
        verifier_status=SandboxVerifierStatus.SUCCESS,
        findings=[supported_finding()],
        safe_public_search_hint_candidates=[safe_hint()],
        generated_at=GENERATED_AT,
    )


def test_valid_sandbox_verifier_request_instantiates():
    request = valid_request()

    assert request.request_id == "sandbox-request-1"
    assert request.artifact_bundle_id == "synthetic-bundle-1"
    assert request.allowed_artifact_metadata[0].source_id == "synthetic-source-1"
    assert request.safe_public_search_hint_policy_ref == "policy-safe-public-hints-v1"


def test_supported_finding_preserves_provenance_confidence_and_sensitivity():
    finding = supported_finding()

    assert finding.finding_type == SandboxFindingType.SUPPORTED_CLAIM
    assert finding.provenance_references[0].row_number == 3
    assert finding.confidence == 0.91
    assert finding.sensitivity == ClientArtifactSensitivity.CONFIDENTIAL
    assert finding.human_review_recommended is False


def test_missing_evidence_finding_requires_human_review():
    finding = review_finding(
        SandboxFindingType.MISSING_EVIDENCE,
        SandboxReviewReasonCode.MISSING_EVIDENCE,
    )

    assert finding.human_review_recommended is True

    with pytest.raises(ValidationError):
        LocalEvidenceFinding(
            finding_id="finding-missing-without-review",
            finding_type=SandboxFindingType.MISSING_EVIDENCE,
            claim_summary="Synthetic missing evidence without review flag.",
            confidence=0.9,
            sensitivity=ClientArtifactSensitivity.INTERNAL,
            review_reason_codes=[SandboxReviewReasonCode.MISSING_EVIDENCE],
        )


def test_contradiction_finding_requires_human_review():
    finding = review_finding(
        SandboxFindingType.CONTRADICTION,
        SandboxReviewReasonCode.CONTRADICTION,
    )

    assert finding.human_review_recommended is True


def test_low_confidence_finding_requires_human_review():
    finding = review_finding(
        SandboxFindingType.LOW_CONFIDENCE,
        SandboxReviewReasonCode.LOW_CONFIDENCE,
        confidence=0.42,
    )

    assert finding.human_review_recommended is True

    with pytest.raises(ValidationError):
        LocalEvidenceFinding(
            finding_id="finding-low-confidence-without-review",
            finding_type=SandboxFindingType.SUPPORTED_CLAIM,
            claim_summary="Synthetic low confidence support without review flag.",
            provenance_references=[provenance()],
            confidence=0.42,
            sensitivity=ClientArtifactSensitivity.INTERNAL,
        )


def test_tool_error_or_invalid_input_output_requires_human_review():
    invalid_input_output = valid_output().model_copy(
        update={
            "verifier_status": SandboxVerifierStatus.INVALID_INPUT,
            "review_reasons": [SandboxReviewReasonCode.INVALID_INPUT],
        },
    )
    tool_error_output = valid_output().model_copy(
        update={
            "verifier_status": SandboxVerifierStatus.TOOL_ERROR,
            "tool_errors": ["Synthetic verifier tool error."],
            "review_reasons": [SandboxReviewReasonCode.TOOL_ERROR],
        },
    )

    assert invalid_input_output.human_review_required is True
    assert tool_error_output.human_review_required is True


def test_output_requires_human_review_for_missing_evidence_and_contradictions():
    missing_output = valid_output().model_copy(
        update={"missing_evidence_items": ["Synthetic support item not present."]},
    )
    contradiction_output = valid_output().model_copy(
        update={"contradictions": ["Synthetic artifact values conflict."]},
    )

    assert missing_output.human_review_required is True
    assert contradiction_output.human_review_required is True


def test_safe_public_search_hint_accepts_only_public_or_non_sensitive_classifications():
    public_hint = safe_hint()
    non_sensitive_hint = safe_hint().model_copy(
        update={"sensitivity": SafePublicSearchHintSensitivity.NON_SENSITIVE},
    )

    assert public_hint.sensitivity == SafePublicSearchHintSensitivity.PUBLIC
    assert non_sensitive_hint.sensitivity == SafePublicSearchHintSensitivity.NON_SENSITIVE


def test_confidential_or_restricted_safe_public_search_hint_is_rejected():
    payload = safe_hint().model_dump()
    payload["sensitivity"] = ClientArtifactSensitivity.CONFIDENTIAL.value

    with pytest.raises(ValidationError):
        SafePublicSearchHintCandidate.model_validate(payload)

    payload = safe_hint().model_dump()
    payload["sensitivity"] = ClientArtifactSensitivity.RESTRICTED.value

    with pytest.raises(ValidationError):
        SafePublicSearchHintCandidate.model_validate(payload)


@pytest.mark.parametrize("model_factory", [valid_request, supported_finding, safe_hint, valid_output])
def test_final_decision_and_decision_fields_are_rejected_or_absent(model_factory):
    model = model_factory()

    assert "final_decision" not in model.__class__.model_fields
    assert "decision" not in model.__class__.model_fields

    payload = model.model_dump()
    payload["final_decision"] = "CONTINUE"

    with pytest.raises(ValidationError) as exc_info:
        model.__class__.model_validate(payload)

    assert any(error["loc"] == ("final_decision",) for error in exc_info.value.errors())

    payload = model.model_dump()
    payload["decision"] = "MANUAL_REVIEW"

    with pytest.raises(ValidationError) as exc_info:
        model.__class__.model_validate(payload)

    assert any(error["loc"] == ("decision",) for error in exc_info.value.errors())


@pytest.mark.parametrize("decision_value", ["CONTINUE", "MANUAL_REVIEW", "REJECT"])
def test_final_outcomes_are_not_accepted_as_verifier_outcomes(decision_value):
    payload = valid_output().model_dump()
    payload["verifier_status"] = decision_value

    with pytest.raises(ValidationError):
        SandboxVerifierOutput.model_validate(payload)

    payload = valid_output().model_dump()
    payload["outcome"] = decision_value

    with pytest.raises(ValidationError) as exc_info:
        SandboxVerifierOutput.model_validate(payload)

    assert any(error["loc"] == ("outcome",) for error in exc_info.value.errors())


def test_no_real_client_data_is_used():
    request = valid_request()
    output = valid_output()

    assert request.allowed_artifact_metadata[0].original_filename.startswith("synthetic-")
    assert output.artifact_bundle_id.startswith("synthetic-")
    assert "Synthetic" in output.findings[0].claim_summary
    assert "Synthetic" in output.safe_public_search_hint_candidates[0].hint_text


def test_contract_module_does_not_introduce_runtime_or_external_behaviors():
    source = inspect.getsource(sandbox_verifier_module).lower()
    parsed_source = ast.parse(inspect.getsource(sandbox_verifier_module))

    imported_roots: set[str] = set()
    for node in ast.walk(parsed_source):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0].lower() for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".")[0].lower())

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
    forbidden_runtime_terms = ["docker", "virtualmachine", "virtual machine"]

    assert imported_roots.isdisjoint(forbidden_imports)
    assert all(term not in source for term in forbidden_runtime_terms)
