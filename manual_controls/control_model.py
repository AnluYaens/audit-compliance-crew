from enum import Enum
from pydantic import BaseModel, Field


class AuthorityLevel(str, Enum):
    ISA_REQUIREMENT = "ISA_REQUIREMENT"
    BDO_POLICY_REQUIREMENT = "BDO_POLICY_REQUIREMENT"
    BDO_DE_REQUIREMENT = "BDO_DE_REQUIREMENT"
    APPLICATION_GUIDANCE = "APPLICATION_GUIDANCE"


class ControlDomain(str, Enum):
    ACCEPTANCE = "ACCEPTANCE"
    PLANNING = "PLANNING"
    MATERIALITY = "MATERIALITY"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    FRAUD = "FRAUD"
    AUDIT_RESPONSE = "AUDIT_RESPONSE"
    AUTOMATED_TOOLS = "AUTOMATED_TOOLS"


class ManualControl(BaseModel):
    control_id: str
    domain: ControlDomain
    chapter: str
    paragraph_reference: str
    authority_level: AuthorityLevel
    summary: str
    required_inputs: list[str] = Field(default_factory=list)
    required_outputs: list[str] = Field(default_factory=list)
    fail_closed_if_missing: bool = True
    ai_allowed: bool = False

