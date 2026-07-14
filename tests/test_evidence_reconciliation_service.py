import ast
from datetime import datetime, timedelta, timezone
import inspect

import pytest
from pydantic import ValidationError

import services.evidence_reconciliation_service as reconciliation_module
from schemas.client_artifacts import (
    ClientArtifactProvenanceReference,
    ClientArtifactSensitivity,
)
from schemas.evidence_reconciliation import (
    EvidenceReconciliationIssueType,
    EvidenceReconciliationResult,
    EvidenceReconciliationSourceLane,
    EvidenceReconciliationStatus,
)
from schemas.research_agent import (
    CandidateSource,
    CitationType,
    EvidenceStatus,
    ExtractedEvidence,
    ResearchAgentOutput,
    ResearchCitation,
    ResearchTaskType,
)
from schemas.sandbox_verifier import (
    LocalEvidenceFinding,
    SandboxFindingType,
    SandboxReviewReasonCode,
    SandboxVerifierOutput,
    SandboxVerifierStatus,
)
from schemas.source_registry import SourceType
from services.evidence_reconciliation_service import (
    MAX_PUBLIC_SOURCE_AGE_DAYS,
    reconcile_sandbox_and_public_evidence,
)


GENERATED_AT = datetime(2026, 7, 14, tzinfo=timezone.utc)
CONFIDENTIAL_SYNTHETIC_VALUE = "SYNTHETIC-CONFIDENTIAL-VALUE-9173"
FINAL_OUTCOMES = {"CONTINUE", "MANUAL_REVIEW", "REJECT"}


def provenance() -> ClientArtifactProvenanceReference:
    return ClientArtifactProvenanceReference(
        source_id="synthetic-internal-source-1",
        file_name="synthetic-confidential-artifact.csv",
        row_number=4,
        column_name="synthetic_support",
    )


def sandbox_finding(
    *,
    finding_type: SandboxFindingType = SandboxFindingType.SUPPORTED_CLAIM,
    claim_summary: str = "Synthetic internal evidence supports the test assertion.",
    confidence: float = 0.94,
    human_review_recommended: bool = False,
    review_reason_codes: list[SandboxReviewReasonCode] | None = None,
) -> LocalEvidenceFinding:
    return LocalEvidenceFinding(
        finding_id=f"synthetic-{finding_type.value}-1",
        finding_type=finding_type,
        claim_summary=claim_summary,
        provenance_references=[provenance()],
        confidence=confidence,
        sensitivity=ClientArtifactSensitivity.CONFIDENTIAL,
        human_review_recommended=human_review_recommended,
        review_reason_codes=review_reason_codes or [],
    )


def sandbox_output(
    *,
    status: SandboxVerifierStatus = SandboxVerifierStatus.SUCCESS,
    findings: list[LocalEvidenceFinding] | None = None,
    missing_evidence_items: list[str] | None = None,
    contradictions: list[str] | None = None,
    tool_errors: list[str] | None = None,
    review_reasons: list[SandboxReviewReasonCode] | None = None,
) -> SandboxVerifierOutput:
    return SandboxVerifierOutput(
        request_id="synthetic-sandbox-request-17-1",
        artifact_bundle_id="synthetic-artifact-bundle-17-1",
        verifier_status=status,
        findings=[sandbox_finding()] if findings is None else findings,
        missing_evidence_items=missing_evidence_items or [],
        contradictions=contradictions or [],
        tool_errors=tool_errors or [],
        review_reasons=review_reasons or [],
        generated_at=GENERATED_AT,
    )


def citation(source_id: str = "synthetic-public-source-1") -> ResearchCitation:
    return ResearchCitation(
        source_id=source_id,
        citation_type=CitationType.URL,
        locator="https://public.example.invalid/filing#synthetic-evidence",
        excerpt="Synthetic public filing support.",
        retrieved_at=GENERATED_AT,
    )


