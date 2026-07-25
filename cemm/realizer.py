"""Verified semantic-pointer realization for facts, plans, and Response CSIR."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from cemm.interpreter import SurfaceCodec, predict_classifier, train_classifier
from cemm.model import canonical, norm_text, surface, toks
from cemm.response import pointerize_fact, pointerize_plan, pointerize_response


class LanguagePack:
    """One self-contained immutable language artifact; no sidecar merging."""

    def __init__(self, path):
        pack_path = Path(path)
        self.path = str(pack_path)
        data = json.loads(pack_path.read_text(encoding="utf-8"))
        hash_material = {key: value for key, value in data.items() if key != "pack_hash"}
        computed = hashlib.sha256(canonical(hash_material).encode()).hexdigest()
        if data.get("pack_hash") != computed:
            raise ValueError(f"pack hash mismatch in {path}")
        self.data = data
        self.language = data["language"]
        self.hash = computed
        self.grammar = set(data.get("grammar_tokens", []))
        self.function_forms = set(data.get("function_forms", []))


class ResponseSurfaceCodec:
    def __init__(self, pack, cache):
        examples = list(pack.data.get("response_examples", ()))
        if not examples:
            self.meta = self.net = None
            self.allowed = {}
            return
        key = (pack.hash, "response-surface-v1")
        cached = cache.get(key) if cache else None
        if cached is not None:
            self.meta, self.net, self.allowed = cached
            return
        self.meta, self.net = train_classifier(examples, "semantic", "surface_plan", 29, 120)
        self.allowed = {}
        for example in examples:
            self.allowed.setdefault(norm_text(example["semantic"]), set()).add(norm_text(example["surface_plan"]))
        if cache:
            cache.put(key, (self.meta, self.net, self.allowed))

    def realize(self, semantic):
        if self.net is None:
            return "", {"authorized_transform": False, "reason": "no_response_examples"}
        plan, confidence, margin, known = predict_classifier(self.meta, self.net, semantic)
        return plan, {
            "semantic": semantic,
            "surface_plan": plan,
            "confidence": confidence,
            "margin": margin,
            "known_token_ratio": known,
            "authorized_transform": norm_text(plan) in self.allowed.get(norm_text(semantic), set()),
        }


class PointerRealizer:
    def __init__(self, store, pack: LanguagePack, cache=None):
        if cache is None:
            raise ValueError("PointerRealizer requires Runtime-owned bounded cache")
        self.s = store
        self.pack = pack
        self.codec = SurfaceCodec.get(pack, cache)
        self.response_codec = ResponseSurfaceCodec(pack, cache)

    def _verify_and_substitute(self, plan, trace, placeholder_info):
        used = sorted(set(token for token in toks(plan) if token.startswith(("@A", "@E", "@N"))))
        unknown = [token for token in used if token not in placeholder_info]
        rendered = plan
        pointers = []
        for placeholder in used:
            info = placeholder_info.get(placeholder)
            if not info:
                continue
            if isinstance(info, tuple):
                info = {"kind": "atom", "value": info[0], "context": info[1]}
            kind = info["kind"]
            value = info["value"]
            if kind == "atom":
                lexical = self.s.preferred(value, self.pack.language, info.get("context"))
                if lexical == value:
                    lexical = ""
            elif kind == "evidence":
                lexical = str(value)
            elif kind == "number":
                lexical = str(value)
            else:
                lexical = ""
            pointers.append({
                "placeholder": placeholder,
                "kind": kind,
                "semantic_ref": value if kind == "atom" else None,
                "evidence_value": value if kind != "atom" else None,
                "surface": lexical,
            })
            rendered = rendered.replace(placeholder, lexical)
        grammar = [token.casefold() for token in toks(plan) if not token.startswith(("@A", "@E", "@N"))]
        bad_grammar = []
        for token in grammar:
            if token in self.pack.grammar:
                continue
            core = token.strip(".,!?;:")
            punctuation = token[len(core):] if token.startswith(core) else ""
            if core and core in self.pack.grammar and all(char in self.pack.grammar for char in punctuation):
                continue
            bad_grammar.append(token)
        leaked = bool(re.search(r"\b(?:atom|existential|app|fact|query|frontier|cycle):[0-9a-fA-F]{8,}\b", rendered))
        leaked = leaked or any(item["kind"] == "atom" and not item["surface"] for item in pointers)
        verified = bool(
            trace.get("authorized_transform", False)
            and not unknown
            and not bad_grammar
            and not leaked
            and rendered.strip()
        )
        proof = {
            **trace,
            "verified": verified,
            "verification_mode": "semantic_or_evidence_pointer_provenance",
            "roundtrip_used": False,
            "pointers": pointers,
            "unknown_pointers": unknown,
            "unknown_grammar": bad_grammar,
            "internal_id_leak": leaked,
            "language_pack_hash": self.pack.hash,
        }
        return surface(toks(rendered)) if verified else "", proof

    def _render(self, semantic, placeholder_info):
        plan, trace = self.codec.realize(semantic)
        normalized = {
            placeholder: {"kind": "atom", "value": value[0], "context": value[1]}
            for placeholder, value in placeholder_info.items()
        }
        return self._verify_and_substitute(plan, trace, normalized)

    def fact(self, fact):
        semantic, mapping = pointerize_fact(fact)
        return self._render(semantic, mapping)

    def plan(self, plan):
        semantic, mapping = pointerize_plan(plan)
        return self._render(semantic, mapping)

    def response(self, response_csir):
        # Proof-bearing facts are the most specific learned realization path.
        outputs, proofs = [], []
        for fact in response_csir.facts[:5]:
            text, proof = self.fact(fact)
            if text:
                outputs.append(text); proofs.append(proof)
        if outputs and response_csir.action in {"answer_bindings"}:
            return " ".join(outputs), {
                "verified": all(item.get("verified") for item in proofs),
                "verification_mode": "response_fact_provenance",
                "fact_proofs": proofs,
                "language_pack_hash": self.pack.hash,
            }
        semantic, mapping = pointerize_response(response_csir)
        plan, trace = self.response_codec.realize(semantic)
        return self._verify_and_substitute(plan, trace, mapping)
