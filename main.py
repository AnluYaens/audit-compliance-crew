from crewai import Crew, Process
from agents import ingestion_agent, independence_agent, risk_agent, guidance_agent
from tasks import task_ingestion, task_independence, task_risk, task_guidance

def safe_company_filename(company_name: str) -> str:
    return company_name.lower().replace(" ", "_")

def run_compliance_pipeline(company_name: str):
    # Reunimos la tripulación modularizada
    bdo_crew = Crew(
        agents=[ingestion_agent, independence_agent, risk_agent, guidance_agent],
        tasks=[task_ingestion, task_independence, task_risk, task_guidance],
        process=Process.sequential,
        verbose=True
    )
    
    return bdo_crew.kickoff(
        inputs={
            "target_company": company_name,
            "target_company_safe": safe_company_filename(company_name),
        }
    )

if __name__ == "__main__":
    # Probemos con una de las empresas con "trampas" en la base de datos
    target = "Quantum Cybernetics"
    print(f"--- Launching Local Ollama Compliance System for: {target} ---")
    run_compliance_pipeline(target)
