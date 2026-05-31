import json
from pathlib import Path

from schemas.evidence import AuditPlanningEvidenceBundle


def save_evidence_bundle(
    bundle: AuditPlanningEvidenceBundle,
    output_dir: str = "output/evidence",
) -> Path:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    safe_company = (
        bundle.target_company.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    output_path = Path(output_dir) / f"{safe_company}_{bundle.run_id}.json"

    output_path.write_text(
        json.dumps(bundle.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    return output_path


def load_evidence_bundle(path: str | Path) -> AuditPlanningEvidenceBundle:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return AuditPlanningEvidenceBundle.model_validate(payload)
