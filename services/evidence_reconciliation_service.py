from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from schemas.evidence_reconciliation import (
    EvidenceReconciliationIssue,
    EvidenceReconciliationIssueType,
    EvidenceReconciliationReasonCode,
    EvidenceReconciliationResult,
    EvidenceReconciliationSourceLane,
    EvidenceReconciliationStatus,
)
from schemas.research_agent import (
    CitationType,
    EvidenceStatus,
    ResearchAgentOutput,
)
from schemas.sandbox_verifier import (
    SandboxFindingType,
    SandboxReviewReasonCode,
    SandboxVerifierOutput,
    SandboxVerifierStatus,
)
from schemas.source_registry import SourceType


MIN_RECONCILIATION_CONFIDENCE = 0.75
MAX_PUBLIC_SOURCE_AGE_DAYS = 365


def _validated_inputs(
    sandbox_output: SandboxVerifierOutput,
    public_output: ResearchAgentOutput,
) -> tuple[SandboxVerifierOutput, ResearchAgentOutput]:
    if not isinstance(sandbox_output, SandboxVerifierOutput):
        raise TypeError("sandbox_output must be a SandboxVerifierOutput.")
    if not isinstance(public_output, ResearchAgentOutput):
        raise TypeError("public_output must be a ResearchAgentOutput.")

    sandbox = SandboxVerifierOutput.model_validate(
        sandbox_output.model_dump(exclude_computed_fields=True)
    )
    public = ResearchAgentOutput.model_validate(
        public_output.model_dump(exclude_computed_fields=True)
    )
    return sandbox, public


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _public_source_age_days(retrieved_at: datetime, generated_at: datetime) -> int:
    return (_utc_datetime(generated_at).date() - _utc_datetime(retrieved_at).date()).days


def _reconciliation_id(sandbox: SandboxVerifierOutput, public: ResearchAgentOutput) -> str:
    trace_key = "|".join((sandbox.request_id, sandbox.artifact_bundle_id, public.run_id))
    return f"evidence-reconciliation-{sha256(trace_key.encode()).hexdigest()[:16]}"


def _issue(
    issues: list[EvidenceReconciliationIssue],
    *,
    issue_type: EvidenceReconciliationIssueType,
    summary: str,
    source_lane: EvidenceReconciliationSourceLane,
    confidence: float,
    reason_code: EvidenceReconciliationReasonCode,
) -> None:
    issues.append(
        EvidenceReconciliationIssue(
            issue_id=f"reconciliation-issue-{len(issues) + 1:03d}",
            issue_type=issue_type,
            summary=summary,
            source_lane=source_lane,
            confidence=confidence,
            human_review_required=True,
            reason_code=reason_code,
        )
    )


