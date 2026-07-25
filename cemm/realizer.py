"""Pointer realizer and mergeable language package for CEMM v1."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from cemm.model import canonical, norm_text, surface, toks
from cemm.interpreter import SurfaceCodec
from cemm.response import pointerize_fact, pointerize_plan


class LanguagePack:
    """Load a generated base pack plus an optional reviewed v1 extension.

    Sidecar extensions keep architectural supervision reviewable without
    hand-editing generated packs or branching on a language inside the kernel.
    """

    _LIST_KEYS = {
        "source_classes",
        "rule_sources",
        "operators",
        "roles",
        "forces",
        "structured_examples",
        "rule_examples",
        "realization_examples",
        "grammar_tokens",
        "function_forms",
    }

    def __init__(self, path):
        pack_path = Path(path)
        self.path = str(pack_path)
        base = json.loads(pack_path.read_text(encoding="utf-8"))
        data = dict(base)
        extension_path = pack_path.with_name(f"{pack_path.stem}.v1.json")
        self.extension_path = str(extension_path) if extension_path.exists() else None
        if extension_path.exists():
            extension = json.loads(extension_path.read_text(encoding="utf-8"))
            if extension.get("language") != base.get("language"):
                raise ValueError("language extension does not match base pack")
            for key, value in extension.items():
                if key in {"language", "version", "pack_hash"}:
                    continue
                if key in self._LIST_KEYS:
                    merged = list(data.get(key, []))
                    if key.endswith("_examples"):
                        by_ref = {item.get("example_ref"): item for item in merged}
                        for item in value:
                            by_ref[item.get("example_ref")] = item
                        merged = list(by_ref.values())
                    else:
                        for item in value:
                            if item not in merged:
                                merged.append(item)
                    data[key] = merged
                else:
                    data[key] = value
            data["version"] = max(int(base.get("version", 0)), int(extension.get("version", 0)))
        # The merged package is the actual pinned projection authority.
        hash_material = {key: value for key, value in data.items() if key != "pack_hash"}
        data["pack_hash"] = hashlib.sha256(canonical(hash_material).encode()).hexdigest()
        self.data = data
        self.language = data["language"]
        self.base_hash = base.get("pack_hash")
        self.hash = data["pack_hash"]
        self.grammar = set(data.get("grammar_tokens", []))
        self.function_forms = set(data.get("function_forms", []))


class PointerRealizer:
    def __init__(self, store, pack: LanguagePack, cache=None):
        self.s = store
        self.pack = pack
        self.codec = SurfaceCodec.get(pack, cache)

    def _render(self, semantic, placeholder_info):
        plan, trace = self.codec.realize(semantic)
        used = sorted(set(token for token in toks(plan) if token.startswith("@A")))
        unknown = [token for token in used if token not in placeholder_info]
        pointers = []
        rendered = plan
        for placeholder in used:
            if placeholder not in placeholder_info:
                continue
            ref, context = placeholder_info[placeholder]
            lexical = self.s.preferred(ref, self.pack.language, context)
            pointers.append(
                {
                    "placeholder": placeholder,
                    "semantic_ref": ref,
                    "context": context,
                    "surface": lexical,
                }
            )
            rendered = rendered.replace(placeholder, lexical)
        grammar = [token.casefold() for token in toks(plan) if not token.startswith("@A")]
        bad_grammar = [token for token in grammar if token not in self.pack.grammar]
        leaked = bool(re.search(r"\b(?:atom|existential|app|fact):[0-9a-fA-F]+", rendered)) or any(
            item["surface"] == item["semantic_ref"] for item in pointers
        )
        verified = (
            trace.get("authorized_transform", False)
            and not unknown
            and not bad_grammar
            and not leaked
            and bool(rendered.strip())
        )
        proof = {
            **trace,
            "verified": verified,
            "verification_mode": "semantic_pointer_provenance",
            "roundtrip_used": False,
            "pointers": pointers,
            "unknown_pointers": unknown,
            "unknown_grammar": bad_grammar,
            "internal_id_leak": leaked,
            "language_pack_hash": self.pack.hash,
        }
        return surface(toks(rendered)) if verified else "", proof

    def fact(self, fact):
        semantic, mapping = pointerize_fact(fact)
        return self._render(semantic, mapping)

    def plan(self, plan):
        semantic, mapping = pointerize_plan(plan)
        return self._render(semantic, mapping)
