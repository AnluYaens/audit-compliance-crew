from crewai import Task
from agents import ingestion_agent, independence_agent, risk_agent, guidance_agent

task_ingestion = Task(
    description=(
        "Use the 'Read Client CRM Data' tool to fetch the file records for '{target_company}'. "
        "Return exactly the compact JSON emitted by the tool and nothing else. "
        "The returned payload must conform to the IngestionToolOutput schema: "
        "schema_version, tool, status, decision, is_blocker, severity, source, query, "
        "matched_company, match_score, match_type, and data. "
        "Do not flatten, rename, summarize, or repair any field. "
        "If status is not SUCCESS, return the tool JSON unchanged and do not invent client data."
    ),
    expected_output="The exact canonical IngestionToolOutput JSON object from the CRM tool.",
    agent=ingestion_agent
)

task_independence = Task(
    description=(
        "Use only the data object inside the canonical IngestionToolOutput JSON from the Ingestion task. "
        "If ingestion status is not SUCCESS or decision is not CONTINUE, return a JSON object with "
        "final_screening_decision=MANUAL_REVIEW and include the unchanged ingestion payload under ingestion_error. "
        "1. Pass data.Company_Name exactly to the 'Check Partner Independence' tool.\n"
        "2. Pass data.CEO_Name, data.Company_Name, and data.Global_Offices exactly to the 'Scan Sanctions Watchlist' tool.\n"
        "Return one compact JSON object conforming to ScreeningAggregateResponse with keys: "
        "company_name, independence_result, sanctions_result, blocking_statuses, final_screening_decision. "
        "independence_result and sanctions_result must be the exact parsed JSON payloads returned by their tools; "
        "do not summarize, rename, or rewrite their contract fields. "
        "blocking_statuses must include any tool status equal to CONFLICT_DETECTED, SANCTIONS_HIT, ERROR, "
        "INVALID_INPUT, or NOT_FOUND. final_screening_decision must be REJECT if any tool decision is REJECT, "
        "MANUAL_REVIEW if any tool decision is MANUAL_REVIEW, otherwise CONTINUE."
    ),
    expected_output="A canonical ScreeningAggregateResponse JSON object containing exact screening tool payloads.",
    agent=independence_agent,
    context=[task_ingestion]
)

task_risk = Task(
    description=(
        "Analyze only the data object inside the canonical IngestionToolOutput JSON from Ingestion. "
        "If ingestion status is not SUCCESS or required fields are missing, call the risk tool with "
        "INVALID_INPUT for each missing or unmappable dimension so it fails closed.\n"
        "1. Map Industry: Technology=Medium, Extractives=High, Energy=High, Agriculture=Low.\n"
        "2. Map Geography: If offices contain Iraq, Libya, or Venezuela, set to High. Else Low.\n"
        "3. Map Financial: If stability is High -> Low. If Medium -> Medium. If Low -> High.\n"
        "Execute the 'Calculate Weighted Risk Score' tool using these three exact mapped strings as flat arguments. "
        "Do not nest arguments inside dictionary keys like mapped_inputs. "
        "Return exactly the compact RiskScoringOutput JSON emitted by the tool and nothing else."
    ),
    expected_output="The exact canonical RiskScoringOutput JSON object from the risk calculator tool.",
    agent=risk_agent,
    context=[task_ingestion]
)

task_guidance = Task(
    description=(
        "Analyze only the canonical JSON outputs from the upstream tasks: IngestionToolOutput, "
        "ScreeningAggregateResponse, and RiskScoringOutput. Treat those payloads as authoritative facts. "
        "Do not recalculate scores, infer missing data, alter statuses, or downgrade blockers. "
        "Use the explicit validated payloads to synthesize a formal BDO Client Engagement Acceptance Memo "
        "in Markdown format. Save the final file."
    ),
    expected_output="A beautifully formatted Markdown audit document.",
    agent=guidance_agent,
    context=[task_ingestion, task_independence, task_risk],
    output_file="memos/memo_{target_company_safe}.md"  # Dynamic variable placeholder
)
