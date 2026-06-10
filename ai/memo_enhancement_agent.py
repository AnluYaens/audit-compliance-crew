from __future__ import annotations

import re
from typing import Any

from ai.auditor_assistant import evidence_field_exists
from schemas.memo_enhancement import (
    MemoEnhancementChange,
    MemoEnhancementChangeType,
    MemoEnhancementRequest,
    MemoEnhancementResponse,
    MemoEnhancementStatus,
    MemoEvidenceReference,
)


DECISION_PHRASES = (
    re.compile(r"\*\*Final decision:\*\*\s*(CONTINUE|MANUAL_REVIEW|REJECT)", re.I),
    re.compile(r"\bfinal decision(?:\s+is|:)?\s+\**(CONTINUE|MANUAL_REVIEW|REJECT)\**", re.I),
    re.compile(
        r"\bplanning outcome\b.{0,120}?\b(?:is|as)\b\s+\**(CONTINUE|MANUAL_REVIEW|REJECT)\**",
        re.I | re.S,
    ),
)


def _short_value(value: Any) -> str:
    text = str(value)
    if len(text) <= 180:
        return text
    return f"{text[:177]}..."


def _bundle_field_value(request: MemoEnhancementRequest, field_path: str) -> Any:
    current: Any = request.evidence_bundle.model_dump(mode="json")

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


def _citation(
    request: MemoEnhancementRequest,
    field_path: str,
    label: str,
) -> MemoEvidenceReference:
    return MemoEvidenceReference(
        field_path=field_path,
        label=label,
        quoted_value=_short_value(_bundle_field_value(request, field_path)),
    )


def _reported_decisions(text: str) -> set[str]:
    decisions: set[str] = set()
    for pattern in DECISION_PHRASES:
        decisions.update(match.group(1).upper() for match in pattern.finditer(text))
    return decisions


def _all_references(response: MemoEnhancementResponse) -> list[MemoEvidenceReference]:
    references = list(response.evidence_references)
    for change in response.changes:
        references.extend(change.evidence_references)
    return references


def _unsupported_change_reasons(
    request: MemoEnhancementRequest,
    response: MemoEnhancementResponse,
) -> list[str]:
    reasons = list(response.unsupported_additions)

    missing_paths = [
        reference.field_path
        for reference in _all_references(response)
        if not evidence_field_exists(request.evidence_bundle, reference.field_path)
    ]
    reasons.extend(
        f"Evidence reference is not present in the bundle: {field_path}"
        for field_path in missing_paths
    )

    for change in response.changes:
        if (
            change.change_type == MemoEnhancementChangeType.FACTUAL_ADDITION
            and not change.evidence_references
        ):
            reasons.append(
                f"Factual addition lacks evidence bundle support: {change.summary}"
            )

    return reasons


def _review_safe_response(
    request: MemoEnhancementRequest,
    *,
    status: MemoEnhancementStatus,
    enhanced_memo: str | None = None,
    evidence_references: list[MemoEvidenceReference] | None = None,
    changes: list[MemoEnhancementChange] | None = None,
    unsupported_additions: list[str] | None = None,
    guardrail_flags: list[str] | None = None,
) -> MemoEnhancementResponse:
    references = evidence_references or [
        _citation(request, "final_decision", "Evidence bundle final decision")
    ]

    return MemoEnhancementResponse(
        run_id=request.run_id,
        target_company=request.target_company,
        status=status,
        original_final_decision=request.evidence_bundle.final_decision,
        preserved_final_decision=request.evidence_bundle.final_decision,
        preserved_manual_review_reasons=list(request.evidence_bundle.manual_review_reasons),
        enhanced_memo=enhanced_memo,
        evidence_references=references,
        changes=changes or [],
        unsupported_additions=unsupported_additions or [],
        guardrail_flags=guardrail_flags or [],
        human_review_required=True,
    )


