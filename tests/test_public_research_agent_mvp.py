import ast
import inspect

import pytest
from pydantic import ValidationError

import ai.public_research_agent as public_research_agent_module
from ai.public_research_agent import (
    PublicResearchAgent,
    PublicResearchScenario,
    run_public_research_mvp,
)
from schemas.client_artifacts import (
    ClientArtifactSensitivity,
    NormalizedClientArtifactBundle,
)
from schemas.research_agent import EvidenceStatus, ResearchAgentOutput
from schemas.sandbox_verifier import (
    LocalEvidenceFinding,
    SafePublicSearchHintCandidate,
    SafePublicSearchHintSensitivity,
    SafePublicSearchHintType,
)


CONFIDENTIAL_SYNTHETIC_VALUE = "SYNTHETIC-PRIVATE-VALUE-7788"
FINAL_OUTCOMES = {"CONTINUE", "MANUAL_REVIEW", "REJECT"}


def safe_hint(
    hint_type: SafePublicSearchHintType = SafePublicSearchHintType.ANNUAL_REPORT,
) -> SafePublicSearchHintCandidate:
    return SafePublicSearchHintCandidate(
        hint_id="synthetic-safe-public-hint-1",
        hint_text="Synthetic Public Entity annual report",
        hint_type=hint_type,
        safe_reason="Uses synthetic public-style terms only.",
        sensitivity=SafePublicSearchHintSensitivity.PUBLIC,
        confidence=0.91,
    )


def assert_schema_valid(output: ResearchAgentOutput) -> None:
    payload = output.model_dump(exclude_computed_fields=True)
    assert ResearchAgentOutput.model_validate(payload) == output


def test_clean_scenario_returns_schema_valid_public_research_output():
    output = PublicResearchAgent().run([safe_hint()], PublicResearchScenario.CLEAN)

    assert_schema_valid(output)
    assert output.human_review_required is False
    assert output.candidate_sources
    assert output.extracted_evidence[0].status == EvidenceStatus.PRESENT
    assert output.extracted_evidence[0].confidence >= 0.75


def test_no_hints_scenario_fails_closed_to_review_handling():
    output = run_public_research_mvp([], PublicResearchScenario.NO_HINTS)

    assert_schema_valid(output)
    assert output.human_review_required is True
    assert output.missing_evidence
    assert output.candidate_sources == []


def test_empty_clean_input_also_fails_closed():
    output = run_public_research_mvp([])
    assert output.human_review_required is True
    assert output.missing_evidence


def test_weak_source_is_low_confidence_and_requires_review():
    output = run_public_research_mvp([safe_hint()], PublicResearchScenario.WEAK_SOURCE)

    assert output.human_review_required is True
    assert output.candidate_sources[0].confidence < 0.75
    assert output.extracted_evidence[0].status == EvidenceStatus.LOW_CONFIDENCE


def test_stale_source_is_outdated_and_requires_review():
    output = run_public_research_mvp([safe_hint()], PublicResearchScenario.STALE_SOURCE)
    payload_text = repr(output.model_dump(mode="json")).lower()

    assert output.human_review_required is True
    assert output.candidate_sources[0].missing_evidence
    assert "stale" in payload_text
    assert "outdated" in payload_text


def test_contradictory_public_evidence_preserves_signals():
    output = run_public_research_mvp(
        [safe_hint()], PublicResearchScenario.CONTRADICTORY_PUBLIC_EVIDENCE
    )

    assert output.human_review_required is True
    assert output.contradictions
    assert output.candidate_sources[0].contradictions
    assert output.extracted_evidence[0].status == EvidenceStatus.CONTRADICTED
    assert output.extracted_evidence[0].contradictions


def test_source_error_preserves_error_and_review_signal():
    output = run_public_research_mvp([safe_hint()], PublicResearchScenario.SOURCE_ERROR)

    assert_schema_valid(output)
    assert output.human_review_required is True
    assert output.tool_errors
    assert output.candidate_sources == []