def candidate_source(
    *,
    confidence: float = 0.95,
    retrieval_date: datetime | None = GENERATED_AT,
    contradictions: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    citations: list[ResearchCitation] | None = None,
) -> CandidateSource:
    return CandidateSource(
        source_id="synthetic-public-source-1",
        title="Synthetic public audited filing",
        source_type=SourceType.AUDITED_FINANCIAL_STATEMENT,
        url="https://public.example.invalid/filing",
        publisher="Synthetic Public Publisher",
        retrieval_date=retrieval_date,
        confidence=confidence,
        relevance=0.93,
        missing_evidence=missing_evidence or [],
        contradictions=contradictions or [],
        citations=[citation()] if citations is None else citations,
    )


def public_evidence(
    *,
    confidence: float = 0.93,
    status: EvidenceStatus = EvidenceStatus.PRESENT,
    missing_evidence: list[str] | None = None,
    contradictions: list[str] | None = None,
    citations: list[ResearchCitation] | None = None,
) -> ExtractedEvidence:
    return ExtractedEvidence(
        evidence_id="synthetic-public-evidence-1",
        source_id="synthetic-public-source-1",
        claim="Synthetic public evidence supports the test assertion.",
        extracted_value="synthetic-public-value",
        status=status,
        confidence=confidence,
        citations=[citation()] if citations is None else citations,
        missing_evidence=missing_evidence or [],
        contradictions=contradictions or [],
    )


def public_output(
    *,
    candidate_sources: list[CandidateSource] | None = None,
    extracted_evidence: list[ExtractedEvidence] | None = None,
    missing_evidence: list[str] | None = None,
    contradictions: list[str] | None = None,
    tool_errors: list[str] | None = None,
) -> ResearchAgentOutput:
    return ResearchAgentOutput(
        task_type=ResearchTaskType.SOURCE_AND_EVIDENCE_RESEARCH,
        run_id="synthetic-public-run-17-1",
        target_company="Synthetic Public Entity",
        research_question="Find synthetic public support for reconciliation testing.",
        generated_at=GENERATED_AT,
        candidate_sources=(
            [candidate_source()] if candidate_sources is None else candidate_sources
        ),
        extracted_evidence=(
            [public_evidence()] if extracted_evidence is None else extracted_evidence
        ),
        missing_evidence=missing_evidence or [],
        contradictions=contradictions or [],
        tool_errors=tool_errors or [],
    )


def issue_types(result: EvidenceReconciliationResult) -> set[EvidenceReconciliationIssueType]:
    return {issue.issue_type for issue in result.issues}


def test_clean_sandbox_and_public_evidence_are_aligned():
    result = reconcile_sandbox_and_public_evidence(sandbox_output(), public_output())

    assert result.status is EvidenceReconciliationStatus.ALIGNED
    assert result.human_review_required is False
    assert result.issues == []
    assert len(result.aligned_evidence_summaries) == 2
    assert result.sandbox_request_id == "synthetic-sandbox-request-17-1"
    assert result.artifact_bundle_id == "synthetic-artifact-bundle-17-1"
    assert result.public_research_run_id == "synthetic-public-run-17-1"
    assert EvidenceReconciliationResult.model_validate(
        result.model_dump(exclude_computed_fields=True)
    ) == result


def test_sandbox_review_required_output_requires_reconciliation_review():
    sandbox = sandbox_output(
        status=SandboxVerifierStatus.REVIEW_REQUIRED,
        review_reasons=[SandboxReviewReasonCode.HUMAN_REVIEW_RECOMMENDED],
    )

    result = reconcile_sandbox_and_public_evidence(sandbox, public_output())

    assert result.status is EvidenceReconciliationStatus.REVIEW_REQUIRED
    assert result.human_review_required is True
    assert any(
        issue.source_lane is EvidenceReconciliationSourceLane.SANDBOX
        for issue in result.issues
    )


def test_public_review_required_output_requires_reconciliation_review():
    public = public_output(
        candidate_sources=[candidate_source(confidence=0.42)],
        extracted_evidence=[
            public_evidence(confidence=0.44, status=EvidenceStatus.LOW_CONFIDENCE)
        ],
    )
    assert public.human_review_required is True

    result = reconcile_sandbox_and_public_evidence(sandbox_output(), public)

    assert result.status is EvidenceReconciliationStatus.WEAK_PUBLIC_EVIDENCE
    assert result.human_review_required is True


