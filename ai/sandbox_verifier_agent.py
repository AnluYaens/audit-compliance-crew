from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from schemas.client_artifacts import (
    LOW_ARTIFACT_CONFIDENCE_THRESHOLD,
    ClientArtifactProvenanceReference,
    NormalizedClientArtifactBundle,
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


MOCK_SANDBOX_VERIFIER_DATETIME = datetime(2026, 7, 9, tzinfo=timezone.utc)


class MockSandboxVerifierScenario(str, Enum):
    CLEAN = "clean"
    MISSING_EVIDENCE = "missing_evidence"
    CONTRADICTION = "contradiction"
    LOW_CONFIDENCE = "low_confidence"
    TOOL_ERROR = "tool_error"
    INVALID_INPUT = "invalid_input"
    SAFE_HINT = "safe_hint"


def _first_provenance(
    artifact_bundle: NormalizedClientArtifactBundle,
) -> ClientArtifactProvenanceReference | None:
    for table in artifact_bundle.normalized_tables:
        if table.provenance is not None:
            return table.provenance
        for row in table.rows:
            if row.provenance is not None:
                return row.provenance
            for cell in row.cells:
                if cell.provenance is not None:
                    return cell.provenance

    for chunk in artifact_bundle.normalized_text_chunks:
        return chunk.provenance

    return None


def _metadata_matches_request(
    request: SandboxVerifierRequest,
    artifact_bundle: NormalizedClientArtifactBundle,
) -> bool:
    allowed_source_ids = {metadata.source_id for metadata in request.allowed_artifact_metadata}
    bundle_source_ids = {metadata.source_id for metadata in artifact_bundle.source_metadata}
    return bundle_source_ids.issubset(allowed_source_ids)


def _invalid_input_output(
    request: SandboxVerifierRequest,
    artifact_bundle: NormalizedClientArtifactBundle,
    reason: str,
) -> SandboxVerifierOutput:
    return SandboxVerifierOutput(
        request_id=request.request_id,
        artifact_bundle_id=artifact_bundle.bundle_id,
        verifier_status=SandboxVerifierStatus.INVALID_INPUT,
        findings=[
            LocalEvidenceFinding(
                finding_id="sandbox-finding-invalid-input-1",
                finding_type=SandboxFindingType.UNSUPPORTED_CLAIM,
                claim_summary="Synthetic verifier input requires auditor review.",
                provenance_references=[],
                confidence=0.80,
                sensitivity=request.sensitivity,
                human_review_recommended=True,
                review_reason_codes=[
                    SandboxReviewReasonCode.UNSUPPORTED_CLAIM,
                    SandboxReviewReasonCode.INVALID_INPUT,
                ],
            )
        ],
        review_reasons=[SandboxReviewReasonCode.INVALID_INPUT],
        tool_errors=[reason],
        generated_at=MOCK_SANDBOX_VERIFIER_DATETIME,
    )


def _review_required_output(
    request: SandboxVerifierRequest,
    artifact_bundle: NormalizedClientArtifactBundle,
    *,
    finding_id: str,
    finding_type: SandboxFindingType,
    claim_summary: str,
    review_reason: SandboxReviewReasonCode,
    confidence: float,
    missing_evidence_items: list[str] | None = None,
    contradictions: list[str] | None = None,
    tool_errors: list[str] | None = None,
) -> SandboxVerifierOutput:
    return SandboxVerifierOutput(
        request_id=request.request_id,
        artifact_bundle_id=artifact_bundle.bundle_id,
        verifier_status=SandboxVerifierStatus.REVIEW_REQUIRED,
        findings=[
            LocalEvidenceFinding(
                finding_id=finding_id,
                finding_type=finding_type,
                claim_summary=claim_summary,
                provenance_references=[
                    provenance
                    for provenance in [_first_provenance(artifact_bundle)]
                    if provenance is not None
                ],
                confidence=confidence,
                sensitivity=request.sensitivity,
                human_review_recommended=True,
                review_reason_codes=[review_reason],
            )
        ],
        missing_evidence_items=missing_evidence_items or [],
        contradictions=contradictions or [],
        tool_errors=tool_errors or [],
        review_reasons=[review_reason],
        generated_at=MOCK_SANDBOX_VERIFIER_DATETIME,
    )


def _bundle_quality_output(
    request: SandboxVerifierRequest,
    artifact_bundle: NormalizedClientArtifactBundle,
) -> SandboxVerifierOutput | None:
    provenance = _first_provenance(artifact_bundle)
    if provenance is None:
        return _review_required_output(
            request,
            artifact_bundle,
            finding_id="sandbox-finding-missing-evidence-1",
            finding_type=SandboxFindingType.MISSING_EVIDENCE,
            claim_summary="Synthetic normalized artifact support is missing.",
            review_reason=SandboxReviewReasonCode.MISSING_EVIDENCE,
            confidence=0.82,
            missing_evidence_items=["No normalized table, row, cell, or text provenance is present."],
        )

    if artifact_bundle.missing_required_fields:
        return _review_required_output(
            request,
            artifact_bundle,
            finding_id="sandbox-finding-missing-required-fields-1",
            finding_type=SandboxFindingType.MISSING_EVIDENCE,
            claim_summary="Synthetic normalized artifact bundle is missing required fields.",
            review_reason=SandboxReviewReasonCode.MISSING_EVIDENCE,
            confidence=0.84,
            missing_evidence_items=list(artifact_bundle.missing_required_fields),
        )

    if artifact_bundle.overall_confidence < LOW_ARTIFACT_CONFIDENCE_THRESHOLD:
        return _review_required_output(
            request,
            artifact_bundle,
            finding_id="sandbox-finding-bundle-low-confidence-1",
            finding_type=SandboxFindingType.LOW_CONFIDENCE,
            claim_summary="Synthetic normalized artifact bundle confidence is below threshold.",
            review_reason=SandboxReviewReasonCode.LOW_CONFIDENCE,
            confidence=artifact_bundle.overall_confidence,
        )

    if artifact_bundle.human_review_recommended:
        return _review_required_output(
            request,
            artifact_bundle,
            finding_id="sandbox-finding-bundle-review-recommended-1",
            finding_type=SandboxFindingType.ANOMALY,
            claim_summary="Synthetic normalized artifact bundle already recommends review.",
            review_reason=SandboxReviewReasonCode.ANOMALY,
            confidence=max(artifact_bundle.overall_confidence, LOW_ARTIFACT_CONFIDENCE_THRESHOLD),
        )

    return None


def _supported_finding(
    request: SandboxVerifierRequest,
    artifact_bundle: NormalizedClientArtifactBundle,
) -> LocalEvidenceFinding:
    provenance = _first_provenance(artifact_bundle)
    if provenance is None:
        raise ValueError("Clean mock verifier output requires normalized artifact provenance.")

    return LocalEvidenceFinding(
        finding_id="sandbox-finding-supported-1",
        finding_type=SandboxFindingType.SUPPORTED_CLAIM,
        claim_summary="Synthetic normalized artifact evidence supports the verifier objective.",
        provenance_references=[provenance],
        confidence=max(artifact_bundle.overall_confidence, 0.90),
        sensitivity=request.sensitivity,
    )


def _safe_hints() -> list[SafePublicSearchHintCandidate]:
    return [
        SafePublicSearchHintCandidate(
            hint_id="sandbox-hint-official-website-1",
            hint_text="Synthetic Public Company official website",
            hint_type=SafePublicSearchHintType.OFFICIAL_WEBSITE,
            safe_reason="Uses synthetic public-style terms only.",
            sensitivity=SafePublicSearchHintSensitivity.PUBLIC,
            confidence=0.90,
        ),
        SafePublicSearchHintCandidate(
            hint_id="sandbox-hint-annual-report-1",
            hint_text="Synthetic Public Company annual report",
            hint_type=SafePublicSearchHintType.ANNUAL_REPORT,
            safe_reason="Uses synthetic public-style terms only.",
            sensitivity=SafePublicSearchHintSensitivity.PUBLIC,
            confidence=0.88,
        ),
        SafePublicSearchHintCandidate(
            hint_id="sandbox-hint-sanctions-list-1",
            hint_text="Synthetic Public Company sanctions list",
            hint_type=SafePublicSearchHintType.SANCTIONS_LIST,
            safe_reason="Uses synthetic non-sensitive screening terms only.",
            sensitivity=SafePublicSearchHintSensitivity.NON_SENSITIVE,
            confidence=0.87,
        ),
        SafePublicSearchHintCandidate(
            hint_id="sandbox-hint-regulator-source-1",
            hint_text="Synthetic Public Company regulator source",
            hint_type=SafePublicSearchHintType.REGULATOR_SOURCE,
            safe_reason="Uses synthetic public-style terms only.",
            sensitivity=SafePublicSearchHintSensitivity.PUBLIC,
            confidence=0.86,
        ),
        SafePublicSearchHintCandidate(
            hint_id="sandbox-hint-reliable-news-1",
            hint_text="Synthetic Public Company reliable news target",
            hint_type=SafePublicSearchHintType.RELIABLE_NEWS,
            safe_reason="Uses synthetic public-style terms only.",
            sensitivity=SafePublicSearchHintSensitivity.PUBLIC,
            confidence=0.85,
        ),
    ]


def run_mock_sandbox_verifier(
    request: SandboxVerifierRequest,
    artifact_bundle: NormalizedClientArtifactBundle,
    scenario: MockSandboxVerifierScenario | str = MockSandboxVerifierScenario.CLEAN,
) -> SandboxVerifierOutput:
    scenario = MockSandboxVerifierScenario(scenario)

    if request.artifact_bundle_id is not None and request.artifact_bundle_id != artifact_bundle.bundle_id:
        return _invalid_input_output(
            request,
            artifact_bundle,
            "Synthetic request bundle identifier does not match the normalized artifact bundle.",
        )

    if not _metadata_matches_request(request, artifact_bundle):
        return _invalid_input_output(
            request,
            artifact_bundle,
            "Synthetic request metadata does not allow every normalized artifact source.",
        )

    if scenario == MockSandboxVerifierScenario.INVALID_INPUT:
        return _invalid_input_output(
            request,
            artifact_bundle,
            "Synthetic invalid input scenario requires auditor review.",
        )

    if scenario == MockSandboxVerifierScenario.TOOL_ERROR:
        return SandboxVerifierOutput(
            request_id=request.request_id,
            artifact_bundle_id=artifact_bundle.bundle_id,
            verifier_status=SandboxVerifierStatus.TOOL_ERROR,
            findings=[],
            tool_errors=["Synthetic verifier tool error before local evidence checks completed."],
            review_reasons=[SandboxReviewReasonCode.TOOL_ERROR],
            generated_at=MOCK_SANDBOX_VERIFIER_DATETIME,
        )

    quality_output = _bundle_quality_output(request, artifact_bundle)
    if quality_output is not None:
        return quality_output

    if scenario == MockSandboxVerifierScenario.MISSING_EVIDENCE:
        return _review_required_output(
            request,
            artifact_bundle,
            finding_id="sandbox-finding-missing-evidence-1",
            finding_type=SandboxFindingType.MISSING_EVIDENCE,
            claim_summary="Synthetic verifier scenario found missing local evidence.",
            review_reason=SandboxReviewReasonCode.MISSING_EVIDENCE,
            confidence=0.82,
            missing_evidence_items=["Synthetic support item is absent from normalized artifacts."],
        )

    if scenario == MockSandboxVerifierScenario.CONTRADICTION:
        contradiction = "Synthetic normalized artifact values conflict for the verifier objective."
        return _review_required_output(
            request,
            artifact_bundle,
            finding_id="sandbox-finding-contradiction-1",
            finding_type=SandboxFindingType.CONTRADICTION,
            claim_summary="Synthetic verifier scenario found contradictory local evidence.",
            review_reason=SandboxReviewReasonCode.CONTRADICTION,
            confidence=0.86,
            contradictions=[contradiction],
        )

    if scenario == MockSandboxVerifierScenario.LOW_CONFIDENCE:
        return _review_required_output(
            request,
            artifact_bundle,
            finding_id="sandbox-finding-low-confidence-1",
            finding_type=SandboxFindingType.LOW_CONFIDENCE,
            claim_summary="Synthetic verifier scenario produced low-confidence support.",
            review_reason=SandboxReviewReasonCode.LOW_CONFIDENCE,
            confidence=0.42,
        )

    return SandboxVerifierOutput(
        request_id=request.request_id,
        artifact_bundle_id=artifact_bundle.bundle_id,
        verifier_status=SandboxVerifierStatus.SUCCESS,
        findings=[_supported_finding(request, artifact_bundle)],
        safe_public_search_hint_candidates=(
            _safe_hints() if scenario == MockSandboxVerifierScenario.SAFE_HINT else []
        ),
        generated_at=MOCK_SANDBOX_VERIFIER_DATETIME,
    )


class MockSandboxVerifier:
    """Deterministic local verifier facade for schema and guardrail tests."""

    def run(
        self,
        request: SandboxVerifierRequest,
        artifact_bundle: NormalizedClientArtifactBundle,
        scenario: MockSandboxVerifierScenario | str = MockSandboxVerifierScenario.CLEAN,
    ) -> SandboxVerifierOutput:
        return run_mock_sandbox_verifier(request, artifact_bundle, scenario)
