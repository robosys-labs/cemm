"""Assimilate grounded taxonomic definitions into provisional schema revisions."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import unicodedata

from .anchor_validator import GroundingAnchorValidator
from ..model.identity import Permission, Provenance, Scope, ScopeLevel
from ..schema.entity_kind import EntityKindSchema
from ..schema.envelope import SchemaDependency, SchemaEnvelope


@dataclass(frozen=True, slots=True)
class GroundedDefinitionLearningResult:
    proposition_ref: str
    schema_record_ref: str = ""
    semantic_key: str = ""
    status: str = "blocked"
    anchor_refs: tuple[str, ...] = ()
    blocker_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


class GroundedDefinitionLearner:
    """Learns only graph-grounded definitions; never copies raw text fields."""

    def __init__(self, schema_store, semantic_memory=None) -> None:
        self._store = schema_store
        self._validator = GroundingAnchorValidator(schema_store, semantic_memory)

    def learn_cycle(self, cycle) -> tuple[GroundedDefinitionLearningResult, ...]:
        results = []
        for interpretation in tuple(
            getattr(cycle, "selected_interpretations", ()) or ()
        ):
            if getattr(interpretation, "communicative_force", "") not in {
                "assert", "correct"
            }:
                continue
            if getattr(interpretation, "predicate_semantic_key", "") != "subkind_of":
                continue
            roles = {
                binding.role_schema_ref.removeprefix("role:"): binding.filler_ref
                for binding in tuple(getattr(interpretation, "role_bindings", ()) or ())
            }
            surfaces = {
                item.role_schema_ref.removeprefix("role:"): item.surface
                for item in tuple(getattr(interpretation, "role_groundings", ()) or ())
                if getattr(item, "surface", "")
            }
            child_ref = roles.get("child_kind", "")
            child_surface = surfaces.get("child_kind", "")
            child = self._semantic_key(child_ref, child_surface)
            parent = roles.get("parent_kind", "")
            language_tag = next((
                getattr(item, "language_tag", "und")
                for item in tuple(getattr(cycle, "surface_evidence", ()) or ())
            ), "und")
            results.append(self._learn(
                child,
                parent,
                lexical_surface=child_surface,
                language_tag=language_tag,
                proposition_ref=str(getattr(interpretation, "proposition_ref", "")),
                context_id=cycle.trigger.context_id,
                cycle_id=cycle.cycle_id,
            ))
        return tuple(results)

    def _learn(
        self,
        child: str,
        parent: str,
        *,
        lexical_surface: str,
        language_tag: str,
        proposition_ref: str,
        context_id: str,
        cycle_id: str,
    ) -> GroundedDefinitionLearningResult:
        existing = tuple(self._store.find_candidates(child))
        latest = max(existing, key=lambda item: item.version, default=None)
        latest_payload = getattr(latest, "payload", None) if latest else None
        inherited_parents = tuple(
            getattr(latest_payload, "parent_kind_refs", ()) or ()
        )
        parent_refs = tuple(dict.fromkeys((*inherited_parents, parent)))
        validation = self._validator.validate_entity_kind(child, parent_refs)
        if not validation.grounded:
            return GroundedDefinitionLearningResult(
                proposition_ref=proposition_ref,
                semantic_key=child,
                blocker_refs=validation.blocker_refs,
            )

        if isinstance(latest_payload, EntityKindSchema) and parent in inherited_parents:
            return GroundedDefinitionLearningResult(
                proposition_ref=proposition_ref,
                schema_record_ref=latest.record_id,
                semantic_key=child,
                status=latest.status,
                anchor_refs=validation.anchor_refs,
                evidence_refs=(cycle_id, proposition_ref),
                blocker_refs=("independent_competence_required",),
            )

        active_parents = {
            parent_ref: self._store.find_active(parent_ref)
            for parent_ref in parent_refs
        }
        missing = tuple(
            parent_ref for parent_ref, envelope in active_parents.items()
            if envelope is None or envelope.schema_kind != "entity_kind"
        )
        if missing:
            return GroundedDefinitionLearningResult(
                proposition_ref=proposition_ref,
                semantic_key=child,
                blocker_refs=tuple(
                    f"unanchored_parent_kind:{parent_ref}"
                    for parent_ref in missing
                ),
            )
        digest = hashlib.sha256(
            f"{child}|{parent}|{context_id}".encode("utf-8")
        ).hexdigest()[:16]
        version = max(
            (int(getattr(item, "version", 0)) for item in existing),
            default=0,
        ) + 1
        record_id = f"learned:entity_kind:{digest}:v{version}"
        payload = EntityKindSchema(
            semantic_key=child,
            parent_kind_refs=parent_refs,
            state_dimension_refs=tuple(
                getattr(latest_payload, "state_dimension_refs", ()) or ()
            ),
            predicate_refs=tuple(
                getattr(latest_payload, "predicate_refs", ()) or ()
            ),
            typical_features=tuple(
                getattr(latest_payload, "typical_features", ()) or ()
            ),
            identity_criteria=tuple(
                getattr(latest_payload, "identity_criteria", ()) or ()
            ),
            grounding_anchor_refs=tuple(dict.fromkeys((
                *tuple(getattr(latest_payload, "grounding_anchor_refs", ()) or ()),
                *validation.anchor_refs,
            ))),
            constitutive_rule_refs=tuple(dict.fromkeys((
                *tuple(getattr(latest_payload, "constitutive_rule_refs", ()) or ()),
                proposition_ref,
            ))),
            default_rule_refs=tuple(
                getattr(latest_payload, "default_rule_refs", ()) or ()
            ),
            event_pattern_refs=tuple(
                getattr(latest_payload, "event_pattern_refs", ()) or ()
            ),
            place_pattern_refs=tuple(
                getattr(latest_payload, "place_pattern_refs", ()) or ()
            ),
            sensitivity=str(
                getattr(latest_payload, "sensitivity", "ordinary")
            ),
        )
        dependencies = tuple(
            SchemaDependency(
                dependency_kind="inheritance",
                target_schema_ref=active_parents[parent_ref].record_id,
                polarity="positive",
                monotonicity="monotone",
                required_for_operations=frozenset({
                    "compose_qualified", "query_theory", "classify"
                }),
            )
            for parent_ref in parent_refs
        )
        envelope = SchemaEnvelope(
            record_id=record_id,
            semantic_key=child,
            schema_kind="entity_kind",
            status="candidate",
            scope=Scope(level=ScopeLevel.SESSION, session_id=context_id),
            version=version,
            payload=payload,
            dependency_refs=tuple(
                dependency.target_schema_ref for dependency in dependencies
            ),
            support_refs=(cycle_id, proposition_ref),
            confidence=0.82,
            permission=Permission.session_private(),
            provenance=Provenance(
                source_id=cycle_id,
                source_kind="user_definition",
                language_tag=language_tag,
            ),
            supersedes_refs=(latest.record_id,) if latest is not None else (),
        )
        self._store.register(envelope, dependencies=dependencies)
        if lexical_surface:
            self._store.index_lexical_form(
                unicodedata.normalize("NFKC", lexical_surface).casefold(),
                language_tag.split("-", 1)[0],
                child,
            )
        revision = self._store.get_revision(record_id)
        transition = self._store.transition_to_provisional(record_id, revision)
        status = (
            "provisional"
            if getattr(transition.status, "value", transition.status) == "success"
            else "candidate"
        )
        return GroundedDefinitionLearningResult(
            proposition_ref=proposition_ref,
            schema_record_ref=record_id,
            semantic_key=child,
            status=status,
            anchor_refs=validation.anchor_refs,
            evidence_refs=(cycle_id, proposition_ref),
            blocker_refs=("independent_competence_required",),
        )

    @staticmethod
    def _semantic_key(existing_ref: str, surface: str) -> str:
        if existing_ref and not existing_ref.startswith((
            "entity:mention:", "ref:", "opaque:", "value:",
        )):
            return existing_ref
        normalized = " ".join(
            unicodedata.normalize("NFKC", surface).casefold().split()
        )
        if not normalized:
            return ""
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        return f"learned_kind:{digest}"
