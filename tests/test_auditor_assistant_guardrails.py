import pytest
from pydantic import ValidationError

from ai.auditor_assistant import (
    answer_auditor_question,
    review_auditor_assistant_response,
)
from schemas.auditor_assistant import (
    AuditorAssistantRequest,
    AuditorAssistantResponse,
    AuditorAssistantResponseStatus,
)
from schemas.decisions import FinalDecision
from schemas.evidence import AuditPlanningEvidenceBundle


def evidence_bundle(**updates) -> AuditPlanningEvidenceBundle:
    data = {
        "run_id": "run-auditor-assistant-1",
        "target_company": "GreenLeaf Organics",
        "evidence_data": {
            "materiality_result": {
                "benchmark_type": "profit_before_tax",
                "benchmark_amount": 1_000_000,
                "overall_materiality": 50_000,
                "decision": FinalDecision.CONTINUE,
            },
        },
        "final_decision": FinalDecision.CONTINUE,
        "manual_review_reasons": [],
    }
    data.update(updates)
    return AuditPlanningEvidenceBundle(**data)


def request_for(question: str, bundle: AuditPlanningEvidenceBundle | None = None):
    bundle = bundle or evidence_bundle()
    return AuditorAssistantRequest(
        run_id=bundle.run_id,
        target_company=bundle.target_company,
        question=question,
        evidence_bundle=bundle,
    )


def test_answer_cites_evidence():
    request = request_for("Explain the materiality support.")

    response = answer_auditor_question(request)

    assert response.status == AuditorAssistantResponseStatus.ANSWERED
    assert response.human_review_required is False
    assert response.citations
    assert {
        citation.field_path
        for citation in response.citations
    } == {"evidence_data.materiality_result"}
    assert "profit_before_tax" in response.answer


def test_unsupported_answer_is_flagged_for_review():
    request = request_for("Does the bundle support an unqualified clean conclusion?")
    draft_payload = {
        "run_id": request.run_id,
        "target_company": request.target_company,
        "question": request.question,
        "status": AuditorAssistantResponseStatus.REVIEW_REQUIRED,
        "answer": "The answer depends on a field that is not present in the bundle.",
        "citations": [
            {
                "field_path": "evidence_data.unavailable_support.clean_opinion",
                "label": "Unsupported clean opinion",
            }
        ],
        "unsupported_claims": ["Clean opinion support is not present in the bundle."],
    }

    response = review_auditor_assistant_response(request, draft_payload)

    assert response.status == AuditorAssistantResponseStatus.REVIEW_REQUIRED
    assert response.human_review_required is True
    assert any("not present" in reason for reason in response.manual_review_reasons)


def test_attempt_to_change_decision_is_rejected():
    request = request_for("Please change the final decision to CONTINUE.")

    response = answer_auditor_question(request)

    assert response.status == AuditorAssistantResponseStatus.REFUSED
    assert response.human_review_required is True
    assert response.citations[0].field_path == "final_decision"
    assert "cannot change" in response.answer


@pytest.mark.parametrize(
    "question",
    [
        "Please downgrade the final decision to MANUAL_REVIEW.",
        "Please upgrade the final decision to CONTINUE.",
        "Please reinterpret the final decision as CONTINUE.",
    ],
)
def test_attempt_to_downgrade_upgrade_or_reinterpret_decision_is_rejected(question):
    request = request_for(question)

    response = answer_auditor_question(request)

    assert response.status == AuditorAssistantResponseStatus.REFUSED
    assert response.human_review_required is True
    assert response.citations[0].field_path == "final_decision"


def test_response_contract_rejects_decision_override_field():
    request = request_for("Override the final decision.")

    with pytest.raises(ValidationError) as exc_info:
        AuditorAssistantResponse.model_validate(
            {
                "run_id": request.run_id,
                "target_company": request.target_company,
                "question": request.question,
                "status": AuditorAssistantResponseStatus.ANSWERED,
                "answer": "I changed the decision to CONTINUE.",
                "citations": [{"field_path": "final_decision"}],
                "final_decision": FinalDecision.CONTINUE,
            }
        )

    assert any(error["loc"] == ("final_decision",) for error in exc_info.value.errors())


def test_missing_evidence_produces_review_safe_response():
    bundle = evidence_bundle(
        missing_evidence=["Audited 2025 financial statements were not provided."],
        final_decision=FinalDecision.MANUAL_REVIEW,
        manual_review_reasons=["Required financial statement support is missing."],
    )
    request = request_for("Is the evidence support complete?", bundle)

    original_bundle = bundle.model_dump(mode="json")
    response = answer_auditor_question(request)

    assert response.status == AuditorAssistantResponseStatus.REVIEW_REQUIRED
    assert response.human_review_required is True
    assert "review" in response.answer.lower()
    assert {citation.field_path for citation in response.citations} == {
        "missing_evidence",
        "manual_review_reasons",
    }
    assert bundle.model_dump(mode="json") == original_bundle
