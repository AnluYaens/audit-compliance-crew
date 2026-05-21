from manual_controls.control_model import (
    AuthorityLevel,
    ControlDomain,
    ManualControl,
)


MATERIALITY_CONTROLS = [
    ManualControl(
        control_id="MAT-001",
        domain=ControlDomain.MATERIALITY,
        chapter="Chapter 8 - Materiality",
        paragraph_reference="Chapter 8",
        authority_level=AuthorityLevel.ISA_REQUIREMENT,
        summary=(
            "Materiality must be considered during planning and must support "
            "risk assessment, audit response design, evaluation of misstatements, "
            "and formation of the audit opinion."
        ),
        required_inputs=[
            "financial_statement_basis",
            "selected_benchmark",
            "benchmark_amount",
            "materiality_percentage",
        ],
        required_outputs=[
            "overall_materiality",
            "performance_materiality",
            "clearly_trivial_threshold",
        ],
        fail_closed_if_missing=True,
        ai_allowed=False,
    )
]
