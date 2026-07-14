from __future__ import annotations

import math
import re

from schemas.client_artifacts import ClientArtifactProvenanceReference
from schemas.sandbox_verifier import (
    SafePublicSearchHintCandidate,
    SafePublicSearchHintSensitivity,
    SafePublicSearchHintType,
    SandboxVerifierOutput,
    SandboxVerifierStatus,
)


SAFE_PUBLIC_SEARCH_HINT_MIN_CONFIDENCE = 0.75

ALLOWED_SAFE_PUBLIC_SEARCH_HINT_TYPES = frozenset(SafePublicSearchHintType)

_UNSAFE_MARKERS = (
    "confidential",
    "restricted",
    "internal only",
    "internalonly",
    "raw client",
    "client artifact",
    "private",
    "secret",
    "password",
    "token",
    "api key",
    "apikey",
    "credential",
)


def _normalized_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _contains_unsafe_marker(values: tuple[str | None, ...]) -> bool:
    return any(
        marker in _normalized_text(value)
        for value in values
        if isinstance(value, str)
        for marker in _UNSAFE_MARKERS
    )


def _provenance_text_values(
    provenance: ClientArtifactProvenanceReference,
) -> tuple[str | None, ...]:
    return (
        provenance.source_id,
        provenance.file_name,
        provenance.sheet_name,
        provenance.column_name,
        provenance.text_chunk_id,
        provenance.field_path,
    )


def _is_safe_candidate(candidate: object) -> bool:
    if not isinstance(candidate, SafePublicSearchHintCandidate):
        return False

    try:
        sensitivity = candidate.sensitivity
        hint_type = candidate.hint_type
        confidence = candidate.confidence
        review_recommended = candidate.human_review_recommended
        public_text_values = (
            candidate.hint_id,
            candidate.hint_text,
            candidate.safe_reason,
        )
        provenance = candidate.provenance
    except AttributeError:
        return False

    if not isinstance(sensitivity, SafePublicSearchHintSensitivity):
        return False
    if sensitivity not in {
        SafePublicSearchHintSensitivity.PUBLIC,
        SafePublicSearchHintSensitivity.NON_SENSITIVE,
    }:
        return False
    if not isinstance(hint_type, SafePublicSearchHintType):
        return False
    if hint_type not in ALLOWED_SAFE_PUBLIC_SEARCH_HINT_TYPES:
        return False
    if review_recommended is not False:
        return False
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return False
    if not math.isfinite(confidence) or confidence < SAFE_PUBLIC_SEARCH_HINT_MIN_CONFIDENCE:
        return False
    if any(not isinstance(value, str) or not value.strip() for value in public_text_values):
        return False
    if _contains_unsafe_marker(public_text_values):
        return False

    if provenance is not None:
        if not isinstance(provenance, ClientArtifactProvenanceReference):
            return False
        if _contains_unsafe_marker(_provenance_text_values(provenance)):
            return False

    return True


def filter_safe_public_search_hints(
    output: SandboxVerifierOutput,
) -> list[SafePublicSearchHintCandidate]:
    """Return fresh public-safe hints from a successful verifier output."""
    if not isinstance(output, SandboxVerifierOutput):
        return []

    try:
        if not isinstance(output.verifier_status, SandboxVerifierStatus):
            return []
        if output.verifier_status is not SandboxVerifierStatus.SUCCESS:
            return []
        if output.human_review_required:
            return []
        candidates = output.safe_public_search_hint_candidates
    except (AttributeError, TypeError, ValueError):
        return []

    if not isinstance(candidates, list):
        return []

    return [
        SafePublicSearchHintCandidate(
            hint_id=candidate.hint_id,
            hint_text=candidate.hint_text,
            hint_type=candidate.hint_type,
            safe_reason=candidate.safe_reason,
            sensitivity=candidate.sensitivity,
            provenance=None,
            confidence=candidate.confidence,
            human_review_recommended=False,
        )
        for candidate in candidates
        if _is_safe_candidate(candidate)
    ]
