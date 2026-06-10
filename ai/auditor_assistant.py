from __future__ import annotations

from typing import Any

from schemas.auditor_assistant import (
    AuditorAssistantCitation,
    AuditorAssistantRequest,
    AuditorAssistantResponse,
    AuditorAssistantResponseStatus,
)
from schemas.evidence import AuditPlanningEvidenceBundle


DECISION_MUTATION_TERMS = (
    "change decision",
    "change the decision",
    "override decision",
    "override the decision",
    "set decision",
    "set the decision",
    "assign decision",
    "assign the decision",
    "downgrade decision",
    "downgrade the decision",
    "downgrade final_decision",
    "downgrade the final decision",
    "upgrade decision",
    "upgrade the decision",
    "upgrade final_decision",
    "upgrade the final decision",
    "reinterpret decision",
    "reinterpret the decision",
    "reinterpret final_decision",
    "reinterpret the final decision",
    "approve the client",
    "reject the client",
    "mark as continue",
    "mark as reject",
    "mark as manual_review",
    "mark the decision",
    "update final_decision",
    "update the final decision",
    "change final_decision",
    "change the final decision",
    "override final_decision",
    "override the final decision",
    "set final_decision",
    "set the final decision",
)


def _bundle_to_mapping(bundle: AuditPlanningEvidenceBundle) -> dict[str, Any]:
    return bundle.model_dump(mode="json")


def _get_field_value(bundle: AuditPlanningEvidenceBundle, field_path: str) -> Any:
    current: Any = _bundle_to_mapping(bundle)

    for part in field_path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(field_path)
            current = current[part]
            continue

        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                raise KeyError(field_path)
            current = current[index]
            continue

        raise KeyError(field_path)

    return current


def evidence_field_exists(bundle: AuditPlanningEvidenceBundle, field_path: str) -> bool:
    try:
        _get_field_value(bundle, field_path)
    except KeyError:
        return False
    return True


def _short_value(value: Any) -> str:
    text = str(value)
    if len(text) <= 180:
        return text
    return f"{text[:177]}..."


def _citation(
    bundle: AuditPlanningEvidenceBundle,
    field_path: str,
    label: str,
) -> AuditorAssistantCitation:
    return AuditorAssistantCitation(
        field_path=field_path,
        label=label,
        quoted_value=_short_value(_get_field_value(bundle, field_path)),
    )


def _contains_decision_mutation(text: str) -> bool:
    normalized = text.lower().replace("-", "_")
    return any(term in normalized for term in DECISION_MUTATION_TERMS)


def _review_safe_response(
    request: AuditorAssistantRequest,
    *,
    status: AuditorAssistantResponseStatus,
    answer: str,
    unsupported_claims: list[str] | None = None,
    guardrail_flags: list[str] | None = None,
    citations: list[AuditorAssistantCitation] | None = None,
) -> AuditorAssistantResponse:
    return AuditorAssistantResponse(
        run_id=request.run_id,
        target_company=request.target_company,
        question=request.question,
        status=status,
        answer=answer,
        citations=citations or [],
        unsupported_claims=unsupported_claims or [],
        guardrail_flags=guardrail_flags or [],
    )


def review_auditor_assistant_response(
    request: AuditorAssistantRequest,
    response_payload: dict[str, Any] | AuditorAssistantResponse,
) -> AuditorAssistantResponse:
    """
    Validate an assistant draft against evidence-bundle guardrails.

    Schema violations, including extra decision fields such as final_decision, are
    rejected by Pydantic. Support gaps in an otherwise structured response are
    converted to review-safe language.
    """
    response = (
        response_payload
        if isinstance(response_payload, AuditorAssistantResponse)
        else AuditorAssistantResponse.model_validate(response_payload)
    )

    if response.run_id != request.run_id or response.target_company != request.target_company:
        return _review_safe_response(
            request,
            status=AuditorAssistantResponseStatus.REVIEW_REQUIRED,
            answer=(
                "I cannot rely on this response because it does not match the "
                "evidence bundle run or target company. Manual review is required."
            ),
            unsupported_claims=["Response metadata does not match the evidence bundle."],
        )

    if _contains_decision_mutation(response.answer):
        return _review_safe_response(
            request,
            status=AuditorAssistantResponseStatus.REFUSED,
            answer=(
                "I cannot change, assign, or override the evidence bundle decision. "
                "The deterministic pipeline owns final decision values."
            ),
            guardrail_flags=["Assistant response attempted to change or override a decision."],
            citations=[
                _citation(
                    request.evidence_bundle,
                    "final_decision",
                    "Evidence bundle final decision",
                )
            ],
        )

    missing_paths = [
        citation.field_path
        for citation in response.citations
        if not evidence_field_exists(request.evidence_bundle, citation.field_path)
    ]
    if missing_paths:
        return _review_safe_response(
            request,
            status=AuditorAssistantResponseStatus.REVIEW_REQUIRED,
            answer=(
                "I cannot support the drafted answer from the cited evidence bundle "
                "fields. Manual review is required before relying on it."
            ),
            unsupported_claims=[
                f"Citation field path is not present in the evidence bundle: {field_path}"
                for field_path in missing_paths
            ],
        )

    if response.status == AuditorAssistantResponseStatus.ANSWERED and not response.citations:
        return _review_safe_response(
            request,
            status=AuditorAssistantResponseStatus.REVIEW_REQUIRED,
            answer=(
                "I cannot answer this from the evidence bundle without cited support. "
                "Manual review is required."
            ),
            unsupported_claims=["Answered response had no evidence bundle citations."],
        )

    return response


