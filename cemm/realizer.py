"""Pointer realizer and language pack for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 271-273, 597-612).

The LanguagePack loads a JSON language definition (grammar tokens,
realization examples, pack hash). The PointerRealizer turns pointerized
semantic strings (with @A placeholders) into natural-language surface text by
invoking the SurfaceCodec and substituting preferred lexical forms for each
pointer, then verifying the result against the language pack grammar.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from cemm.store import Store
from cemm.model import norm_text, toks, surface, stable, canonical
from cemm.interpreter import SurfaceCodec
from cemm.response import pointerize_fact, pointerize_plan


class LanguagePack:
    def __init__(self, path):
        self.path = str(path)
        self.data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.language = self.data["language"]
        self.hash = self.data["pack_hash"]
        self.grammar = set(self.data.get("grammar_tokens", []))


class PointerRealizer:
    def __init__(self, s: Store, pack: LanguagePack, cache=None):
        self.s = s
        self.pack = pack
        self.codec = SurfaceCodec.get(pack, cache)

    def _render(self, semantic, ph_info):
        plan, trace = self.codec.realize(semantic)
        used = sorted(set(x for x in toks(plan) if x.startswith("@A")))
        unknown = [x for x in used if x not in ph_info]
        pointers = []
        rendered = plan
        for p in used:
            if p in ph_info:
                ref, context = ph_info[p]
                lex = self.s.preferred(ref, self.pack.language, context)
                pointers.append(
                    {
                        "placeholder": p,
                        "semantic_ref": ref,
                        "context": context,
                        "surface": lex,
                    }
                )
                rendered = rendered.replace(p, lex)
        grammar = [x.casefold() for x in toks(plan) if not x.startswith("@A")]
        badgrammar = [x for x in grammar if x not in self.pack.grammar]
        leaked = bool(
            re.search(r"\b(?:atom|existential|app|fact):[0-9a-fA-F]+", rendered)
        ) or any(x["surface"] == x["semantic_ref"] for x in pointers)
        ok = (
            trace.get("authorized_transform", False)
            and not unknown
            and not badgrammar
            and not leaked
            and bool(rendered.strip())
        )
        proof = {
            **trace,
            "verified": ok,
            "verification_mode": "semantic_pointer_provenance",
            "roundtrip_used": False,
            "pointers": pointers,
            "unknown_pointers": unknown,
            "unknown_grammar": badgrammar,
            "internal_id_leak": leaked,
            "language_pack_hash": self.pack.hash,
        }
        return surface(toks(rendered)) if ok else "", proof

    def fact(self, f):
        sem, mp = pointerize_fact(f)
        return self._render(sem, mp)

    def plan(self, plan):
        sem, mp = pointerize_plan(plan)
        return self._render(sem, mp)
