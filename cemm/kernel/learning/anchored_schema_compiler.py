"""Grounding-enforcing wrapper for the recursive dialogue learning compiler."""
from __future__ import annotations

from dataclasses import replace

from .schema_compiler import LearnedSchemaCompiler
from ..schema.envelope import SchemaDependency


class AnchoredLearnedSchemaCompiler(LearnedSchemaCompiler):
    """Keeps partial lexical hypotheses, but blocks unanchored semantic schemas.

    The wrapped compiler remains responsible for schema-family construction.
    This policy layer converts semantic-key dependencies into exact active
    revision references and records missing anchors as unresolved fields.  It
    cannot activate a revision and does not treat source text as a definition.
    """

    def __init__(self, schema_store) -> None:
        self._store = schema_store

    def compile(self, **kwargs):
        artifact = super().compile(**kwargs)
        envelope = artifact.primary_envelope
        payload = envelope.payload
        unresolved = list(artifact.unresolved_fields)
        limitations = list(artifact.limitations)
        dependencies = []

        if envelope.schema_kind == "entity_kind":
            anchors = []
            parent_keys = []
            for parent in tuple(getattr(payload, "parent_kind_refs", ()) or ()):
                active = self._active(parent, "entity_kind")
                if active is None:
                    unresolved.append(f"grounding_anchor:entity_kind:{parent}")
                    continue
                parent_keys.append(active.semantic_key)
                anchors.append(active.record_id)
                dependencies.append(self._dependency("inheritance", active.record_id))
            predicate_keys = []
            for predicate in tuple(getattr(payload, "predicate_refs", ()) or ()):
                active = self._active(predicate, "predicate")
                if active is None:
                    unresolved.append(f"grounding_anchor:predicate:{predicate}")
                    continue
                predicate_keys.append(active.semantic_key)
                anchors.append(active.record_id)
                dependencies.append(self._dependency("definition", active.record_id))
            payload = replace(
                payload,
                parent_kind_refs=tuple(dict.fromkeys(parent_keys)),
                predicate_refs=tuple(dict.fromkeys(predicate_keys)),
                grounding_anchor_refs=tuple(dict.fromkeys((
                    *tuple(getattr(payload, "grounding_anchor_refs", ()) or ()),
                    *anchors,
                ))),
            )
            if not anchors:
                unresolved.append("grounded_entity_place_event_self_anchor")

        elif envelope.schema_kind == "predicate":
            for role_ref in tuple(getattr(payload, "role_refs", ()) or ()):
                active = self._active(role_ref, "role")
                if active is None:
                    unresolved.append(f"grounding_anchor:role:{role_ref}")
                else:
                    dependencies.append(self._dependency("definition", active.record_id))

        elif envelope.schema_kind == "state_dimension":
            holders = tuple(getattr(payload, "holder_kinds", ()) or ())
            for holder in holders:
                active = self._active(holder, "entity_kind")
                if active is None:
                    unresolved.append(f"grounding_anchor:holder_kind:{holder}")
                else:
                    dependencies.append(self._dependency("selectional", active.record_id))
            if not holders:
                unresolved.append("grounded_holder_kind")

        elif envelope.schema_kind == "rule":
            # Surface rule drafts are never executable.  The dedicated grounded
            # rule learner must supply non-empty, anchored atoms and competence.
            unresolved.extend((
                "grounded_premise_atoms",
                "grounded_conclusion_atoms",
                "grounding_anchor_closure",
            ))
            limitations.append("rule execution requires GroundedRuleLearner")

        elif envelope.schema_kind == "lexeme_sense":
            unresolved.extend((
                "grounded_semantic_schema",
                "sense_individuation",
            ))

        dependency_refs = tuple(dict.fromkeys(
            dependency.target_schema_ref for dependency in dependencies
        ))
        envelope = replace(
            envelope,
            payload=payload,
            dependency_refs=dependency_refs,
        )
        return replace(
            artifact,
            primary_envelope=envelope,
            dependencies=tuple(self._dedupe_dependencies(dependencies)),
            unresolved_fields=tuple(dict.fromkeys(unresolved)),
            limitations=tuple(dict.fromkeys(limitations)),
        )

    def _active(self, value: str, expected_kind: str):
        value = str(value)
        envelope = self._store.get(value)
        if envelope is None:
            envelope = self._store.find_active(value)
        if envelope is None and value.startswith("role:"):
            envelope = self._store.find_active(value.removeprefix("role:"))
        if envelope is None and not value.startswith("role:"):
            envelope = self._store.find_active(f"role:{value}")
        if envelope is None or envelope.status != "active":
            return None
        return envelope if envelope.schema_kind == expected_kind else None

    @staticmethod
    def _dependency(kind: str, record_id: str) -> SchemaDependency:
        return SchemaDependency(
            dependency_kind=kind,
            target_schema_ref=record_id,
            polarity="positive",
            monotonicity="monotone",
            required_for_operations=frozenset({
                "compose_qualified", "query_theory", "classify",
            }),
        )

    @staticmethod
    def _dedupe_dependencies(items):
        result = []
        seen = set()
        for item in items:
            key = (item.dependency_kind, item.target_schema_ref)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result
