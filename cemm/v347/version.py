"""Single runtime version authority for CEMM v3.4.7."""
from __future__ import annotations
from dataclasses import dataclass

VERSION = "3.4.7"
ARCHITECTURE_REVISION = "v3.4.7-final-completion"
SEMANTIC_AUTHORITY = "cemm.v347"


@dataclass(frozen=True, slots=True)
class VersionManifest:
    version: str = VERSION
    architecture_revision: str = ARCHITECTURE_REVISION
    semantic_authority: str = SEMANTIC_AUTHORITY
    referent_model: str = "referent-v1"
    uol_model: str = "uol-v347.2"
    patch_protocol: str = "graphpatch-v1"
    storage_schema: str = "sqlite-v347.2"


MANIFEST = VersionManifest()
