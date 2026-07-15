"""Grounding resolver that preserves query ports without treating them as gaps."""
from __future__ import annotations

from .grounding import (
    DefinitionGrounding,
    GraphGrounding,
    GroundedRoleBinding,
    GroundingResolver,
    PredicationGrounding,
    ReferentGrounding,
)
from ..schema.use_profile import UseProfileLevel


class CanonicalGroundingResolver(GroundingResolver):

    def _ground_binding(self, binding, evidence):
        filler = binding.filler_ref
        if not filler.startswith("ref:token:"):
            return super()._ground_binding(binding, evidence)
        try:
            index = int(filler.rsplit(":", 1)[1])
            token = evidence.token_stream.tokens[index]
        except (ValueError, IndexError):
            return super()._ground_binding(binding, evidence)

        semantic_keys = tuple(dict.fromkeys(
            candidate.semantic_key
            for candidate in evidence.lexical_sense_candidates
            if index in candidate.source_token_indices
            and candidate.semantic_key
        ))
        participant = {
            "pronoun:first_person": ("user", "speaker:user"),
            "pronoun:second_person": ("self", "addressee:self"),
        }
        for key in semantic_keys:
            if key in participant:
                referent_ref, discourse_identity = participant[key]
                grounding = ReferentGrounding(
                    referent_ref=referent_ref,
                    referent_kind="discourse_participant",
                    discourse_identity=discourse_identity,
                    confidence=1.0,
                    source_token_index=index,
                    surface=token.raw_form,
                    semantic_keys=(key,),
                )
                return GroundedRoleBinding(
                    role_schema_ref=binding.role_schema_ref,
                    original_filler_ref=filler,
                    grounded_filler_ref=referent_ref,
                    grounding=grounding,
                    confidence=min(binding.confidence, 1.0),
                )

        grammatical = next(
            (key for key in semantic_keys if key.startswith(("grammar:", "wh:"))),
            "",
        )
        if grammatical:
            grounding = ReferentGrounding(
                referent_ref=grammatical,
                referent_kind="grammatical_operator",
                discourse_identity=f"{grammatical}:{evidence.language_tag}",
                confidence=1.0,
                source_token_index=index,
                surface=token.raw_form,
                semantic_keys=(grammatical,),
            )
            return GroundedRoleBinding(
                role_schema_ref=binding.role_schema_ref,
                original_filler_ref=filler,
                grounded_filler_ref=grounding.referent_ref,
                grounding=grounding,
                confidence=min(binding.confidence, 1.0),
            )

        active_key = next(
            (key for key in semantic_keys if self._store.find_active(key) is not None),
            "",
        )
        if active_key:
            grounding = ReferentGrounding(
                referent_ref=f"ref:schema:{active_key}",
                referent_kind="schema_sense",
                discourse_identity=f"{active_key}:{evidence.language_tag}",
                confidence=0.9,
                source_token_index=index,
                surface=token.raw_form,
                semantic_keys=semantic_keys,
            )
            return GroundedRoleBinding(
                role_schema_ref=binding.role_schema_ref,
                original_filler_ref=filler,
                grounded_filler_ref=grounding.referent_ref,
                grounding=grounding,
                confidence=min(binding.confidence, 0.9),
            )
        return super()._ground_binding(binding, evidence)
    def ground_graph(
        self,
        candidate_graph,
        surface_evidence,
        *,
        context_ref: str = "",
        environment_fingerprint: str = "",
    ) -> GraphGrounding:
        referents = []
        definitions = []
        predications = []

        for candidate in candidate_graph.candidate_predications:
            predication = candidate.predication
            envelope = self._resolve_envelope(predication.predicate_schema_ref)
            if envelope is None:
                definition = DefinitionGrounding(
                    schema_record_ref=predication.predicate_schema_ref,
                    semantic_key=predication.predicate_schema_ref,
                    blockers=("predicate schema unresolved",),
                    use_profile=self._opaque_profile(
                        predication.predicate_schema_ref,
                        context_ref,
                        "predicate schema unresolved",
                    ),
                )
            else:
                definition = self._definition_from_envelope(
                    envelope,
                    context_ref,
                    environment_fingerprint,
                )
            definitions.append(definition)

            grounded_roles = []
            opaque_roles = []
            for binding in predication.bindings:
                grounded = self._ground_binding(binding, surface_evidence)
                grounded_roles.append(grounded)
                if grounded.grounding is not None:
                    referents.append(grounded.grounding)
                    if grounded.grounding.is_unknown:
                        opaque_roles.append(binding.role_schema_ref)

            unresolved = tuple(
                port.role_schema_ref
                for port in predication.open_ports
                if port.required
            )
            query_ports = tuple(
                port.role_schema_ref
                for port in predication.open_ports
                if not port.required
            )
            query_roles = tuple(dict.fromkeys((
                *self._query_role_refs(envelope),
                *query_ports,
            )))
            use_profile = definition.use_profile
            structurally_usable = bool(
                use_profile is not None
                and use_profile.level is not UseProfileLevel.INADMISSIBLE
            )
            limitations = list(definition.blockers)
            if unresolved:
                limitations.append(
                    f"unresolved roles: {', '.join(unresolved)}"
                )
            if opaque_roles:
                limitations.append(
                    f"opaque role fillers: {', '.join(opaque_roles)}"
                )

            predications.append(PredicationGrounding(
                predication_ref=predication.id,
                predicate_schema_ref=predication.predicate_schema_ref,
                predicate_semantic_key=(
                    getattr(envelope, "semantic_key", "")
                    if envelope is not None
                    else predication.predicate_schema_ref
                ),
                definition=definition,
                role_bindings=tuple(grounded_roles),
                unresolved_role_refs=unresolved,
                query_role_refs=query_roles,
                opaque_role_refs=tuple(dict.fromkeys(opaque_roles)),
                use_profile=use_profile,
                is_structurally_usable=structurally_usable,
                limitations=tuple(limitations),
            ))

        return GraphGrounding(
            predications=tuple(predications),
            referents=tuple(self._dedupe_referents(referents)),
            definition_groundings=tuple(definitions),
            opaque_lexeme_refs=tuple(candidate_graph.opaque_lexeme_refs),
        )