def reconcile_sandbox_and_public_evidence(
    sandbox_output: SandboxVerifierOutput,
    public_output: ResearchAgentOutput,
) -> EvidenceReconciliationResult:
    """Reconcile validated internal and public evidence without deciding compliance."""
    sandbox, public = _validated_inputs(sandbox_output, public_output)
    issues: list[EvidenceReconciliationIssue] = []
    missing_summaries: list[str] = []
    contradiction_summaries: list[str] = []
    source_error_summaries: list[str] = []

    invalid_sandbox = (
        sandbox.verifier_status is SandboxVerifierStatus.INVALID_INPUT
        or SandboxReviewReasonCode.INVALID_INPUT in sandbox.review_reasons
    )
    if invalid_sandbox:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.INVALID_INPUT,
            summary="The sandbox lane reported invalid structured input.",
            source_lane=EvidenceReconciliationSourceLane.SANDBOX,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.INVALID_SANDBOX_INPUT,
        )

    sandbox_error_count = len(sandbox.tool_errors)
    if (
        sandbox.verifier_status is SandboxVerifierStatus.TOOL_ERROR
        or SandboxReviewReasonCode.TOOL_ERROR in sandbox.review_reasons
    ) and not sandbox_error_count:
        sandbox_error_count = 1
    if sandbox_error_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.TOOL_ERROR,
            summary=f"The sandbox lane reported {sandbox_error_count} tool error signal(s).",
            source_lane=EvidenceReconciliationSourceLane.SANDBOX,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.SANDBOX_TOOL_ERROR,
        )
        source_error_summaries.append(
            f"Sandbox evidence processing reported {sandbox_error_count} error signal(s)."
        )

    public_error_count = len(public.tool_errors)
    if public_error_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.TOOL_ERROR,
            summary=f"The public lane reported {public_error_count} tool error signal(s).",
            source_lane=EvidenceReconciliationSourceLane.PUBLIC,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.PUBLIC_TOOL_ERROR,
        )
        source_error_summaries.append(
            f"Public evidence processing reported {public_error_count} error signal(s)."
        )

    sandbox_missing_count = len(sandbox.missing_evidence_items) + sum(
        finding.finding_type
        in {SandboxFindingType.MISSING_EVIDENCE, SandboxFindingType.UNSUPPORTED_CLAIM}
        for finding in sandbox.findings
    )
    if not sandbox.findings:
        sandbox_missing_count += 1
    if sandbox_missing_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.MISSING_INTERNAL_EVIDENCE,
            summary="Required internal evidence is absent or unsupported.",
            source_lane=EvidenceReconciliationSourceLane.INTERNAL,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.MISSING_INTERNAL_EVIDENCE,
        )
        missing_summaries.append(
            f"Internal evidence has {sandbox_missing_count} missing or unsupported signal(s)."
        )

    public_missing_count = len(public.missing_evidence)
    public_missing_count += sum(
        source.retrieval_date is None for source in public.candidate_sources
    )
    public_missing_count += sum(len(source.missing_evidence) for source in public.candidate_sources)
    public_missing_count += sum(
        len(evidence.missing_evidence) + (evidence.status is EvidenceStatus.MISSING)
        for evidence in public.extracted_evidence
    )
    if not public.candidate_sources:
        public_missing_count += 1
    if not public.extracted_evidence:
        public_missing_count += 1
    if public_missing_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.MISSING_PUBLIC_EVIDENCE,
            summary="Required public evidence or candidate sources are absent.",
            source_lane=EvidenceReconciliationSourceLane.PUBLIC,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.MISSING_PUBLIC_EVIDENCE,
        )
        missing_summaries.append(
            f"Public evidence has {public_missing_count} missing source or support signal(s)."
        )

    sandbox_contradiction_count = len(sandbox.contradictions) + sum(
        finding.finding_type is SandboxFindingType.CONTRADICTION
        for finding in sandbox.findings
    )
    if sandbox_contradiction_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.CONTRADICTION,
            summary="The sandbox lane reported contradictory internal evidence.",
            source_lane=EvidenceReconciliationSourceLane.SANDBOX,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.CONTRADICTORY_EVIDENCE,
        )
        contradiction_summaries.append(
            f"Sandbox evidence contains {sandbox_contradiction_count} contradiction signal(s)."
        )

    public_contradiction_count = len(public.contradictions)
    public_contradiction_count += sum(
        len(source.contradictions) for source in public.candidate_sources
    )
    public_contradiction_count += sum(
        len(evidence.contradictions) + (evidence.status is EvidenceStatus.CONTRADICTED)
        for evidence in public.extracted_evidence
    )
    if public_contradiction_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.CONTRADICTION,
            summary="The public lane reported contradictory public evidence.",
            source_lane=EvidenceReconciliationSourceLane.PUBLIC,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.CONTRADICTORY_EVIDENCE,
        )
        contradiction_summaries.append(
            f"Public evidence contains {public_contradiction_count} contradiction signal(s)."
        )

    stale_source_count = 0
    future_source_count = 0
    for source in public.candidate_sources:
        if source.retrieval_date is None:
            continue
        age_days = _public_source_age_days(source.retrieval_date, public.generated_at)
        if age_days < 0:
            future_source_count += 1
        elif age_days > MAX_PUBLIC_SOURCE_AGE_DAYS:
            stale_source_count += 1

    if future_source_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.INVALID_INPUT,
            summary="Public source metadata contains a future retrieval date.",
            source_lane=EvidenceReconciliationSourceLane.PUBLIC,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.INVALID_PUBLIC_INPUT,
        )
    if stale_source_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.STALE_SOURCE,
            summary=f"The public lane contains {stale_source_count} stale source(s).",
            source_lane=EvidenceReconciliationSourceLane.PUBLIC,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.STALE_PUBLIC_SOURCE,
        )

    public_confidences = [source.confidence for source in public.candidate_sources]
    public_confidences.extend(evidence.confidence for evidence in public.extracted_evidence)
    weak_public_count = sum(
        confidence < MIN_RECONCILIATION_CONFIDENCE for confidence in public_confidences
    )
    weak_public_count += sum(
        evidence.status is EvidenceStatus.LOW_CONFIDENCE
        for evidence in public.extracted_evidence
    )
    weak_public_count += sum(not source.citations for source in public.candidate_sources)
    weak_public_count += sum(not evidence.citations for evidence in public.extracted_evidence)
    if weak_public_count:
        issue_confidence = min(public_confidences, default=0.0)
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.LOW_CONFIDENCE,
            summary="Public evidence confidence or citation support is below the required threshold.",
            source_lane=EvidenceReconciliationSourceLane.PUBLIC,
            confidence=issue_confidence,
            reason_code=EvidenceReconciliationReasonCode.LOW_PUBLIC_CONFIDENCE,
        )

    unsafe_public_count = sum(
        source.source_type is SourceType.INTERNAL_SYSTEM for source in public.candidate_sources
    )
    unsafe_public_count += sum(
        citation.citation_type is CitationType.INTERNAL_RECORD
        for source in public.candidate_sources
        for citation in source.citations
    )
    unsafe_public_count += sum(
        citation.citation_type is CitationType.INTERNAL_RECORD
        for evidence in public.extracted_evidence
        for citation in evidence.citations
    )
    if unsafe_public_count:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.UNSAFE_PUBLIC_HINT,
            summary="The public lane contains internal-source classifications that are not public-safe.",
            source_lane=EvidenceReconciliationSourceLane.RECONCILIATION,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.UNSAFE_PUBLIC_HINT,
        )

    sandbox_issue_types = {
        issue.issue_type
        for issue in issues
        if issue.source_lane
        in {EvidenceReconciliationSourceLane.SANDBOX, EvidenceReconciliationSourceLane.INTERNAL}
    }
    if sandbox.human_review_required and not sandbox_issue_types.intersection(
        {
            EvidenceReconciliationIssueType.INVALID_INPUT,
            EvidenceReconciliationIssueType.TOOL_ERROR,
            EvidenceReconciliationIssueType.MISSING_INTERNAL_EVIDENCE,
            EvidenceReconciliationIssueType.CONTRADICTION,
            EvidenceReconciliationIssueType.LOW_CONFIDENCE,
        }
    ):
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.REVIEW_REQUIRED,
            summary="The sandbox lane requires human review.",
            source_lane=EvidenceReconciliationSourceLane.SANDBOX,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.SANDBOX_REVIEW_REQUIRED,
        )

    public_issue_types = {
        issue.issue_type
        for issue in issues
        if issue.source_lane
        in {EvidenceReconciliationSourceLane.PUBLIC, EvidenceReconciliationSourceLane.RECONCILIATION}
    }
    if public.human_review_required and not public_issue_types:
        _issue(
            issues,
            issue_type=EvidenceReconciliationIssueType.REVIEW_REQUIRED,
            summary="The public lane requires human review.",
            source_lane=EvidenceReconciliationSourceLane.PUBLIC,
            confidence=1.0,
            reason_code=EvidenceReconciliationReasonCode.PUBLIC_REVIEW_REQUIRED,
        )

    issue_types = {issue.issue_type for issue in issues}
    if EvidenceReconciliationIssueType.INVALID_INPUT in issue_types:
        status = EvidenceReconciliationStatus.INVALID_INPUT
    elif EvidenceReconciliationIssueType.TOOL_ERROR in issue_types:
        status = EvidenceReconciliationStatus.SOURCE_ERROR
    elif EvidenceReconciliationIssueType.CONTRADICTION in issue_types:
        status = EvidenceReconciliationStatus.CONTRADICTORY_EVIDENCE
    elif EvidenceReconciliationIssueType.UNSAFE_PUBLIC_HINT in issue_types:
        status = EvidenceReconciliationStatus.REVIEW_REQUIRED
    elif EvidenceReconciliationIssueType.STALE_SOURCE in issue_types:
        status = EvidenceReconciliationStatus.STALE_PUBLIC_EVIDENCE
    elif EvidenceReconciliationIssueType.MISSING_INTERNAL_EVIDENCE in issue_types:
        status = EvidenceReconciliationStatus.MISSING_INTERNAL_EVIDENCE
    elif EvidenceReconciliationIssueType.MISSING_PUBLIC_EVIDENCE in issue_types:
        status = EvidenceReconciliationStatus.MISSING_PUBLIC_EVIDENCE
    elif EvidenceReconciliationIssueType.LOW_CONFIDENCE in issue_types:
        status = EvidenceReconciliationStatus.WEAK_PUBLIC_EVIDENCE
    elif issues or sandbox.human_review_required or public.human_review_required:
        status = EvidenceReconciliationStatus.REVIEW_REQUIRED
    else:
        status = EvidenceReconciliationStatus.ALIGNED

    aligned_summaries: list[str] = []
    if status is EvidenceReconciliationStatus.ALIGNED:
        aligned_summaries = [
            f"Sandbox lane contains {len(sandbox.findings)} high-confidence supported finding(s).",
            (
                "Public lane contains "
                f"{len(public.extracted_evidence)} high-confidence cited evidence item(s) "
                f"from {len(public.candidate_sources)} candidate source(s)."
            ),
        ]

    return EvidenceReconciliationResult(
        reconciliation_id=_reconciliation_id(sandbox, public),
        sandbox_request_id=sandbox.request_id,
        artifact_bundle_id=sandbox.artifact_bundle_id,
        public_research_run_id=public.run_id,
        status=status,
        issues=issues,
        aligned_evidence_summaries=aligned_summaries,
        missing_evidence_summaries=missing_summaries,
        contradiction_summaries=contradiction_summaries,
        source_error_summaries=source_error_summaries,
    )