def answer_auditor_question(request: AuditorAssistantRequest) -> AuditorAssistantResponse:
    """
    Deterministic auditor-assistant facade for local guardrail tests.

    This function does not call an LLM and never mutates the evidence bundle.
    Future model-backed output should be passed through
    review_auditor_assistant_response before use.
    """
    bundle = request.evidence_bundle
    question = request.question.lower()

    if _contains_decision_mutation(question):
        return _review_safe_response(
            request,
            status=AuditorAssistantResponseStatus.REFUSED,
            answer=(
                "I cannot change, assign, or override final decisions. The evidence "
                "bundle remains the source of truth and deterministic Python services "
                "own decision values."
            ),
            guardrail_flags=["Auditor question requested a decision change or override."],
            citations=[_citation(bundle, "final_decision", "Evidence bundle final decision")],
        )

    if bundle.missing_evidence and (
        "missing" in question or "support" in question or "evidence" in question
    ):
        return _review_safe_response(
            request,
            status=AuditorAssistantResponseStatus.REVIEW_REQUIRED,
            answer=(
                "The evidence bundle records missing support, so this needs auditor "
                "review before any clean conclusion can be relied on."
            ),
            guardrail_flags=["Evidence bundle contains missing evidence."],
            citations=[
                _citation(bundle, "missing_evidence", "Missing evidence"),
                _citation(bundle, "manual_review_reasons", "Manual review reasons"),
            ],
        )

    if "materiality" in question and evidence_field_exists(
        bundle,
        "evidence_data.materiality_result",
    ):
        materiality = bundle.evidence_data["materiality_result"]
        benchmark_type = materiality.get("benchmark_type", "not available")
        decision = materiality.get("decision", "not available")
        return review_auditor_assistant_response(
            request,
            AuditorAssistantResponse(
                run_id=request.run_id,
                target_company=request.target_company,
                question=request.question,
                status=AuditorAssistantResponseStatus.ANSWERED,
                answer=(
                    "The evidence bundle records materiality using benchmark "
                    f"{benchmark_type} with materiality module decision {decision}."
                ),
                citations=[
                    _citation(
                        bundle,
                        "evidence_data.materiality_result",
                        "Materiality result",
                    )
                ],
            ),
        )

    if "decision" in question:
        citations = [_citation(bundle, "final_decision", "Evidence bundle final decision")]
        if bundle.manual_review_reasons:
            citations.append(
                _citation(bundle, "manual_review_reasons", "Manual review reasons")
            )

        return review_auditor_assistant_response(
            request,
            AuditorAssistantResponse(
                run_id=request.run_id,
                target_company=request.target_company,
                question=request.question,
                status=AuditorAssistantResponseStatus.ANSWERED,
                answer=(
                    "The evidence bundle records the final decision as "
                    f"{bundle.final_decision.value}. I can explain the cited bundle "
                    "fields, but I cannot change that decision."
                ),
                citations=citations,
            ),
        )

    return _review_safe_response(
        request,
        status=AuditorAssistantResponseStatus.REVIEW_REQUIRED,
        answer=(
            "I cannot answer this question from the currently available evidence "
            "bundle fields. Manual review is required or more cited support should "
            "be added through the deterministic pipeline."
        ),
        unsupported_claims=["No supported evidence bundle field matched the auditor question."],
    )


class AuditorAssistant:
    """Deterministic auditor assistant wrapper for guardrail tests."""

    def run(self, request: AuditorAssistantRequest) -> AuditorAssistantResponse:
        return answer_auditor_question(request)


__all__ = [
    "AuditorAssistant",
    "answer_auditor_question",
    "evidence_field_exists",
    "review_auditor_assistant_response",
]
