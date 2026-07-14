from __future__ import annotations

import ast
from dataclasses import fields
import inspect
from pathlib import Path
import subprocess
import sys

import pytest

import app.run_two_agent_demo as cli_module
import orchestration.two_agent_demo_runner as demo_runner_module
from ai.public_research_agent import PublicResearchScenario
from ai.sandbox_verifier_agent import MockSandboxVerifierScenario
from app.run_two_agent_demo import main as cli_main
from orchestration.two_agent_demo_runner import TwoAgentDemoResult, run_two_agent_demo
from schemas.client_artifacts import (
    ClientArtifactQualityStatus,
    NormalizedClientArtifactBundle,
)
from schemas.evidence_reconciliation import EvidenceReconciliationStatus
from schemas.research_agent import ResearchAgentOutput
from schemas.sandbox_verifier import SandboxVerifierOutput, SandboxVerifierRequest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIDENTIAL_VALUES = {
    "SYNTHETIC-CONFIDENTIAL-ENTITY-1811",
    "SYNTHETIC-PRIVATE-AMOUNT-9181",
    "Synthetic Internal Owner 1811",
}
LOCAL_FILENAME = "synthetic-private-artifact-1811.csv"
FINAL_OUTCOMES = {"CONTINUE", "MANUAL_REVIEW", "REJECT"}


def synthetic_artifact(tmp_path: Path) -> Path:
    path = tmp_path / LOCAL_FILENAME
    path.write_text(
        "entity_ref,amount_ref,owner_ref\n"
        "SYNTHETIC-CONFIDENTIAL-ENTITY-1811,"
        "SYNTHETIC-PRIVATE-AMOUNT-9181,"
        "Synthetic Internal Owner 1811\n",
        encoding="utf-8",
    )
    return path


def reconciliation_summaries(result: TwoAgentDemoResult) -> list[str]:
    reconciliation = result.reconciliation_result
    summaries = [issue.summary for issue in reconciliation.issues]
    summaries.extend(reconciliation.aligned_evidence_summaries)
    summaries.extend(reconciliation.missing_evidence_summaries)
    summaries.extend(reconciliation.contradiction_summaries)
    summaries.extend(reconciliation.source_error_summaries)
    return summaries


def test_clean_end_to_end_demo_completes_all_validated_stages(tmp_path: Path):
    result = run_two_agent_demo(synthetic_artifact(tmp_path))

    assert isinstance(result, TwoAgentDemoResult)
    assert result.normalized_artifact_bundle.quality_status is ClientArtifactQualityStatus.COMPLETE
    assert NormalizedClientArtifactBundle.model_validate(
        result.normalized_artifact_bundle.model_dump(exclude_computed_fields=True)
    ) == result.normalized_artifact_bundle

    assert isinstance(result.sandbox_request, SandboxVerifierRequest)
    assert result.sandbox_request.artifact_bundle_id == result.normalized_artifact_bundle.bundle_id
    assert result.sandbox_request.allowed_artifact_metadata == (
        result.normalized_artifact_bundle.source_metadata
    )
    assert SandboxVerifierRequest.model_validate(
        result.sandbox_request.model_dump(exclude_computed_fields=True)
    ) == result.sandbox_request

    assert isinstance(result.sandbox_verifier_output, SandboxVerifierOutput)
    assert SandboxVerifierOutput.model_validate(
        result.sandbox_verifier_output.model_dump(exclude_computed_fields=True)
    ) == result.sandbox_verifier_output
    assert result.approved_public_hints
    assert all(hint.provenance is None for hint in result.approved_public_hints)

    assert isinstance(result.public_research_output, ResearchAgentOutput)
    assert ResearchAgentOutput.model_validate(
        result.public_research_output.model_dump(exclude_computed_fields=True)
    ) == result.public_research_output
    assert result.public_research_output.candidate_sources
    assert result.public_research_output.extracted_evidence

    assert result.reconciliation_result.status is EvidenceReconciliationStatus.ALIGNED
    assert result.human_review_required is False
    assert result.stage_status_summary == {
        "normalization": "COMPLETE",
        "sandbox_verification": "success",
        "safe_hint_bridge": "complete",
        "public_research": "complete",
        "evidence_reconciliation": "aligned",
    }


