"""Verified semantic-pointer realization for facts, plans, and Response CSIR."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from cemm.model import canonical, norm_text, surface, toks
from cemm.response import pointerize_fact, pointerize_plan, pointerize_response
from cemm.reference import CanonicalResponseRealizer
from cemm.surface_plans import ExactSurfacePlanIndex

_POINTER = re.compile(r"@(?:A|E|N)\d+")
_PLAN_INTERNAL_REF = re.compile(r"(?<![A-Za-z0-9_])(?:atom|app|fact|query|frontier|cycle|existential):[A-Za-z0-9_.:-]+")


class LanguagePack:
    """One self-contained immutable language artifact; no sidecar merging."""

    def __init__(self, path):
        pack_path = Path(path)
        self.path = str(pack_path)
        data = json.loads(pack_path.read_text(encoding="utf-8"))
        material = {key: value for key, value in data.items() if key != "pack_hash"}
        computed = hashlib.sha256(canonical(material).encode()).hexdigest()
        if data.get("pack_hash") != computed:
            raise ValueError(f"pack hash mismatch in {path}")
        self.data = data
        self.language = data["language"]
        self.hash = computed
        self.grammar = set(data.get("grammar_tokens", []))
        self.function_forms = set(data.get("function_forms", []))


class PointerRealizer:
    def __init__(self, store, pack: LanguagePack, cache=None):
        if cache is None:
            raise ValueError("PointerRealizer requires Runtime-owned bounded cache")
        self.s = store
        self.pack = pack
        self.codec = ExactSurfacePlanIndex(pack, "realization_examples")
        self.response_codec = ExactSurfacePlanIndex(pack, "response_examples")
        self.canonical_response = CanonicalResponseRealizer(store, pack)

    def _verify_and_substitute(self, plan, trace, placeholder_info):
        used = sorted(set(_POINTER.findall(plan)), key=lambda item: (-len(item), item))
        unknown = [token for token in used if token not in placeholder_info]
        rendered = plan
        pointers = []
        for placeholder in used:
            raw_info = placeholder_info.get(placeholder)
            if not raw_info:
                continue
            info = (
                {"kind": "atom", "value": raw_info[0], "context": raw_info[1]}
                if isinstance(raw_info, tuple)
                else dict(raw_info)
            )
            kind = info["kind"]
            value = info["value"]
            if kind == "atom":
                lexical = self.s.preferred(
                    value, self.pack.language, info.get("context")
                )
                if lexical == value:
                    lexical = ""
            elif kind in {"evidence", "number"}:
                lexical = str(value)
            else:
                lexical = ""
            pointers.append(
                {
                    "placeholder": placeholder,
                    "kind": kind,
                    "semantic_ref": value if kind == "atom" else None,
                    "evidence_value": value if kind != "atom" else None,
                    "surface": lexical,
                    "context": info.get("context"),
                    "literal_type": info.get("literal_type"),
                }
            )
            rendered = re.sub(
                rf"(?<![A-Za-z0-9_]){re.escape(placeholder)}(?!\d)",
                lambda _match, value=lexical: value,
                rendered,
            )
        grammar = [
            token.casefold()
            for token in toks(plan)
            if not token.startswith(("@A", "@E", "@N"))
        ]
        bad_grammar = []
        for token in grammar:
            if token in self.pack.grammar:
                continue
            core = token.strip(".,!?;:")
            punctuation = token[len(core) :] if token.startswith(core) else ""
            if core and core in self.pack.grammar and all(
                char in self.pack.grammar for char in punctuation
            ):
                continue
            bad_grammar.append(token)
        # Only reviewed plan text is inspected for raw internal refs. Substituted
        # evidence may legitimately contain colons (URLs, times, identifiers).
        leaked = bool(_PLAN_INTERNAL_REF.search(plan))
        leaked = leaked or any(
            item["kind"] == "atom" and not item["surface"] for item in pointers
        )
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
        normalized = {}
        for placeholder, value in placeholder_info.items():
            if isinstance(value, tuple):
                normalized[placeholder] = {
                    "kind": "atom",
                    "value": value[0],
                    "context": value[1],
                }
            else:
                normalized[placeholder] = dict(value)
        return self._verify_and_substitute(plan, trace, normalized)

    def fact(self, fact):
        semantic, mapping = pointerize_fact(fact)
        return self._render(semantic, mapping)

    def plan(self, plan):
        semantic, mapping = pointerize_plan(plan)
        return self._render(semantic, mapping)

    def response(self, response_csir, output_frame=None):
        """Realize one Response CSIR without permitting semantic downgrade.

        The grammar realization is the semantic authority because it emits an
        explicit ResponseEquivalenceReceipt for the exact CSIR.  An exact learned
        surface plan may be selected only when it independently verifies and is
        byte-for-byte the same normalized surface as that equivalent grammar
        realization.  A learned plan therefore cannot replace a query answer with
        a supporting fact or otherwise change action, target, obligation, query
        kind, polarity, modality, or payload.
        """
        if output_frame is None:
            return "", {
                "verified": False,
                "verification_mode": "no_semantic_equivalent_response",
                "reason": "output_participant_frame_required",
                "response_ref": response_csir.response_ref,
            }

        canonical_surface, canonical_proof = self.canonical_response.realize(
            response_csir, output_frame
        )
        if not canonical_surface or not canonical_proof.get("verified"):
            return "", {
                **canonical_proof,
                "verified": False,
                "verification_mode": "no_semantic_equivalent_response",
                "response_ref": response_csir.response_ref,
            }

        semantic, mapping = pointerize_response(response_csir)
        plan, learned_trace = self.response_codec.realize(semantic)
        learned_surface, learned_proof = self._verify_and_substitute(
            plan, learned_trace, mapping
        )
        learned_matches_authority = bool(
            learned_surface
            and learned_proof.get("verified")
            and learned_surface == canonical_surface
        )
        if learned_matches_authority:
            return learned_surface, {
                **canonical_proof,
                "verified": True,
                "verification_mode": "exact_learned_surface_confirmed_by_same_csir_grammar",
                "response_ref": response_csir.response_ref,
                "learned_transform": learned_proof,
                "canonical_surface": canonical_surface,
            }

        return canonical_surface, {
            **canonical_proof,
            "verified": True,
            "verification_mode": "same_response_csir_grammar",
            "response_ref": response_csir.response_ref,
            "rejected_learned_transform": {
                **learned_proof,
                "surface_equal_to_canonical": learned_surface == canonical_surface,
            },
        }
