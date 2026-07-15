"""GroundingResolver — referent, definition, role, and predication grounding."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..model.identity import Scope
from ..model.role_binding import RoleBinding
from ..schema.closure import GroundedDefinitionClosure, SchemaGroundingAssessment
from ..schema.competence import CompetenceAssessment, CompetenceHarness
from ..schema.grounding_spec import GroundingSpecification, SemanticPattern
from ..schema.provenance import FieldProvenanceMap
from ..schema.resolver import SchemaResolver
from ..schema.store import SemanticSchemaStore
from ..schema.use_profile import (
    ACTIVE_OPERATIONS,
    OPAQUE_OPERATIONS,
    PARTIAL_OPERATIONS,
    SchemaUseProfile,
    UseProfileLevel,
    derive_use_profile,
)
from ...language.interfaces import SurfaceEvidence


@dataclass(frozen=True, slots=True)
class ReferentGrounding:
    referent_ref: str = ""
    referent_kind: str = ""
    discourse_identity: str = ""
    confidence: float = 0.0
    is_unknown: bool = False
    source_token_index: int | None = None
    surface: str = ""
    semantic_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DefinitionGrounding:
    schema_record_ref: str = ""
    semantic_key: str = ""
    semantic_family: str = ""
    assessment: SchemaGroundingAssessment | None = None
    use_profile: SchemaUseProfile | None = None
    competence: CompetenceAssessment | None = None
    is_grounded: bool = False
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GroundedRoleBinding:
    role_schema_ref: str
    original_filler_ref: str
    grounded_filler_ref: str
    grounding: ReferentGrounding | None = None
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class PredicationGrounding:
    predication_ref: str
    predicate_schema_ref: str
    predicate_semantic_key: str = ""
    definition: DefinitionGrounding | None = None
    role_bindings: tuple[GroundedRoleBinding, ...] = ()
    unresolved_role_refs: tuple[str, ...] = ()
    query_role_refs: tuple[str, ...] = ()
    opaque_role_refs: tuple[str, ...] = ()
    use_profile: SchemaUseProfile | None = None
    is_structurally_usable: bool = False
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GraphGrounding:
    predications: tuple[PredicationGrounding, ...] = ()
    referents: tuple[ReferentGrounding, ...] = ()
    definition_groundings: tuple[DefinitionGrounding, ...] = ()
    opaque_lexeme_refs: tuple[str, ...] = ()

    def for_predication(self, predication_ref: str) -> PredicationGrounding | None:
        return next(
            (item for item in self.predications if item.predication_ref == predication_ref),
            None,
        )


class GroundingResolver:
    def __init__(
        self,
        store: SemanticSchemaStore,
        resolver: SchemaResolver | None = None,
    ) -> None:
        self._store = store
        self._resolver = resolver or SchemaResolver(store)
        self._closure_checker = GroundedDefinitionClosure()
        self._competence_harness = CompetenceHarness()

    def ground_graph(
        self,
        candidate_graph: Any,
        surface_evidence: SurfaceEvidence,
        *,
        context_ref: str = "",
        environment_fingerprint: str = "",
    ) -> GraphGrounding:
        referents: list[ReferentGrounding] = []
        definitions: list[DefinitionGrounding] = []
        predications: list[PredicationGrounding] = []

        for candidate in candidate_graph.candidate_predications:
            predication = candidate.predication
            envelope = self._resolve_envelope(predication.predicate_schema_ref)
            if envelope is None:
                definition = DefinitionGrounding(
                    schema_record_ref=predication.predicate_schema_ref,
                    semantic_key=predication.predicate_schema_ref,
                    blockers=("predicate schema unresolved",),
                    use_profile=self._opaque_profile(
                        predication.predicate_schema_ref, context_ref,
                        "predicate schema unresolved",
                    ),
                )
            else:
                definition = self._definition_from_envelope(
                    envelope, context_ref, environment_fingerprint
                )
            definitions.append(definition)

            grounded_roles: list[GroundedRoleBinding] = []
            opaque_roles: list[str] = []
            for binding in predication.bindings:
                grounded = self._ground_binding(binding, surface_evidence)
                grounded_roles.append(grounded)
                if grounded.grounding is not None:
                    referents.append(grounded.grounding)
                    if grounded.grounding.is_unknown:
                        opaque_roles.append(binding.role_schema_ref)

            unresolved = tuple(port.role_schema_ref for port in predication.open_ports)
            use_profile = definition.use_profile
            structurally_usable = bool(
                use_profile is not None
                and use_profile.level not in {UseProfileLevel.INADMISSIBLE}
            )
            limitations = list(definition.blockers)
            if unresolved:
                limitations.append(f"unresolved roles: {', '.join(unresolved)}")
            if opaque_roles:
                limitations.append(f"opaque role fillers: {', '.join(opaque_roles)}")

            predications.append(
                PredicationGrounding(
                    predication_ref=predication.id,
                    predicate_schema_ref=predication.predicate_schema_ref,
                    predicate_semantic_key=(
                        getattr(envelope, "semantic_key", "")
                        if envelope is not None else predication.predicate_schema_ref
                    ),
                    definition=definition,
                    role_bindings=tuple(grounded_roles),
                    unresolved_role_refs=unresolved,
                    query_role_refs=self._query_role_refs(envelope),
                    opaque_role_refs=tuple(dict.fromkeys(opaque_roles)),
                    use_profile=use_profile,
                    is_structurally_usable=structurally_usable,
                    limitations=tuple(limitations),
                )
            )

        return GraphGrounding(
            predications=tuple(predications),
            referents=tuple(self._dedupe_referents(referents)),
            definition_groundings=tuple(definitions),
            opaque_lexeme_refs=tuple(candidate_graph.opaque_lexeme_refs),
        )

    def ground_referent(
        self,
        surface: str,
        language_tag: str = "en",
        discourse_context: dict[str, Any] | None = None,
    ) -> ReferentGrounding:
        keys = self._store.lookup_lexical_form(surface, language_tag)
        if not keys:
            opaque = self._opaque_key(surface, language_tag)
            return ReferentGrounding(
                referent_ref=f"ref:lexical:{opaque}",
                referent_kind="lexical_form",
                discourse_identity=opaque,
                confidence=0.0,
                is_unknown=True,
                surface=surface,
                semantic_keys=(opaque,),
            )
        active_keys = [key for key in keys if self._store.find_active(key) is not None]
        provisional_keys = [
            key for key in keys
            if any(
                getattr(candidate, "status", "") == "provisional"
                for candidate in self._store.find_candidates(key)
            )
        ]
        selected = (
            active_keys[0] if active_keys
            else provisional_keys[0] if provisional_keys
            else keys[0]
        )
        usable = bool(active_keys or provisional_keys)
        return ReferentGrounding(
            referent_ref=f"ref:schema:{selected}",
            referent_kind="schema_sense" if usable else "lexical_form",
            discourse_identity=f"{selected}:{language_tag}",
            confidence=0.9 if active_keys else (0.55 if provisional_keys else 0.2),
            is_unknown=not usable,
            surface=surface,
            semantic_keys=tuple(keys),
        )

    def ground_definition(
        self,
        semantic_key: str,
        context_ref: str = "",
        scope: Scope | None = None,
        valid_at: datetime | None = None,
        patterns: tuple[SemanticPattern, ...] = (),
        provenance_map: FieldProvenanceMap | None = None,
        competence_cases: tuple[Any, ...] = (),
        implementation_path: str = "",
        environment_fingerprint: str = "",
    ) -> DefinitionGrounding:
        candidates = self._store.find_candidates(
            semantic_key,
            context_ref=context_ref or None,
            scope=scope,
            valid_at=valid_at,
        )
        if not candidates:
            return DefinitionGrounding(
                semantic_key=semantic_key,
                use_profile=self._opaque_profile(
                    semantic_key, context_ref, "no schema candidate"
                ),
                blockers=("No candidates found for semantic key",),
            )
        envelope = max(
            candidates,
            key=lambda item: (
                item.status == "active", item.status == "provisional", item.version
            ),
        )
        if envelope.status == "active":
            return self._definition_from_envelope(
                envelope, context_ref, environment_fingerprint
            )

        spec = GroundingSpecification(
            semantic_family=envelope.schema_kind,
            required_definition_fields=(),
            allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
            minimum_independent_oracle_classes=frozenset({"invariant"}),
        )
        assessment = self._closure_checker.assess(
            envelope=envelope,
            grounding_spec=spec,
            patterns=patterns,
            provenance_map=provenance_map,
            dependencies=envelope.dependency_refs,
            environment_fingerprint=environment_fingerprint,
        )
        competence = None
        if competence_cases:
            competence = self._competence_harness.assess(
                tuple(competence_cases), implementation_path
            )
        use_profile = derive_use_profile(
            assessment=assessment,
            context_ref=context_ref,
            competence_is_competent=bool(competence and competence.is_competent),
            competence_is_self_certified=bool(
                competence and competence.is_self_certified
            ),
            epistemic_admissible=True,
            scope_accessible=True,
        )
        return DefinitionGrounding(
            schema_record_ref=envelope.record_id,
            semantic_key=envelope.semantic_key,
            semantic_family=envelope.schema_kind,
            assessment=assessment,
            use_profile=use_profile,
            competence=competence,
            is_grounded=use_profile.level in {UseProfileLevel.ACTIVE, UseProfileLevel.CAUSAL},
            blockers=assessment.blocker_reasons,
        )

    def _ground_binding(
        self, binding: RoleBinding, evidence: SurfaceEvidence,
    ) -> GroundedRoleBinding:
        filler = binding.filler_ref
        if not filler.startswith("ref:token:"):
            return GroundedRoleBinding(
                binding.role_schema_ref,
                filler,
                filler,
                confidence=binding.confidence,
            )
        try:
            index = int(filler.rsplit(":", 1)[1])
            token = evidence.token_stream.tokens[index]
        except (ValueError, IndexError):
            return GroundedRoleBinding(
                binding.role_schema_ref,
                filler,
                filler,
                confidence=0.0,
            )

        lemma = token.lemma_candidates[0] if token.lemma_candidates else token.normalized_form
        grammatical = {
            "what", "which", "who", "where", "when", "why", "how",
            "a", "an", "the", "do", "does", "did", "is", "are", "am",
            "was", "were", "be", "not", "and", "or", "but", "if", "that",
        }
        if lemma in grammatical:
            grounding = ReferentGrounding(
                referent_ref=f"grammar:{lemma}",
                referent_kind="grammatical_operator",
                discourse_identity=f"grammar:{lemma}:{evidence.language_tag}",
                confidence=1.0,
                source_token_index=index,
                surface=token.raw_form,
                semantic_keys=(f"grammar:{lemma}",),
            )
            return GroundedRoleBinding(
                role_schema_ref=binding.role_schema_ref,
                original_filler_ref=filler,
                grounded_filler_ref=grounding.referent_ref,
                grounding=grounding,
                confidence=min(binding.confidence, 1.0),
            )
        components = tuple(
            component.casefold() for component in token.contraction.components
        ) if token.contraction else ()
        deictic = components[0] if components else lemma
        if deictic in {"i", "me", "my", "mine", "we", "us", "our"}:
            grounding = ReferentGrounding(
                referent_ref="user",
                referent_kind="discourse_participant",
                discourse_identity="speaker:user",
                confidence=1.0,
                source_token_index=index,
                surface=token.raw_form,
            )
        elif deictic in {"you", "your", "yours"}:
            grounding = ReferentGrounding(
                referent_ref="self",
                referent_kind="discourse_participant",
                discourse_identity="addressee:self",
                confidence=1.0,
                source_token_index=index,
                surface=token.raw_form,
            )
        else:
            grounding = self.ground_referent(token.normalized_form, evidence.language_tag)
            grounding = ReferentGrounding(
                referent_ref=grounding.referent_ref,
                referent_kind=grounding.referent_kind,
                discourse_identity=grounding.discourse_identity,
                confidence=grounding.confidence,
                is_unknown=grounding.is_unknown,
                source_token_index=index,
                surface=token.raw_form,
                semantic_keys=grounding.semantic_keys,
            )
        return GroundedRoleBinding(
            role_schema_ref=binding.role_schema_ref,
            original_filler_ref=filler,
            grounded_filler_ref=grounding.referent_ref,
            grounding=grounding,
            confidence=min(binding.confidence, grounding.confidence or binding.confidence),
        )

    def _resolve_envelope(self, predicate_ref: str) -> Any | None:
        direct = self._store.get(predicate_ref)
        if direct is not None:
            return direct
        active = self._store.find_active(predicate_ref)
        if active is not None:
            return active
        candidates = self._store.find_candidates(predicate_ref)
        return max(candidates, key=lambda item: item.version) if candidates else None

    def _definition_from_envelope(
        self, envelope: Any, context_ref: str, environment_fingerprint: str,
    ) -> DefinitionGrounding:
        if envelope.status == "active":
            profile = SchemaUseProfile(
                schema_record_ref=envelope.record_id,
                context_ref=context_ref,
                level=UseProfileLevel.ACTIVE,
                structural_status="structurally_executable",
                competence_status="boot_or_independently_validated",
                epistemic_admissibility="admitted",
                permitted_semantic_operations=frozenset(
                    operation.value for operation in ACTIVE_OPERATIONS
                ),
                grounding_assessment_ref=envelope.grounding_assessment_ref,
            )
            return DefinitionGrounding(
                schema_record_ref=envelope.record_id,
                semantic_key=envelope.semantic_key,
                semantic_family=envelope.schema_kind,
                use_profile=profile,
                is_grounded=True,
            )
        profile = SchemaUseProfile(
            schema_record_ref=envelope.record_id,
            context_ref=context_ref,
            level=UseProfileLevel.PARTIAL,
            structural_status="partial",
            competence_status="limited",
            epistemic_admissibility="attributed_only",
            permitted_semantic_operations=frozenset(
                operation.value for operation in PARTIAL_OPERATIONS
            ),
            limitations=("schema is provisional",),
        )
        return DefinitionGrounding(
            schema_record_ref=envelope.record_id,
            semantic_key=envelope.semantic_key,
            semantic_family=envelope.schema_kind,
            use_profile=profile,
            is_grounded=False,
            blockers=("schema is provisional",),
        )

    @staticmethod
    def _query_role_refs(envelope: Any | None) -> tuple[str, ...]:
        if envelope is None:
            return ()
        payload = getattr(envelope, "payload", None)
        refs: list[str] = []
        for projection in getattr(payload, "query_projections", ()) or ():
            if getattr(projection, "projection_kind", "") != "open_role":
                continue
            refs.extend(str(ref) for ref in getattr(projection, "role_refs", ()) if ref)
        return tuple(dict.fromkeys(refs))

    @staticmethod
    def _opaque_profile(
        schema_ref: str, context_ref: str, limitation: str,
    ) -> SchemaUseProfile:
        return SchemaUseProfile(
            schema_record_ref=schema_ref,
            context_ref=context_ref,
            level=UseProfileLevel.OPAQUE,
            structural_status="opaque",
            epistemic_admissibility="blocked",
            permitted_semantic_operations=frozenset(
                operation.value for operation in OPAQUE_OPERATIONS
            ),
            limitations=(limitation,),
        )

    @staticmethod
    def _opaque_key(surface: str, language: str) -> str:
        return f"opaque:{language}:{'_'.join(surface.casefold().split())}"

    @staticmethod
    def _dedupe_referents(
        referents: list[ReferentGrounding],
    ) -> list[ReferentGrounding]:
        result: list[ReferentGrounding] = []
        seen: set[tuple[str, int | None]] = set()
        for referent in referents:
            key = (referent.referent_ref, referent.source_token_index)
            if key not in seen:
                seen.add(key)
                result.append(referent)
        return result
