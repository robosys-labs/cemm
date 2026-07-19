"""Single runtime version authority for CEMM v3.5."""
from __future__ import annotations
from dataclasses import dataclass

VERSION = "3.5.0"
ARCHITECTURE_REVISION = "v3.5-learning-first-final"
SEMANTIC_AUTHORITY = "cemm.v350"
CORE_LOOP_REVISION = "stage0-22-v350-final"


@dataclass(frozen=True, slots=True)
class VersionManifest:
    version: str = VERSION
    architecture_revision: str = ARCHITECTURE_REVISION
    semantic_authority: str = SEMANTIC_AUTHORITY
    core_loop_revision: str = CORE_LOOP_REVISION
    referent_model: str = "referent-v350"
    uol_model: str = "uol-v350"
    patch_protocol: str = "graphpatch-v1"
    storage_schema: str = "sqlite-v350.8"


MANIFEST = VersionManifest()