def test_public_research_receives_the_exact_bridge_approved_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    actual_bridge = demo_runner_module.filter_safe_public_search_hints
    actual_public_research = demo_runner_module.run_public_research_mvp
    bridge_call: dict[str, object] = {}

    def bridge_spy(output: SandboxVerifierOutput):
        approved = actual_bridge(output)
        bridge_call["output"] = output
        bridge_call["approved"] = approved
        return approved

    def public_research_spy(hints, scenario):
        assert hints is bridge_call["approved"]
        return actual_public_research(hints, scenario)

    monkeypatch.setattr(demo_runner_module, "filter_safe_public_search_hints", bridge_spy)
    monkeypatch.setattr(demo_runner_module, "run_public_research_mvp", public_research_spy)

    result = run_two_agent_demo(synthetic_artifact(tmp_path))

    assert bridge_call["output"] is result.sandbox_verifier_output
    assert bridge_call["approved"] is result.approved_public_hints
    assert all(hint.provenance is None for hint in result.approved_public_hints)


def test_sandbox_review_scenario_has_no_public_hints_and_fails_closed(tmp_path: Path):
    result = run_two_agent_demo(
        synthetic_artifact(tmp_path),
        sandbox_scenario=MockSandboxVerifierScenario.CONTRADICTION,
    )

    assert result.sandbox_verifier_output.human_review_required is True
    assert result.approved_public_hints == []
    assert result.public_research_output.candidate_sources == []
    assert result.public_research_output.missing_evidence
    assert (
        result.reconciliation_result.status
        is EvidenceReconciliationStatus.CONTRADICTORY_EVIDENCE
    )
    assert result.human_review_required is True


@pytest.mark.parametrize(
    "public_scenario, expected_status",
    [
        (PublicResearchScenario.WEAK_SOURCE, EvidenceReconciliationStatus.WEAK_PUBLIC_EVIDENCE),
        (PublicResearchScenario.STALE_SOURCE, EvidenceReconciliationStatus.STALE_PUBLIC_EVIDENCE),
        (PublicResearchScenario.SOURCE_ERROR, EvidenceReconciliationStatus.SOURCE_ERROR),
    ],
)
def test_public_issue_scenarios_require_reconciliation_review(
    tmp_path: Path,
    public_scenario: PublicResearchScenario,
    expected_status: EvidenceReconciliationStatus,
):
    result = run_two_agent_demo(
        synthetic_artifact(tmp_path),
        public_scenario=public_scenario,
    )

    assert result.public_research_output.human_review_required is True
    assert result.reconciliation_result.status is expected_status
    assert result.human_review_required is True


def test_confidential_values_and_local_identifiers_do_not_cross_public_boundary(
    tmp_path: Path,
):
    path = synthetic_artifact(tmp_path)
    result = run_two_agent_demo(path)
    local_source_ids = {
        metadata.source_id for metadata in result.normalized_artifact_bundle.source_metadata
    }

    approved_hint_text = repr(
        [hint.model_dump(mode="json") for hint in result.approved_public_hints]
    )
    public_output_text = repr(result.public_research_output.model_dump(mode="json"))
    summary_text = repr(reconciliation_summaries(result))

    protected_values = CONFIDENTIAL_VALUES | {
        LOCAL_FILENAME,
        str(path),
        *local_source_ids,
    }
    for protected_value in protected_values:
        assert protected_value not in approved_hint_text
        assert protected_value not in public_output_text
        assert protected_value not in summary_text