def test_wrapper_accepts_validated_safe_hint_candidates_only():
    output = run_public_research_mvp(
        [safe_hint(SafePublicSearchHintType.REGULATOR_SOURCE)]
    )
    assert output.candidate_sources

    with pytest.raises(TypeError):
        run_public_research_mvp([safe_hint().model_dump()])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        run_public_research_mvp((safe_hint(),))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        run_public_research_mvp([object()])  # type: ignore[list-item]


@pytest.mark.parametrize(
    "sensitivity",
    [ClientArtifactSensitivity.CONFIDENTIAL.value, ClientArtifactSensitivity.RESTRICTED.value],
)
def test_confidential_or_restricted_hint_like_payload_is_rejected(sensitivity: str):
    payload = safe_hint().model_dump()
    payload["sensitivity"] = sensitivity

    with pytest.raises(ValidationError):
        SafePublicSearchHintCandidate.model_validate(payload)
    with pytest.raises(TypeError):
        run_public_research_mvp([payload])  # type: ignore[list-item]


def test_constructed_unsafe_hint_is_rejected_by_wrapper():
    unsafe_hint = safe_hint().model_copy(
        update={"sensitivity": ClientArtifactSensitivity.CONFIDENTIAL.value}
    )
    with pytest.raises(ValueError, match="unsafe sensitivity"):
        run_public_research_mvp([unsafe_hint])


@pytest.mark.parametrize(
    "unsafe_input",
    [NormalizedClientArtifactBundle.model_construct(), LocalEvidenceFinding.model_construct()],
)
def test_client_artifacts_and_local_findings_are_rejected(unsafe_input: object):
    with pytest.raises(TypeError):
        run_public_research_mvp([unsafe_input])  # type: ignore[list-item]


@pytest.mark.parametrize(
    "update",
    [
        {"hint_text": "Confidential synthetic client artifact value"},
        {"human_review_recommended": True},
        {"confidence": 0.40},
    ],
)
def test_unsafe_or_unreviewed_validated_hint_is_rejected(update: dict[str, object]):
    unsafe_hint = safe_hint().model_copy(update=update)

    with pytest.raises(ValueError):
        run_public_research_mvp([unsafe_hint])


def test_public_output_does_not_echo_confidential_hint_values():
    mislabeled_hint = safe_hint().model_copy(
        update={
            "hint_id": CONFIDENTIAL_SYNTHETIC_VALUE,
            "hint_text": CONFIDENTIAL_SYNTHETIC_VALUE,
            "safe_reason": CONFIDENTIAL_SYNTHETIC_VALUE,
        }
    )
    output = run_public_research_mvp([mislabeled_hint])
    assert CONFIDENTIAL_SYNTHETIC_VALUE not in repr(output.model_dump(mode="json"))


def test_output_has_no_decision_fields_or_final_outcomes():
    assert "final_decision" not in ResearchAgentOutput.model_fields
    assert "decision" not in ResearchAgentOutput.model_fields

    for scenario in PublicResearchScenario:
        hints = [] if scenario == PublicResearchScenario.NO_HINTS else [safe_hint()]
        payload = run_public_research_mvp(hints, scenario).model_dump(mode="json")
        payload_text = repr(payload)

        assert "final_decision" not in payload
        assert "decision" not in payload
        assert all(outcome not in payload_text for outcome in FINAL_OUTCOMES)


def test_wrapper_source_introduces_no_external_or_unsafe_runtime_behavior():
    source = inspect.getsource(public_research_agent_module)
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
        "subprocess", "requests", "urllib", "http", "socket", "openai", "crewai",
        "azure", "pytesseract", "pypdf", "pdfplumber", "openpyxl", "pandas",
    }
    assert imported_roots.isdisjoint(forbidden_imports)
    assert called_names.isdisjoint({"open", "exec", "eval", "compile"})
    assert all(
        term not in source.lower()
        for term in {"docker", "virtualmachine", "virtual machine"}
    )


def test_test_data_is_synthetic_only():
    payload_text = repr(run_public_research_mvp([safe_hint()]).model_dump(mode="json"))

    assert "Synthetic" in payload_text
    assert "Acme" not in payload_text
    assert "Contoso" not in payload_text
    assert "Globex" not in payload_text
