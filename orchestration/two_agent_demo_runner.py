from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai.public_research_agent import PublicResearchScenario, run_public_research_mvp
from ai.sandbox_verifier_agent import (
    MockSandboxVerifierScenario,
    run_mock_sandbox_verifier,
)
from schemas.client_artifacts import (
    ClientArtifactSensitivity,
    NormalizedClientArtifactBundle,
)
from schemas.evidence_reconciliation import EvidenceReconciliationResult
from schemas.research_agent import ResearchAgentOutput
from schemas.sandbox_verifier import (
    SafePublicSearchHintCandidate,
    SandboxVerifierOutput,
    SandboxVerifierRequest,
)
from services.client_artifact_normalization_service import normalize_client_artifact_file
from services.evidence_reconciliation_service import reconcile_sandbox_and_public_evidence
from services.safe_hint_bridge_service import filter_safe_public_search_hints


@dataclass(frozen=True)
class TwoAgentDemoResult:
    """Validated stage outputs from the non-decisional two-agent demo."""

    normalized_artifact_bundle: NormalizedClientArtifactBundle
    sandbox_request: SandboxVerifierRequest
    sandbox_verifier_output: SandboxVerifierOutput
    approved_public_hints: list[SafePublicSearchHintCandidate]
    public_research_output: ResearchAgentOutput
    reconciliation_result: EvidenceReconciliationResult
    stage_status_summary: dict[str, str]
    human_review_required: bool


def _build_sandbox_request(
    artifact_bundle: NormalizedClientArtifactBundle,
    sensitivity: ClientArtifactSensitivity,
) -> SandboxVerifierRequest:
    return SandboxVerifierRequest(
        request_id=f"two-agent-demo-request-{artifact_bundle.bundle_id}",
        artifact_bundle_id=artifact_bundle.bundle_id,
        allowed_artifact_metadata=list(artifact_bundle.source_metadata),
        verifier_objective="Verify synthetic normalized artifact support for the demo.",
        sensitivity=sensitivity,
        safe_public_search_hint_policy_ref="safe-hint-bridge-v1",
    )


def run_two_agent_demo(
    artifact_path: Path | str,
    *,
    sandbox_scenario: MockSandboxVerifierScenario | str = (
        MockSandboxVerifierScenario.SAFE_HINT
    ),
    public_scenario: PublicResearchScenario | str = PublicResearchScenario.CLEAN,
    sensitivity: ClientArtifactSensitivity = ClientArtifactSensitivity.CONFIDENTIAL,
) -> TwoAgentDemoResult:
    """Run the local two-agent evidence workflow without deciding compliance."""
    artifact_bundle = normalize_client_artifact_file(
        artifact_path,
        sensitivity=sensitivity,
    )
    sandbox_request = _build_sandbox_request(artifact_bundle, sensitivity)
    sandbox_output = run_mock_sandbox_verifier(
        sandbox_request,
        artifact_bundle,
        scenario=sandbox_scenario,
    )

    approved_hints = filter_safe_public_search_hints(sandbox_output)
    public_output = run_public_research_mvp(
        approved_hints,
        scenario=public_scenario,
    )
    reconciliation_result = reconcile_sandbox_and_public_evidence(
        sandbox_output,
        public_output,
    )

    stage_status_summary = {
        "normalization": artifact_bundle.quality_status.value,
        "sandbox_verification": sandbox_output.verifier_status.value,
        "safe_hint_bridge": "complete",
        "public_research": (
            "review_required" if public_output.human_review_required else "complete"
        ),
        "evidence_reconciliation": reconciliation_result.status.value,
    }

    return TwoAgentDemoResult(
        normalized_artifact_bundle=artifact_bundle,
        sandbox_request=sandbox_request,
        sandbox_verifier_output=sandbox_output,
        approved_public_hints=approved_hints,
        public_research_output=public_output,
        reconciliation_result=reconciliation_result,
        stage_status_summary=stage_status_summary,
        human_review_required=reconciliation_result.human_review_required,
    )
