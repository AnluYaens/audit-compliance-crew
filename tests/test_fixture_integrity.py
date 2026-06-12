import json
from pathlib import Path

from schemas.decisions import FinalDecision
from schemas.evidence import AuditPlanningEvidenceBundle
from schemas.financial_statements import FinancialStatementSet
from schemas.research_agent import ResearchAgentOutput


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
EVAL_GOLDEN_ROOT = Path(__file__).parents[1] / "evals" / "golden_outputs"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def json_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.json"))


def test_required_fixture_directories_exist():
    assert (FIXTURE_ROOT / "evidence_bundles").is_dir()
    assert (FIXTURE_ROOT / "agent_outputs").is_dir()
    assert (FIXTURE_ROOT / "financial_statements").is_dir()
    assert EVAL_GOLDEN_ROOT.is_dir()


def test_representative_fixture_files_exist():
    expected_files = [
        FIXTURE_ROOT / "evidence_bundles" / "clean_continue.json",
        FIXTURE_ROOT / "evidence_bundles" / "reject_independence_conflict.json",
        FIXTURE_ROOT / "evidence_bundles" / "manual_review_missing_source_support.json",
        FIXTURE_ROOT / "agent_outputs" / "clean_research_agent_output.json",
        FIXTURE_ROOT / "agent_outputs" / "contradiction_research_agent_output.json",
        FIXTURE_ROOT / "agent_outputs" / "missing_evidence_research_agent_output.json",
        FIXTURE_ROOT / "agent_outputs" / "low_confidence_research_agent_output.json",
        FIXTURE_ROOT / "financial_statements" / "clean_financial_statement_set.json",
        FIXTURE_ROOT / "financial_statements" / "missing_line_item_financial_statement_set.json",
        FIXTURE_ROOT / "financial_statements" / "low_confidence_financial_statement_set.json",
        EVAL_GOLDEN_ROOT / "case_index.json",
    ]

    for expected_file in expected_files:
        assert expected_file.is_file(), f"Missing fixture: {expected_file}"


def test_evidence_bundle_fixtures_validate_against_schema():
    bundles = [
        AuditPlanningEvidenceBundle.model_validate(load_json(path))
        for path in json_files(FIXTURE_ROOT / "evidence_bundles")
    ]

    assert {bundle.final_decision for bundle in bundles} == {
        FinalDecision.CONTINUE,
        FinalDecision.MANUAL_REVIEW,
        FinalDecision.REJECT,
    }
    assert all(bundle.created_at.year == 2025 for bundle in bundles)


def test_agent_output_fixtures_validate_against_schema():
    outputs = [
        ResearchAgentOutput.model_validate(load_json(path))
        for path in json_files(FIXTURE_ROOT / "agent_outputs")
    ]

    assert any(not output.human_review_required for output in outputs)
    assert any("CONTRADICTED" in reason for output in outputs for reason in output.manual_review_reasons)
    assert any("missing support" in reason for output in outputs for reason in output.manual_review_reasons)
    assert any("below 0.75" in reason for output in outputs for reason in output.manual_review_reasons)


def test_financial_statement_fixtures_validate_against_schema():
    statement_sets = [
        FinancialStatementSet.model_validate(load_json(path))
        for path in json_files(FIXTURE_ROOT / "financial_statements")
    ]

    assert any(not statement_set.manual_review_required for statement_set in statement_sets)
    assert any("Missing required line item" in reason for statement_set in statement_sets for reason in statement_set.manual_review_reasons)
    assert any("below 0.75" in reason for statement_set in statement_sets for reason in statement_set.manual_review_reasons)


def test_golden_output_metadata_is_readable():
    golden_files = json_files(EVAL_GOLDEN_ROOT)

    assert golden_files

    for golden_file in golden_files:
        payload = load_json(golden_file)
        metadata = payload["metadata"]

        assert metadata["schema_version"] == "1.0"
        assert metadata["dataset_name"]
        assert "created_at" in metadata.get("normalized_fields", [])
