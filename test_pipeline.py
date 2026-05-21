import os
from crewai import Crew, Process
from agents import ingestion_agent, independence_agent, risk_agent, guidance_agent
from tasks import task_ingestion, task_independence, task_risk, task_guidance

# Definimos el banco de pruebas con los resultados esperados (Trampas)
TEST_CASES = [
    {
        "company": "Quantum Cybernetics",
        "expected_flag": "CONFLICTO DE INDEPENDENCIA (Socio Sarah Jenkins posee acciones)"
    },
    {
        "company": "Vanguard Mining Corp",
        "expected_flag": "SANCIÓN CRÍTICA (CEO Dimitri Volkov en lista negra)"
    },
    {
        "company": "Apex Energy Group",
        "expected_flag": "ALTO RIESGO MATEMÁTICO (Operaciones en Irak/Libya + Baja estabilidad)"
    },
    {
        "company": "GreenLeaf Organics",
        "expected_flag": "APROBACIÓN LIMPIA o RIESGO BAJO/MODERADO"
    }
]

def safe_company_filename(company_name: str) -> str:
    return company_name.lower().replace(" ", "_")

def run_automated_test_suite():
    # Creamos la carpeta de reportes si no existe
    os.makedirs("memos", exist_ok=True)
    
    print("=" * 60)
    print("INICIANDO SUITE DE PRUEBAS AUTOMATIZADAS - BDO COMPLIANCE")
    print("=" * 60)
    
    for case in TEST_CASES:
        target = case["company"]
        print(f"\n[TEST] Evaluando: {target}")
        print(f"[Esperado]: {case['expected_flag']}")
        print("-" * 40)
        
        safe_filename = safe_company_filename(target)
        
        # Inicializamos la tripulación para este caso específico
        crew = Crew(
            agents=[ingestion_agent, independence_agent, risk_agent, guidance_agent],
            tasks=[task_ingestion, task_independence, task_risk, task_guidance],
            process=Process.sequential,
            verbose=True
        )
        
        # Ejecutamos el pipeline
        try:
            crew.kickoff(inputs={"target_company": target, "target_company_safe": safe_filename})
            print(f"[OK] Pipeline completado para {target}. Reporte guardado en: memos/memo_{safe_filename}.md")
        except Exception as e:
            print(f"[ERROR] Falló la ejecución para {target}: {str(e)}")
            
    print("\n" + "=" * 60)
    print("SUITE DE PRUEBAS FINALIZADA. Revisa la carpeta '/memos' para ver los resultados.")
    print("=" * 60)

if __name__ == "__main__":
    run_automated_test_suite()