def test_missing_internal_evidence_is_detected():
    result = reconcile_sandbox_and_public_evidence(
        sandbox_output(findings=[]),
        public_output(),
    )

    assert result.status is EvidenceReconciliationStatus.MISSING_INTERNAL_EVIDENCE
    assert EvidenceReconciliationIssueType.MISSING_INTERNAL_EVIDENCE in issue_types(result)
    assert result.missing_evidence_summaries


def test_missing_public_evidence_is_detected():
    result = reconcile_sandbox_and_public_evidence(
        sandbox_output(),
        public_output(
            candidate_sources=[],
            extracted_evidence=[],
            missing_evidence=["Synthetic public support was not found."],
        ),
    )

    assert result.status is EvidenceReconciliationStatus.MISSING_PUBLIC_EVIDENCE
    assert EvidenceReconciliationIssueType.MISSING_PUBLIC_EVIDENCE in issue_types(result)
    assert result.missing_evidence_summaries


def test_weak_public_evidence_is_detected():
    result = reconcile_sandbox_and_public_evidence(
        sandbox_output(),
        public_output(
            candidate_sources=[candidate_source(confidence=0.60)],
            extracted_evidence=[public_evidence(confidence=0.62)],
        ),
    )

    assert result.status is EvidenceReconciliationStatus.WEAK_PUBLIC_EVIDENCE
    assert EvidenceReconciliationIssueType.LOW_CONFIDENCE in issue_types(result)
    assert result.human_review_required is True


def test_stale_public_evidence_is_detected():
    stale_date = GENERATED_AT - timedelta(days=MAX_PUBLIC_SOURCE_AGE_DAYS + 1)
    result = reconcile_sandbox_and_public_evidence(
        sandbox_output(),
        public_output(candidate_sources=[candidate_source(retrieval_date=stale_date)]),
    )

    assert result.status is EvidenceReconciliationStatus.STALE_PUBLIC_EVIDENCE
    assert EvidenceReconciliationIssueType.STALE_SOURCE in issue_types(result)
    assert result.human_review_required is True


@pytest.mark.parametrize("lane", ["sandbox", "public"])
def test_contradictory_evidence_is_detected_from_either_lane(lane: str):
    sandbox = sandbox_output()
    public = public_output()
    if lane == "sandbox":
        sandbox = sandbox_output(
            findings=[
                sandbox_finding(
                    finding_type=SandboxFindingType.CONTRADICTION,
                    human_review_recommended=True,
                    review_reason_codes=[SandboxReviewReasonCode.CONTRADICTION],
                )
            ]
        )
    else:
        public = public_output(
            extracted_evidence=[
                public_evidence(
                    status=EvidenceStatus.CONTRADICTED,
                    contradictions=["Synthetic public values conflict."],
                )
            ]
        )

    result = reconcile_sandbox_and_public_evidence(sandbox, public)

    assert result.status is EvidenceReconciliationStatus.CONTRADICTORY_EVIDENCE
    assert EvidenceReconciliationIssueType.CONTRADICTION in issue_types(result)
    assert result.contradiction_summaries


@pytest.mark.parametrize("lane", ["sandbox", "public"])
def test_source_errors_are_detected_from_either_lane(lane: str):
    sandbox = sandbox_output()
    public = public_output()
    if lane == "sandbox":
        sandbox = sandbox_output(
            status=SandboxVerifierStatus.TOOL_ERROR,
            tool_errors=["Synthetic sandbox tool error."],
            review_reasons=[SandboxReviewReasonCode.TOOL_ERROR],
        )
    else:
        public = public_output(tool_errors=["Synthetic public tool error."])

    result = reconcile_sandbox_and_public_evidence(sandbox, public)

    assert result.status is EvidenceReconciliationStatus.SOURCE_ERROR
    assert EvidenceReconciliationIssueType.TOOL_ERROR in issue_types(result)
    assert result.source_error_summaries


