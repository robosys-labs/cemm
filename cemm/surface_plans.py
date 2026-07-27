"""Immutable exact semantic-signature surface-plan indexes.

This index is deliberately incapable of similarity search or runtime learning.
Every accepted transform is tied to one case-sensitive semantic signature and
one deterministic plan fingerprint from the pinned language artifact.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping


def exact_signature(value: Any) -> str:
    # Structural semantic signatures are case-sensitive. Only transport
    # whitespace is canonicalized; no case folding or lexical normalization.
    return " ".join(str(value).split())


def _fingerprint(example_key: str, semantic: str, plan: str) -> str:
    material = f"{example_key}\0{semantic}\0{plan}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class ExactSurfacePlanIndex:
    def __init__(self, pack, example_key: str):
        self.example_key = str(example_key)
        if not self.example_key:
            raise ValueError("surface plan index requires an example key")
        grouped: dict[str, dict[str, Mapping[str, str]]] = {}
        examples = pack.data.get(self.example_key, ())
        if not isinstance(examples, list):
            raise ValueError(f"{self.example_key} must be a list")
        for index, example in enumerate(examples):
            if not isinstance(example, Mapping):
                raise ValueError(f"{self.example_key}[{index}] is not an object")
            semantic = exact_signature(example.get("semantic", ""))
            plan = str(example.get("surface_plan", "")).strip()
            if not semantic or not plan:
                raise ValueError(
                    f"{self.example_key}[{index}] requires semantic and surface_plan"
                )
            fingerprint = _fingerprint(self.example_key, semantic, plan)
            grouped.setdefault(semantic, {})[fingerprint] = {
                "plan": plan,
                "fingerprint": fingerprint,
            }
        conflicts = {
            key: tuple(sorted(item["plan"] for item in values.values()))
            for key, values in grouped.items()
            if len(values) > 1
        }
        if conflicts:
            raise ValueError(
                "conflicting exact surface supervision: "
                + "; ".join(
                    f"{key} -> {list(values)}"
                    for key, values in sorted(conflicts.items())
                )
            )
        self.plans = {
            key: next(iter(values.values())) for key, values in grouped.items()
        }

    def realize(self, semantic):
        key = exact_signature(semantic)
        record = self.plans.get(key)
        if record is None:
            return "", {
                "semantic": semantic,
                "surface_plan": "",
                "authorized_transform": False,
                "reason": "no_exact_reviewed_surface_plan",
                "example_key": self.example_key,
                "signature": key,
            }
        return record["plan"], {
            "semantic": semantic,
            "surface_plan": record["plan"],
            "authorized_transform": True,
            "selection": "exact_case_sensitive_semantic_signature",
            "alternative_count": 1,
            "example_key": self.example_key,
            "signature": key,
            "plan_fingerprint": record["fingerprint"],
        }
