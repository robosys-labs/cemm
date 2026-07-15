"""Compile grounded teaching evidence into the correct schema family."""
from __future__ import annotations
from dataclasses import dataclass
from uuid import uuid4
from ..model.identity import (
    Permission, PermissionScope, Provenance,
    RetentionPolicy, Scope,
)
from ..model.surface import LexicalFormRef
from ..schema.entity_kind import EntityKindSchema
from ..schema.envelope import SchemaDependency, SchemaEnvelope
from ..schema.lexeme import LexemeSenseSchema
from ..schema.predicate import PredicateSchema
from ..schema.rule import RuleSchema
from ..schema.state_dimension import StateDimensionSchema

@dataclass(frozen=True, slots=True)
class CompiledLearningArtifact:
    primary_envelope: SchemaEnvelope
    auxiliary_envelopes: tuple[SchemaEnvelope, ...] = ()
    dependencies: tuple[SchemaDependency, ...] = ()
    unresolved_fields: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

class LearnedSchemaCompiler:
    def compile(
        self, *, target_semantic_key, target_surface,
        language_tag, scope, contributions,
        rule_candidates=(), source_ref, version,
    ):
        values = {}
        for contribution in contributions:
            values.setdefault(
                contribution.field_name, []
            ).append(contribution.field_value)
        family = self._first(values, "semantic_family")
        dependencies, unresolved, limitations = [], [], []

        if rule_candidates:
            rule = RuleSchema(
                semantic_key=f"learned_rule:{uuid4().hex[:12]}",
                premises=(),
                conclusions=(),
                rule_kind=rule_candidates[0].rule_kind,
                strength=rule_candidates[0].strength,
                causal_warrant=rule_candidates[0].causal_warrant,
                enabled_by_default=False,
                provenance_refs=(source_ref,),
            )
            envelope = self._envelope(
                target_semantic_key, "rule", rule,
                scope, source_ref, version,
            )
            return CompiledLearningArtifact(
                primary_envelope=envelope,
                unresolved_fields=(
                    "premise_predications",
                    "conclusion_predications",
                    "independent_competence",
                ),
                limitations=(
                    "surface rule draft is disabled until "
                    "ordinary-clause replay fills its atoms",
                ),
            )

        if family in {
            "entity_kind", "role", "entity_kind_or_role"
        }:
            parents = tuple(dict.fromkeys(
                str(value)
                for value in values.get("parent_kind_ref", ())
                if value
            ))
            predicates = tuple(dict.fromkeys(
                str(value)
                for value in values.get(
                    "constitutive_predicate_ref", ()
                )
                if value
            ))
            if not parents and not predicates:
                unresolved.append("constitutive_structure")
            payload = EntityKindSchema(
                semantic_key=target_semantic_key,
                parent_kind_refs=parents,
                predicate_refs=predicates,
                identity_criteria=tuple(
                    str(value)
                    for value in values.get(
                        "identity_criterion", ()
                    )
                ),
                typical_features=tuple(
                    str(value)
                    for value in values.get(
                        "typical_feature_ref", ()
                    )
                ),
            )
            dependencies.extend(
                SchemaDependency(
                    dependency_kind="definition",
                    target_schema_ref=parent,
                )
                for parent in parents
            )
            schema_kind = "entity_kind"
        elif family == "predicate":
            roles = tuple(dict.fromkeys(
                str(value).removeprefix("role:")
                for value in values.get("role_ref", ())
                if value
            ))
            if not roles:
                unresolved.append("required_roles")
            payload = PredicateSchema(
                semantic_key=target_semantic_key,
                role_refs=tuple(
                    f"role:{role}" for role in roles
                ),
                predication_kind=str(
                    self._first(
                        values, "predication_kind"
                    ) or "relation"
                ),
            )
            schema_kind = "predicate"
        elif family == "state_dimension":
            value_type = str(
                self._first(values, "value_type") or ""
            )
            if not value_type:
                unresolved.append("value_type")
            payload = StateDimensionSchema(
                semantic_key=target_semantic_key,
                value_type=value_type or "text",
                holder_kinds=frozenset(
                    str(value)
                    for value in values.get(
                        "holder_kind_ref", ()
                    )
                ),
            )
            schema_kind = "state_dimension"
        else:
            payload = LexemeSenseSchema(
                semantic_key=target_semantic_key,
                lexical_form_refs=(LexicalFormRef(
                    surface=target_surface,
                    language_tag=language_tag,
                    normalised=target_surface.casefold(),
                ),),
                part_of_speech=str(
                    self._first(
                        values, "part_of_speech"
                    ) or ""
                ),
                sense_disambiguators=tuple(
                    str(value)
                    for value in values.get(
                        "related_surface_form", ()
                    )
                ),
            )
            schema_kind = "lexeme_sense"
            unresolved.extend((
                "semantic_family",
                "constitutive_structure",
            ))
            limitations.append(
                "only a lexical candidate has been established"
            )

        primary = self._envelope(
            target_semantic_key, schema_kind, payload,
            scope, source_ref, version,
        )
        auxiliary = ()
        if schema_kind != "lexeme_sense" and target_surface:
            lexical = LexemeSenseSchema(
                semantic_key=target_semantic_key,
                lexical_form_refs=(LexicalFormRef(
                    surface=target_surface,
                    language_tag=language_tag,
                    normalised=target_surface.casefold(),
                ),),
                semantic_schema_ref=primary.record_id,
                part_of_speech=str(
                    self._first(
                        values, "part_of_speech"
                    ) or ""
                ),
            )
            auxiliary = (
                self._envelope(
                    f"lexeme:{language_tag}:"
                    f"{target_semantic_key}",
                    "lexeme_sense", lexical,
                    scope, source_ref, version,
                ),
            )
        return CompiledLearningArtifact(
            primary_envelope=primary,
            auxiliary_envelopes=auxiliary,
            dependencies=tuple(dependencies),
            unresolved_fields=tuple(
                dict.fromkeys(unresolved)
            ),
            limitations=tuple(dict.fromkeys(limitations)),
        )

    @staticmethod
    def _envelope(
        key, schema_kind, payload, scope,
        source_ref, version,
    ):
        return SchemaEnvelope(
            record_id=(
                f"learned:{schema_kind}:"
                f"{uuid4().hex[:12]}:v{version}"
            ),
            semantic_key=key,
            schema_kind=schema_kind,
            status="candidate",
            scope=scope,
            version=version,
            payload=payload,
            confidence=0.45,
            permission=Permission(
                scope=PermissionScope.SESSION_PRIVATE,
                may_store=True,
                may_retrieve=True,
                may_use=True,
                may_share=False,
                may_execute=False,
                retention=RetentionPolicy.SESSION,
            ),
            provenance=Provenance(
                source_id=source_ref,
                source_kind="user_teaching",
            ),
        )

    @staticmethod
    def _first(values, key):
        items = values.get(key, ())
        return items[0] if items else None
