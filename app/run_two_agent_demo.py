from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence

from ai.public_research_agent import PublicResearchScenario
from ai.sandbox_verifier_agent import MockSandboxVerifierScenario
from orchestration.two_agent_demo_runner import TwoAgentDemoResult, run_two_agent_demo


SCENARIOS = {
    "clean": (
        MockSandboxVerifierScenario.SAFE_HINT,
        PublicResearchScenario.CLEAN,
    ),
    "review": (
        MockSandboxVerifierScenario.CONTRADICTION,
        PublicResearchScenario.CLEAN,
    ),
    "sandbox-contradiction": (
        MockSandboxVerifierScenario.CONTRADICTION,
        PublicResearchScenario.CLEAN,
    ),
    "sandbox-missing-evidence": (
        MockSandboxVerifierScenario.MISSING_EVIDENCE,
        PublicResearchScenario.CLEAN,
    ),
    "public-weak": (
        MockSandboxVerifierScenario.SAFE_HINT,
        PublicResearchScenario.WEAK_SOURCE,
    ),
    "public-stale": (
        MockSandboxVerifierScenario.SAFE_HINT,
        PublicResearchScenario.STALE_SOURCE,
    ),
    "public-error": (
        MockSandboxVerifierScenario.SAFE_HINT,
        PublicResearchScenario.SOURCE_ERROR,
    ),
}

SYNTHETIC_ARTIFACT_CONTENT = (
    "record_id,reporting_period,support_status\n"
    "SYNTHETIC-CONFIDENTIAL-RECORD-1801,2026-Q2,documented\n"
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local synthetic two-agent evidence demo.",
    )
    parser.add_argument(
        "artifact_path",
        nargs="?",
        type=Path,
        help="Optional local synthetic CSV or JSON artifact.",
    )
    parser.add_argument(
        "--scenario",
        choices=tuple(SCENARIOS),
        default="clean",
        help="Schema-valid synthetic demo scenario (default: clean).",
    )
    return parser.parse_args(argv)


def _print_summary(result: TwoAgentDemoResult, scenario: str) -> None:
    bundle = result.normalized_artifact_bundle
    sandbox = result.sandbox_verifier_output
    public = result.public_research_output
    reconciliation = result.reconciliation_result

    print("Two-Agent Evidence Demo")
    print(f"Scenario: {scenario}")
    print(
        "Normalization: "
        f"{result.stage_status_summary['normalization']} "
        f"(tables={len(bundle.normalized_tables)})"
    )
    print(
        "Sandbox verification: "
        f"{result.stage_status_summary['sandbox_verification']} "
        f"(findings={len(sandbox.findings)})"
    )
    bridge_status = result.stage_status_summary["safe_hint_bridge"]
    if bridge_status == "complete" and not result.approved_public_hints:
        bridge_status = "no_approved_hints"

    print(
        "Safe Hint Bridge: "
        f"{bridge_status} "
        f"(approved_hints={len(result.approved_public_hints)})"
    )
    print(
        "Public research: "
        f"{result.stage_status_summary['public_research']} "
        f"(sources={len(public.candidate_sources)}, "
        f"evidence_items={len(public.extracted_evidence)})"
    )
    print(
        "Evidence reconciliation: "
        f"{result.stage_status_summary['evidence_reconciliation']} "
        f"(issues={len(reconciliation.issues)})"
    )
    review_label = "yes" if result.human_review_required else "no"
    print(f"Human review required: {review_label}")


def _run_with_path(artifact_path: Path, scenario: str) -> TwoAgentDemoResult:
    sandbox_scenario, public_scenario = SCENARIOS[scenario]
    return run_two_agent_demo(
        artifact_path,
        sandbox_scenario=sandbox_scenario,
        public_scenario=public_scenario,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)

    if args.artifact_path is not None:
        result = _run_with_path(args.artifact_path, args.scenario)
        _print_summary(result, args.scenario)
        return

    with TemporaryDirectory(prefix="audit-compliance-demo-") as temp_dir:
        artifact_path = Path(temp_dir) / "synthetic-two-agent-input.csv"
        artifact_path.write_text(SYNTHETIC_ARTIFACT_CONTENT, encoding="utf-8")
        result = _run_with_path(artifact_path, args.scenario)
        _print_summary(result, args.scenario)


if __name__ == "__main__":
    main()
