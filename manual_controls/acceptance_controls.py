from manual_controls.control_model import (
    AuthorityLevel,
    ControlDomain,
    ManualControl,
)


ACCEPTANCE_CONTROLS = [
    ManualControl(
        control_id="ACC-001",
        domain=ControlDomain.ACCEPTANCE,
        chapter="Acceptance and Continuance",
        paragraph_reference="Acceptance and Continuance",
        authority_level=AuthorityLevel.FIRM_POLICY_REQUIREMENT,
        summary=(
            "Acceptance and continuance must be evaluated before proceeding "
            "with the engagement."
        ),
        required_inputs=[
            "target_company",
            "kyc_result",
            "sanctions_result",
            "independence_result",
        ],
        required_outputs=[
            "acceptance_decision",
            "manual_review_reasons",
        ],
        fail_closed_if_missing=True,
        ai_allowed=False,
    )
]
