from ai.memo_enhancement_agent import (
    enhance_memo,
    review_memo_enhancement_response,
)
from schemas.decisions import FinalDecision
from schemas.evidence import AuditPlanningEvidenceBundle
from schemas.memo_enhancement import (
    MemoEnhancementChangeType,
    MemoEnhancementRequest,
    MemoEnhancementStatus,
)
from services.planning_memo_service import generate_planning_memo


def evidence_bundle(**updates) -> AuditPlanningEvidenceBundle:
    data = {
        "run_id": "run-memo-enhancement-1",
        "target_company": "GreenLeaf Organics",
        "evidence_data": {
            "acceptance_decision": FinalDecision.CONTINUE.value,
            "materiality_result": {
                "benchmark_type": "profit_before_tax",
                "benchmark_amount": 1_000_000,
                "overall_materiality": 50_000,
                "decision": FinalDecision.CONTINUE.value,
            },
        },
        "final_decision": FinalDecision.CONTINUE,
        "manual_review_reasons": [],
    }
    data.update(updates)
    return AuditPlanningEvidenceBundle(**data)


def request_for(bundle: AuditPlanningEvidenceBundle | None = None) -> MemoEnhancementRequest:
    bundle = bundle or evidence_bundle()
    return MemoEnhancementRequest(
        run_id=bundle.run_id,
        target_company=bundle.target_company,
        original_memo=generate_planning_memo(bundle),
        evidence_bundle=bundle,
        enhancement_instructions="Improve readability without changing conclusions.",
    )


def valid_payload(request: MemoEnhancementRequest) -> dict:
    enhanced_memo = request.original_memo.replace(
        "This conclusion is based on the structured evidence bundle",
        "This planning conclusion is based on the structured evidence bundle",
    )
    return {
        "run_id": request.run_id,
        "target_company": request.target_company,
        "status": MemoEnhancementStatus.ENHANCED,
        "original_final_decision": request.evidence_bundle.final_decision,
        "preserved_final_decision": request.evidence_bundle.final_decision,
        "preserved_manual_review_reasons": list(
            request.evidence_bundle.manual_review_reasons
        ),
        "enhanced_memo": enhanced_memo,
        "evidence_references": [
            {
                "field_path": "final_decision",
                "label": "Evidence bundle final decision",
                "quoted_value": request.evidence_bundle.final_decision.value,
            }
        ],
        "changes": [
            {
                "change_type": MemoEnhancementChangeType.READABILITY_EDIT,
                "summary": "Clarified conclusion wording without changing facts.",
            }
        ],
        "human_review_required": True,
    }


def test_valid_enhancement_preserves_decision():
    request = request_for()

    response = review_memo_enhancement_response(request, valid_payload(request))

    assert response.status == MemoEnhancementStatus.ENHANCED
    assert response.original_final_decision == FinalDecision.CONTINUE
    assert response.preserved_final_decision == FinalDecision.CONTINUE
    assert "Final decision:** CONTINUE" in response.enhanced_memo
    assert response.evidence_references[0].field_path == "final_decision"


def test_unsupported_fact_is_flagged():
    request = request_for()
    payload = valid_payload(request)
    payload["enhanced_memo"] += "\n\nThe company opened a new Paris office in 2026."
    payload["changes"] = [
        {
            "change_type": MemoEnhancementChangeType.FACTUAL_ADDITION,
            "summary": "Added a new Paris office fact.",
            "evidence_references": [],
        }
    ]

    response = review_memo_enhancement_response(request, payload)

    assert response.status == MemoEnhancementStatus.REVIEW_REQUIRED
    assert response.human_review_required is True
    assert response.unsupported_additions
    assert any("lacks evidence bundle support" in reason for reason in response.unsupported_additions)


def test_decision_change_attempt_is_rejected():
    request = request_for()
    payload = valid_payload(request)
    payload["preserved_final_decision"] = FinalDecision.REJECT
    payload["enhanced_memo"] = payload["enhanced_memo"].replace(
        "**Final decision:** CONTINUE",
        "**Final decision:** REJECT",
    )

    response = review_memo_enhancement_response(request, payload)

    assert response.status == MemoEnhancementStatus.REJECTED
    assert response.preserved_final_decision == FinalDecision.CONTINUE
    assert response.human_review_required is True
    assert any("final decision" in flag for flag in response.guardrail_flags)


def test_enhanced_memo_is_marked_human_review_required():
    request = request_for()

    response = enhance_memo(request)

    assert response.status == MemoEnhancementStatus.ENHANCED
    assert response.human_review_required is True
    assert "requires human review" in response.manual_review_reasons[0]
