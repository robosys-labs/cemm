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
    """Load a compiled language pack.

    Packs are compiled by the trainer and contain all supervision data:
    source classes, forces, function forms, structured/rule/realization
    examples, operators, and roles. There is no runtime merging — the
    pack file is the single source of truth.
    """

    def __init__(self, path):
        pack_path = Path(path)
        self.path = str(pack_path)
        data = json.loads(pack_path.read_text(encoding="utf-8"))
        # Verify pack hash integrity.
        hash_material = {key: value for key, value in data.items() if key != "pack_hash"}
        computed = hashlib.sha256(canonical(hash_material).encode()).hexdigest()
        if "pack_hash" in data and data["pack_hash"] != computed:
            raise ValueError(f"pack hash mismatch in {path}: stored={data['pack_hash']} computed={computed}")
        self.data = data
        self.language = data["language"]
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