def review_memo_enhancement_response(
    request: MemoEnhancementRequest,
    response_payload: dict[str, Any] | MemoEnhancementResponse,
) -> MemoEnhancementResponse:
    """
    Validate a future AI memo enhancement against deterministic memo guardrails.

    This function does not call an LLM and does not mutate or overwrite the
    deterministic memo. Any model-backed memo draft should pass through this
    wrapper before it is shown as an enhanced draft.
    """
    response = (
        response_payload
        if isinstance(response_payload, MemoEnhancementResponse)
        else MemoEnhancementResponse.model_validate(response_payload)
    )

    if response.run_id != request.run_id or response.target_company != request.target_company:
        return _review_safe_response(
            request,
            status=MemoEnhancementStatus.REJECTED,
            guardrail_flags=[
                "Memo enhancement metadata does not match the evidence bundle.",
            ],
        )

    bundle_decision = request.evidence_bundle.final_decision
    if (
        response.original_final_decision != bundle_decision
        or response.preserved_final_decision != bundle_decision
    ):
        return _review_safe_response(
            request,
            status=MemoEnhancementStatus.REJECTED,
            enhanced_memo=response.enhanced_memo,
            guardrail_flags=[
                "Memo enhancement attempted to change or misstate the final decision.",
            ],
        )

    if response.preserved_manual_review_reasons != request.evidence_bundle.manual_review_reasons:
        return _review_safe_response(
            request,
            status=MemoEnhancementStatus.REJECTED,
            enhanced_memo=response.enhanced_memo,
            guardrail_flags=[
                "Memo enhancement did not preserve evidence bundle manual review reasons.",
            ],
        )

    if response.enhanced_memo:
        reported_decisions = _reported_decisions(response.enhanced_memo)
        unsupported_decisions = {
            decision
            for decision in reported_decisions
            if decision != bundle_decision.value
        }
        if unsupported_decisions:
            return _review_safe_response(
                request,
                status=MemoEnhancementStatus.REJECTED,
                enhanced_memo=response.enhanced_memo,
                guardrail_flags=[
                    "Enhanced memo text attempted to change or override the final decision.",
                ],
            )

    unsupported_additions = _unsupported_change_reasons(request, response)
    if unsupported_additions:
        return _review_safe_response(
            request,
            status=MemoEnhancementStatus.REVIEW_REQUIRED,
            enhanced_memo=response.enhanced_memo,
            evidence_references=response.evidence_references,
            changes=response.changes,
            unsupported_additions=unsupported_additions,
            guardrail_flags=response.guardrail_flags,
        )

    if not any(
        reference.field_path == "final_decision" for reference in response.evidence_references
    ):
        response.evidence_references.append(
            _citation(request, "final_decision", "Evidence bundle final decision")
        )

    return response


def enhance_memo(request: MemoEnhancementRequest) -> MemoEnhancementResponse:
    """
    Deterministic no-op enhancement facade for local guardrail tests.

    Future model output should be reviewed with review_memo_enhancement_response.
    Until then, this returns the original memo as an enhanced draft and marks it
    for human review.
    """
    return review_memo_enhancement_response(
        request,
        MemoEnhancementResponse(
            run_id=request.run_id,
            target_company=request.target_company,
            status=MemoEnhancementStatus.ENHANCED,
            original_final_decision=request.evidence_bundle.final_decision,
            preserved_final_decision=request.evidence_bundle.final_decision,
            preserved_manual_review_reasons=list(
                request.evidence_bundle.manual_review_reasons
            ),
            enhanced_memo=request.original_memo,
            evidence_references=[
                _citation(request, "final_decision", "Evidence bundle final decision")
            ],
            changes=[
                MemoEnhancementChange(
                    change_type=MemoEnhancementChangeType.READABILITY_EDIT,
                    summary=(
                        "No model enhancement was applied; deterministic memo was preserved."
                    ),
                )
            ],
            human_review_required=True,
        ),
    )


class MemoEnhancementAgent:
    """Deterministic memo enhancement wrapper for guardrail tests."""

    def run(
        self,
        request: MemoEnhancementRequest,
        response_payload: dict[str, Any] | MemoEnhancementResponse | None = None,
    ) -> MemoEnhancementResponse:
        if response_payload is None:
            return enhance_memo(request)

        return review_memo_enhancement_response(request, response_payload)


__all__ = [
    "MemoEnhancementAgent",
    "enhance_memo",
    "review_memo_enhancement_response",
]
