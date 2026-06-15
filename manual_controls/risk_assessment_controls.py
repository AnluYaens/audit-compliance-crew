from manual_controls.control_model import (
    AuthorityLevel,
    ControlDomain,
    ManualControl,
)


RISK_ASSESSMENT_CONTROLS = [
    ManualControl(
        control_id="RISK-001",
        domain=ControlDomain.RISK_ASSESSMENT,
        chapter="Risk Assessment Procedures",
        paragraph_reference="Risk Assessment Procedures",
        authority_level=AuthorityLevel.ISA_REQUIREMENT,
        summary=(
            "The audit team must identify and assess risks of material "
            "misstatement at the financial statement level and assertion level."
        ),
        required_inputs=[
            "entity_understanding",
            "financial_statement_areas",
            "assertions",
            "risk_indicators",
        ],
        required_outputs=[
            "identified_risks",
            "risk_level",
            "affected_assertions",
            "evidence_references",
        ],
        fail_closed_if_missing=True,
        ai_allowed=False,
    )
]
