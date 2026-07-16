"""Span-aware and dialogue-context-aware canonical grounding.

Grounding is driven by typed role families, lexical semantic evidence and the
bounded dialogue snapshot.  It never tests language-specific surface strings.
"""
from __future__ import annotations

from contextvars import ContextVar
import hashlib
import unicodedata

from .canonical_grounding import CanonicalGroundingResolver
from .grounding import GroundedRoleBinding, ReferentGrounding


_PARTICIPANT_KEYS = {
    "pronoun:first_person": ("user", "speaker:user"),
    "determiner:first_person_possessive": ("user", "speaker:user"),
    "pronoun:second_person": ("self", "addressee:self"),
    "determiner:second_person_possessive": ("self", "addressee:self"),
}
_GRAMMATICAL_PREFIXES = (
    "grammar:", "wh:", "aux:", "polarity:",
)
_NON_VALUE_PREFIXES = (
    *_GRAMMATICAL_PREFIXES,
    "pronoun:", "determiner:", "discourse:", "anaphor:", "opaque:",
)


class ContextualGroundingResolver(CanonicalGroundingResolver):
    grounding_version = "span-context-grounding-v3.4.6"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context_snapshot_var: ContextVar[object | None] = ContextVar(
            "cemm_context_snapshot", default=None
        )

    def ground_graph(
        self,
        candidate_graph,
        surface_evidence,
        *,
        context_ref="",
        environment_fingerprint="",
        context_snapshot=None,
    ):
        token = self._context_snapshot_var.set(context_snapshot)
        try:
            return super().ground_graph(
                candidate_graph,
                surface_evidence,
                context_ref=context_ref,
                environment_fingerprint=environment_fingerprint,
                context_snapshot=context_snapshot,
            )
        finally:
            self._context_snapshot_var.reset(token)

    def _ground_binding(self, binding, evidence, context_ref=""):
        filler = binding.filler_ref
        indices = self._span_indices(filler)
        if not indices:
            return super()._ground_binding(binding, evidence, context_ref)

        try:
            tokens = tuple(evidence.token_stream.tokens[index] for index in indices)
        except IndexError:
            return GroundedRoleBinding(
                binding.role_schema_ref,
                filler,
                filler,
                confidence=0.0,
            )
        semantic_keys = tuple(dict.fromkeys(
            candidate.semantic_key
            for candidate in evidence.lexical_sense_candidates
            if set(candidate.source_token_indices) & set(indices)
            and candidate.semantic_key
        ))
        accepted = self._accepted_families(binding.role_schema_ref)
        snapshot = self._context_snapshot_var.get()

        if (
            "proposition" in accepted
            and any(key.startswith("anaphor:") for key in semantic_keys)
            and snapshot is not None
        ):
            proposition_ref = str(
                getattr(snapshot, "recent_system_proposition_ref", "")
            )
            if proposition_ref:
                grounding = ReferentGrounding(
                    referent_ref=proposition_ref,
                    referent_kind="proposition",
                    discourse_identity=f"anaphora:{proposition_ref}",
                    confidence=0.92,
                    source_token_index=indices[0],
                    surface=self._surface(tokens),
                    semantic_keys=semantic_keys,
                )
                return self._binding(binding, filler, grounding)

        participant_key = next(
            (key for key in semantic_keys if key in _PARTICIPANT_KEYS), ""
        )
        if participant_key:
            referent_ref, discourse_identity = _PARTICIPANT_KEYS[participant_key]
            grounding = ReferentGrounding(
                referent_ref=referent_ref,
                referent_kind="discourse_participant",
                discourse_identity=discourse_identity,
                confidence=1.0,
                source_token_index=indices[0],
                surface=self._surface(tokens),
                semantic_keys=(participant_key,),
            )
            return self._binding(binding, filler, grounding)

        grammatical = next(
            (
                key for key in semantic_keys
                if key.startswith(_GRAMMATICAL_PREFIXES)
            ),
            "",
        )
        if grammatical and not accepted.intersection({"value", "referent"}):
            grounding = ReferentGrounding(
                referent_ref=grammatical,
                referent_kind="grammatical_operator",
                discourse_identity=f"{grammatical}:{evidence.language_tag}",
                confidence=1.0,
                source_token_index=indices[0],
                surface=self._surface(tokens),
                semantic_keys=(grammatical,),
            )
            return self._binding(binding, filler, grounding)

        normalized = unicodedata.normalize("NFKC", self._surface(tokens)).strip()
        digest = hashlib.sha256(
            f"{evidence.language_tag}|{normalized.casefold()}".encode("utf-8")
        ).hexdigest()[:16]
        active_keys = tuple(
            key for key in semantic_keys
            if self._store.find_active(key) is not None
        )
        provisional_keys = tuple(
            key for key in semantic_keys
            if any(
                getattr(item, "status", "") == "provisional"
                for item in self._store.find_candidates(key)
            )
        )
        usable_keys = active_keys or provisional_keys
        if usable_keys:
            selected = usable_keys[0]
            grounding = ReferentGrounding(
                referent_ref=selected,
                referent_kind="schema_sense",
                discourse_identity=f"{selected}:{evidence.language_tag}",
                confidence=0.9 if active_keys else 0.62,
                is_unknown=not bool(active_keys),
                source_token_index=indices[0],
                surface=normalized,
                semantic_keys=semantic_keys,
            )
            return self._binding(binding, filler, grounding)

        semantic_value_keys = tuple(
            key for key in semantic_keys
            if key and not key.startswith(_NON_VALUE_PREFIXES)
        )
        if "value" in accepted and semantic_value_keys:
            # Lexicalized enum/property values have language-independent semantic
            # identity.  Their surfaces differ across language packs, but the
            # grounded value reference does not.
            selected = semantic_value_keys[0]
            grounding = ReferentGrounding(
                referent_ref=selected,
                referent_kind="value",
                discourse_identity=f"semantic_value:{selected}",
                confidence=0.92,
                is_unknown=False,
                source_token_index=indices[0],
                surface=normalized,
                semantic_keys=(selected,),
            )
        elif "value" in accepted:
            grounding = ReferentGrounding(
                referent_ref=f"value:text:{digest}",
                referent_kind="value",
                discourse_identity=f"value:{digest}",
                confidence=0.9,
                is_unknown=False,
                source_token_index=indices[0],
                surface=normalized,
                semantic_keys=("value:text",),
            )
        elif "referent" in accepted:
            grounding = ReferentGrounding(
                referent_ref=f"entity:mention:{digest}",
                referent_kind="entity_anchor",
                discourse_identity=f"mention:{digest}",
                confidence=0.68,
                is_unknown=False,
                source_token_index=indices[0],
                surface=normalized,
                semantic_keys=semantic_keys or ("entity:untyped",),
            )
        else:
            return super()._ground_binding(binding, evidence, context_ref)
        return self._binding(binding, filler, grounding)

    @staticmethod
    def _binding(binding, filler, grounding):
        return GroundedRoleBinding(
            binding.role_schema_ref,
            filler,
            grounding.referent_ref,
            grounding,
            min(binding.confidence, grounding.confidence),
        )

    @staticmethod
    def _span_indices(filler: str) -> tuple[int, ...]:
        if filler.startswith("ref:token:"):
            try:
                return (int(filler.rsplit(":", 1)[1]),)
            except ValueError:
                return ()
        if filler.startswith("ref:span:"):
            try:
                return tuple(
                    int(value) for value in filler.removeprefix("ref:span:").split(",")
                    if value != ""
                )
            except ValueError:
                return ()
        return ()

    @staticmethod
    def _surface(tokens) -> str:
        return " ".join(token.raw_form for token in tokens).strip()