def test_invalid_input_objects_raise_clear_type_or_validation_errors():
    with pytest.raises(TypeError, match="SandboxVerifierOutput"):
        reconcile_sandbox_and_public_evidence(object(), public_output())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ResearchAgentOutput"):
        reconcile_sandbox_and_public_evidence(sandbox_output(), object())  # type: ignore[arg-type]

    invalid_sandbox = sandbox_output().model_copy(update={"verifier_status": "not-valid"})
    with pytest.warns(UserWarning, match="Pydantic serializer warnings"):
        with pytest.raises(ValidationError):
            reconcile_sandbox_and_public_evidence(invalid_sandbox, public_output())


def test_invalid_sandbox_status_fails_closed_to_invalid_input_result():
    result = reconcile_sandbox_and_public_evidence(
        sandbox_output(
            status=SandboxVerifierStatus.INVALID_INPUT,
            review_reasons=[SandboxReviewReasonCode.INVALID_INPUT],
        ),
        public_output(),
    )

    assert result.status is EvidenceReconciliationStatus.INVALID_INPUT
    assert result.human_review_required is True


def test_output_contains_no_decision_fields_or_final_outcomes():
    result = reconcile_sandbox_and_public_evidence(sandbox_output(), public_output())
    payload = result.model_dump(mode="json")
    payload_text = repr(payload)

    assert "final_decision" not in EvidenceReconciliationResult.model_fields
    assert "decision" not in EvidenceReconciliationResult.model_fields
    assert all(outcome not in payload_text for outcome in FINAL_OUTCOMES)

    for field_name in ("final_decision", "decision"):
        invalid_payload = result.model_dump(exclude_computed_fields=True)
        invalid_payload[field_name] = "CONTINUE"
        with pytest.raises(ValidationError):
            EvidenceReconciliationResult.model_validate(invalid_payload)


def test_confidential_local_values_are_not_copied_to_any_summary():
    confidential_finding = sandbox_finding(
        finding_type=SandboxFindingType.CONTRADICTION,
        claim_summary=CONFIDENTIAL_SYNTHETIC_VALUE,
        human_review_recommended=True,
        review_reason_codes=[SandboxReviewReasonCode.CONTRADICTION],
    )
    sandbox = sandbox_output(
        status=SandboxVerifierStatus.TOOL_ERROR,
        findings=[confidential_finding],
        missing_evidence_items=[CONFIDENTIAL_SYNTHETIC_VALUE],
        contradictions=[CONFIDENTIAL_SYNTHETIC_VALUE],
        tool_errors=[CONFIDENTIAL_SYNTHETIC_VALUE],
        review_reasons=[
            SandboxReviewReasonCode.CONTRADICTION,
            SandboxReviewReasonCode.TOOL_ERROR,
        ],
    )

    result = reconcile_sandbox_and_public_evidence(sandbox, public_output())
    summaries = [issue.summary for issue in result.issues]
    summaries.extend(result.aligned_evidence_summaries)
    summaries.extend(result.missing_evidence_summaries)
    summaries.extend(result.contradiction_summaries)
    summaries.extend(result.source_error_summaries)

    assert CONFIDENTIAL_SYNTHETIC_VALUE not in repr(summaries)


def test_service_introduces_no_external_or_parsing_runtime_behavior():
    parsed_source = ast.parse(inspect.getsource(reconciliation_module))
    imported_roots: set[str] = set()
    called_names: set[str] = set()

    for node in ast.walk(parsed_source):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id.casefold())
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr.casefold())

    forbidden_imports = {
        "requests",
        "urllib",
        "http",
        "subprocess",
        "openai",
        "crewai",
        "azure",
        "docker",
        "pypdf",
        "pdfplumber",
        "openpyxl",
        "pandas",
        "pytesseract",
    }
    forbidden_calls = {
        "open",
        "run",
        "popen",
        "urlopen",
        "request",
        "get",
        "post",
        "ocr",
    }

    assert imported_roots.isdisjoint(forbidden_imports)
    assert called_names.isdisjoint(forbidden_calls)
