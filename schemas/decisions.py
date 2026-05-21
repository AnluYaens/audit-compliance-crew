from enum import Enum


class FinalDecision(str, Enum):
    CONTINUE = "CONTINUE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECT = "REJECT"


class ControlStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
