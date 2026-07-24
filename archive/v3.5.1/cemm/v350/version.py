"""Single active runtime-version authority for CEMM v3.5.1."""
from __future__ import annotations

from dataclasses import dataclass

VERSION = "3.5.1"
ARCHITECTURE_REVISION = "v3.5.1-grounded-recurrent-semantic-dynamics"
SEMANTIC_AUTHORITY = "cemm.v350"
CORE_LOOP_REVISION = "stage0-22-v351-csir-recurrent"


@dataclass(frozen=True, slots=True)
class VersionManifest:
    version: str = VERSION
    architecture_revision: str = ARCHITECTURE_REVISION
    semantic_authority: str = SEMANTIC_AUTHORITY
    core_loop_revision: str = CORE_LOOP_REVISION
    referent_model: str = "referent-v351-grounded"
    semantic_ir_model: str = "csir-v2"
    dynamics_model: str = "typed-recurrent-attractor-v351"
    patch_protocol: str = "graphpatch-v1"
    storage_schema: str = "sqlite-v351.9"


MANIFEST = VersionManifest()
