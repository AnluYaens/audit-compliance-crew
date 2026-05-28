from __future__ import annotations

from pathlib import Path

from schemas.evidence import AuditPlanningEvidenceBundle


def save_planning_memo(
    bundle: AuditPlanningEvidenceBundle,
    memo_content: str,
    output_dir: str = "memos",
) -> Path:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    safe_company = (
        bundle.target_company.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    output_path = Path(output_dir) / f"{safe_company}_{bundle.run_id}.md"

    output_path.write_text(memo_content, encoding="utf-8")

    return output_path