def test_cli_summary_excludes_confidential_and_local_sandbox_details(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    path = synthetic_artifact(tmp_path)
    result = run_two_agent_demo(path)
    cli_main([str(path), "--scenario", "clean"])
    output = capsys.readouterr().out

    assert "Two-Agent Evidence Demo" in output
    assert "Evidence reconciliation: aligned" in output
    assert "Human review required: no" in output

    protected_values = CONFIDENTIAL_VALUES | {
        LOCAL_FILENAME,
        str(path),
        *(
            metadata.source_id
            for metadata in result.normalized_artifact_bundle.source_metadata
        ),
        *(
            finding.claim_summary
            for finding in result.sandbox_verifier_output.findings
        ),
    }
    assert all(protected_value not in output for protected_value in protected_values)
    assert all(outcome not in output for outcome in FINAL_OUTCOMES)


def test_result_and_cli_have_no_compliance_outcome_fields_or_values(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    result = run_two_agent_demo(synthetic_artifact(tmp_path))
    result_field_names = {field.name for field in fields(TwoAgentDemoResult)}

    assert result_field_names.isdisjoint({"final_decision", "decision"})
    assert "final_decision" not in result.stage_status_summary
    assert "decision" not in result.stage_status_summary
    assert all(outcome not in repr(result) for outcome in FINAL_OUTCOMES)

    cli_main(["--scenario", "review"])
    output = capsys.readouterr().out
    assert "Human review required: yes" in output
    assert "final_decision" not in output.casefold()
    assert "decision" not in output.casefold()
    assert all(outcome not in output for outcome in FINAL_OUTCOMES)


def test_runner_delegates_each_stage_without_reimplementing_reconciliation():
    source = inspect.getsource(demo_runner_module)
    parsed_source = ast.parse(source)
    called_names = [
        node.func.id
        for node in ast.walk(parsed_source)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]

    assert called_names.count("normalize_client_artifact_file") == 1
    assert called_names.count("run_mock_sandbox_verifier") == 1
    assert called_names.count("filter_safe_public_search_hints") == 1
    assert called_names.count("run_public_research_mvp") == 1
    assert called_names.count("reconcile_sandbox_and_public_evidence") == 1
    assert "EvidenceReconciliationStatus" not in source
    identifiers = {
        node.id for node in ast.walk(parsed_source) if isinstance(node, ast.Name)
    }
    identifiers.update(
        node.attr for node in ast.walk(parsed_source) if isinstance(node, ast.Attribute)
    )
    assert identifiers.isdisjoint({"final_decision", "decision"})
    assert all(outcome not in source for outcome in FINAL_OUTCOMES)


def test_production_runner_introduces_no_external_or_unsafe_runtime_behavior():
    imported_roots: set[str] = set()
    called_names: set[str] = set()

    for module in (demo_runner_module, cli_module):
        parsed_source = ast.parse(inspect.getsource(module))
        for node in ast.walk(parsed_source):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0].casefold() for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0].casefold())
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id.casefold())
                elif isinstance(node.func, ast.Attribute):
                    called_names.add(node.func.attr.casefold())

    forbidden_imports = {
        "azure",
        "crewai",
        "docker",
        "http",
        "openai",
        "openpyxl",
        "pandas",
        "pdfplumber",
        "pypdf",
        "pytesseract",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    forbidden_calls = {
        "eval",
        "exec",
        "get",
        "popen",
        "post",
        "request",
        "system",
        "urlopen",
    }

    assert imported_roots.isdisjoint(forbidden_imports)
    assert called_names.isdisjoint(forbidden_calls)


def test_cli_module_smoke_run_uses_temporary_synthetic_input():
    completed = subprocess.run(
        [sys.executable, "-m", "app.run_two_agent_demo"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert "Normalization: COMPLETE" in completed.stdout
    assert "Evidence reconciliation: aligned" in completed.stdout
    assert "Human review required: no" in completed.stdout
    assert LOCAL_FILENAME not in completed.stdout
    assert all(value not in completed.stdout for value in CONFIDENTIAL_VALUES)
    assert all(outcome not in completed.stdout for outcome in FINAL_OUTCOMES)
