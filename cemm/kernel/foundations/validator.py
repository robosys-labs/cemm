"""Cross-package semantic foundation validation."""
from __future__ import annotations

import json
from pathlib import Path

from ..boot.v343 import load_v343_package


FORBIDDEN_DOMAIN_KEYS = frozenset({
    "machine",
    "leader",
    "president",
    "engineer",
    "mother_in_law",
    "wife",
    "husband",
})


def validate_data_root(data_root: Path) -> tuple[str, ...]:
    failures: list[str] = []
    package = load_v343_package(data_root)

    foundation_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (data_root / "foundations" / "v343").glob("*.json")
    )
    for key in FORBIDDEN_DOMAIN_KEYS:
        if f'"{key}"' in foundation_text:
            failures.append(f"domain_concept_in_foundations:{key}")

    predicate_keys = {
        item["semantic_key"]
        for item in json.loads(
            (
                data_root
                / "foundations"
                / "v343"
                / "predicates.json"
            ).read_text(encoding="utf-8")
        )
    }
    policies = json.loads(
        (
            data_root
            / "foundations"
            / "v343"
            / "self_claim_policies.json"
        ).read_text(encoding="utf-8")
    )
    for policy in policies:
        if policy["predicate_key"] not in predicate_keys:
            failures.append(
                f"self_claim_policy_missing_predicate:{policy['predicate_key']}"
            )

    for tag, semantic_pack in package.language_packs.items():
        for mapping in semantic_pack.input_lexicon:
            if mapping.semantic_key in FORBIDDEN_DOMAIN_KEYS:
                failures.append(f"domain_seed_in_language_pack:{tag}:{mapping.semantic_key}")
        failures.extend(
            f"{tag}:{failure}"
            for failure in semantic_pack.validate()
        )
    return tuple(failures)
