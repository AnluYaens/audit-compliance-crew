from crewai import Agent, LLM
from tools.compliance_tools import (
    calculate_weighted_risk_score,
    check_partner_independence,
    read_client_crm_data,
    scan_sanctions_watchlist,
)

# Configura la conexión local con Ollama
# Puedes cambiar "llama3" por "mistral" o "llama3.1" según el modelo que descargues
local_llm = LLM(
    model="ollama/llama3.1",  
    base_url="http://localhost:11434"
)

ingestion_agent = Agent(
    role="Senior Data Ingestion Specialist",
    goal="Extract corporate profiles from file datastores and preserve the validated JSON contract exactly.",
    backstory=(
        "You are the system's deterministic data gateway. You use specialized file utilities "
        "to pull validated JSON profiles cleanly, and you never guess, reshape, or repair schema fields."
    ),
    tools=[read_client_crm_data],
    llm=local_llm,  
    verbose=True,
    allow_delegation=False
)

independence_agent = Agent(
    role="Independence & Sanctions Compliance Detective",
    goal="Verify corporate entities against internal equity registries and sanctions databases using only validated payloads.",
    backstory=(
        "You are a strict compliance risk auditor. You pass exact schema fields into deterministic tools "
        "and preserve the returned screening contracts without narrative edits."
    ),
    tools=[check_partner_independence, scan_sanctions_watchlist],
    llm=local_llm,
    verbose=True,
    allow_delegation=False
)

risk_agent = Agent(
    role="Lead Audit Risk Analyst",
    goal="Map validated corporate parameters to approved risk states and execute deterministic risk scoring.",
    backstory=(
        "You translate validated CRM fields into the approved High, Medium, Low, or INVALID_INPUT states. "
        "The Python tool owns all math and fail-closed validation."
    ),
    tools=[calculate_weighted_risk_score],
    llm=local_llm,
    verbose=True,
    allow_delegation=False
)

guidance_agent = Agent(
    role="Professional Standards Quality Author",
    goal="Compile validated structural findings into a formalized Client Acceptance Memo.",
    backstory=(
        "You consume explicit JSON contracts from upstream agents as immutable evidence. "
        "You write the memo narrative without changing statuses, decisions, scores, blockers, or source facts."
    ),
    llm=local_llm,
    verbose=True,
    allow_delegation=False
)
