"""Canonical data-only v3.4.3 boot loader."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..schema.foundation_contract import FoundationRegistry
from ..self_model.claim_authorizer import SelfClaimAuthorizer
from ...language.semantic_pack import SemanticLanguagePack


@dataclass(frozen=True, slots=True)
class V343BootPackage:
    foundations: FoundationRegistry
    self_claim_authorizer: SelfClaimAuthorizer
    language_packs: dict[str, SemanticLanguagePack]
    fingerprint: str


def load_v343_package(data_root: Path) -> V343BootPackage:
    foundation_root = data_root / "foundations" / "v343"
    foundations = FoundationRegistry.load(foundation_root)
    foundation_failures = foundations.validate()
    if foundation_failures:
        raise RuntimeError(
            "foundation_validation_failed:" + ";".join(foundation_failures)
        )

    self_claims = SelfClaimAuthorizer.load(
        foundation_root / "self_claim_policies.json"
    )
    packs: dict[str, SemanticLanguagePack] = {}
    language_root = data_root / "languages"
    for path in sorted(language_root.glob("*/v343")):
        pack = SemanticLanguagePack.load(path)
        packs[pack.language_tag] = pack

    if len(packs) < 2:
        raise RuntimeError("multilingual_boot_requires_at_least_two_language_packs")

    fingerprint = (
        f"foundations={foundations.fingerprint};"
        + ";".join(
            f"{tag}={pack.fingerprint}"
            for tag, pack in sorted(packs.items())
        )
    )
    return V343BootPackage(
        foundations=foundations,
        self_claim_authorizer=self_claims,
        language_packs=packs,
        fingerprint=fingerprint,
    )
