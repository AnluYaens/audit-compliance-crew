from __future__ import annotations

import json
from pathlib import Path

from schemas.evidence import AuditPlanningEvidenceBundle
from schemas.source_registry import SourceRecord, SourceRegistry


def add_source_record(
    bundle: AuditPlanningEvidenceBundle,
    source_record: SourceRecord,
) -> AuditPlanningEvidenceBundle:
    bundle.source_records.append(source_record)
    return bundle


def source_registry_from_bundle(bundle: AuditPlanningEvidenceBundle) -> SourceRegistry:
    return SourceRegistry(
        run_id=bundle.run_id,
        target_company=bundle.target_company,
        records=bundle.source_records,
    )


def save_source_registry(
    bundle: AuditPlanningEvidenceBundle,
    output_dir: str = "output/evidence/source_registry",
) -> Path:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    safe_company = (
        bundle.target_company.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    output_path = Path(output_dir) / f"{safe_company}_{bundle.run_id}_sources.json"
    registry = source_registry_from_bundle(bundle)

    output_path.write_text(
        json.dumps(registry.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    return output_path
