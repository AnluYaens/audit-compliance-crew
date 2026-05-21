"""
Backward compatibility shim.

Phase 2 moved the strict Pydantic data contracts into schemas/contracts.py.
Old Phase 1 modules may still import from models.py during the migration.
"""

from schemas.contracts import *  # noqa: F403
