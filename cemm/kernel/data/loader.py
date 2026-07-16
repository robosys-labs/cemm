"""Load, validate and activate versioned foundation/language data packages."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, json
from typing import Any

from ..model.identity import Permission, Provenance, Scope, ScopeLevel
from ..model.refs import FrozenMap
from ..model.surface import LexicalFormRef
from ..schema.construction import InputConstructionSchema
from ..schema.entity_kind import EntityKindSchema
from ..schema.envelope import SchemaDependency, SchemaEnvelope
from ..schema.lexeme import LexemeSenseSchema
from ..schema.operation import OperationSchema, CostModel
from ..schema.predicate import (
    CardinalityPolicy, ContextBehavior, EvidencePolicy, IdentityPolicy,
    ModalityBehavior, PersistencePolicy, PolarityBehavior, PredicateSchema,
    QueryProjection,
)
from ..schema.realization import RealizationSchema
from ..schema.role import RoleSchema
from ..schema.rule import RelationAlgebraSchema, RuleSchema
from ..schema.state_dimension import StateDimensionSchema
from ...language.pack import LanguagePackRegistry

@dataclass(frozen=True, slots=True)
class DefinitionValidationReport:
    ok: bool
    fingerprint: str
    failures: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def require_ok(self):
        if not self.ok:
            raise RuntimeError(
                "definition package validation failed: " + "; ".join(self.failures)
            )

@dataclass(frozen=True, slots=True)
class _GroundingAssessment:
    is_structurally_executable: bool = True
    blocker_reasons: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class _CompetenceAssessment:
    is_competent: bool = True
    is_self_certified: bool = False

class DefinitionPackageLoader:
    FORBIDDEN_FOUNDATION_DOMAIN_KEYS = frozenset({
        "machine", "leader", "president", "engineer",
        "mother_in_law", "wife", "husband",
    })

    def __init__(self, data_root: Path):
        self.root = data_root
        self.manifest = self._json("foundations/manifest.json")
        self.roles = self._json("foundations/roles.json")
        self.predicates = self._json("foundations/predicates.json")
        self.entity_kinds = self._json("foundations/entity_kinds.json")
        self.state_dimensions = self._json("foundations/state_dimensions.json")
        self.operations = self._json("foundations/operations.json")
        self.relation_algebra = self._json("foundations/relation_algebra.json")
        self.rules = self._json("foundations/rules.json")
        self.dialogue_policies = self._json("foundations/dialogue_policies.json")

    def validate(self, language_registry=None):
        failures, warnings = [], []
        role_keys = {item["semantic_key"] for item in self.roles}
        predicate_keys = {item["semantic_key"] for item in self.predicates}
        entity_keys = {item["semantic_key"] for item in self.entity_kinds}
        state_keys = {item["semantic_key"] for item in self.state_dimensions}
        operation_keys = {item["semantic_key"] for item in self.operations}
        all_semantics = predicate_keys | entity_keys | state_keys | operation_keys

        for label, collection in (
            ("roles", self.roles), ("predicates", self.predicates),
            ("entity_kinds", self.entity_kinds),
            ("state_dimensions", self.state_dimensions),
            ("operations", self.operations), ("rules", self.rules),
        ):
            keys = [item["semantic_key"] for item in collection]
            if len(keys) != len(set(keys)):
                failures.append(f"duplicate semantic key in {label}")

        forbidden = self.FORBIDDEN_FOUNDATION_DOMAIN_KEYS & all_semantics
        if forbidden:
            failures.append(
                "domain concepts are present in foundation package: "
                + ", ".join(sorted(forbidden))
            )

        for predicate in self.predicates:
            missing = set(predicate.get("role_refs", ())) - role_keys
            if missing:
                failures.append(
                    f"predicate {predicate['semantic_key']} missing roles {sorted(missing)}"
                )
        for entity in self.entity_kinds:
            for field, available in (
                ("parent_kind_refs", entity_keys),
                ("state_dimension_refs", state_keys),
                ("predicate_refs", predicate_keys),
            ):
                missing = set(entity.get(field, ())) - available
                if missing:
                    failures.append(
                        f"entity {entity['semantic_key']} has missing {field}: "
                        f"{sorted(missing)}"
                    )
        for algebra in self.relation_algebra:
            if algebra["predicate_key"] not in predicate_keys:
                failures.append(
                    f"algebra references missing predicate {algebra['predicate_key']}"
                )
            inverse = algebra.get("inverse_predicate_key")
            if inverse and inverse not in predicate_keys:
                failures.append(f"algebra references missing inverse {inverse}")
        for rule in self.rules:
            for atom in (*rule.get("premises", ()), *rule.get("conclusions", ())):
                if atom["predicate_key"] not in predicate_keys:
                    failures.append(
                        f"rule {rule['semantic_key']} references missing predicate "
                        f"{atom['predicate_key']}"
                    )
            if rule.get("sensitivity") == "sensitive" and rule.get(
                "enabled_by_default", True
            ):
                failures.append(
                    f"sensitive rule {rule['semantic_key']} cannot be enabled by default"
                )

        digest = hashlib.sha256()
        for path in sorted((self.root / "foundations").glob("*.json")):
            digest.update(path.read_bytes())

        if language_registry:
            for tag in language_registry.language_tags:
                pack = language_registry.require(tag)
                for entry in pack.lexical_entries:
                    key = entry.semantic_key
                    if not key.startswith((
                        "grammar:", "pronoun:", "wh:", "aux:", "polarity:"
                    )) and key not in all_semantics:
                        failures.append(
                            f"{tag} lexeme {entry.surface!r} points to missing {key}"
                        )
                for construction in pack.constructions:
                    if (
                        construction.predicate_key
                        and construction.predicate_key not in predicate_keys
                    ):
                        failures.append(
                            f"{tag} construction {construction.schema_id} "
                            f"points to missing predicate "
                            f"{construction.predicate_key}"
                        )
                    if not construction.terms:
                        failures.append(
                            f"{tag} construction {construction.schema_id} has no terms"
                        )
                for realization in pack.realizations:
                    if realization.predicate_key not in predicate_keys:
                        failures.append(
                            f"{tag} realization points to missing predicate "
                            f"{realization.predicate_key}"
                        )
        return DefinitionValidationReport(
            ok=not failures,
            fingerprint=digest.hexdigest(),
            failures=tuple(failures),
            warnings=tuple(warnings),
        )

    def install(self, store, language_registry):
        report = self.validate(language_registry)
        report.require_ok()
        registered = []

        for item in self.roles:
            payload = RoleSchema(
                role_key=item["semantic_key"],
                required=bool(item.get("required", True)),
                cardinality=item.get("cardinality", "one"),
                accepted_object_families=frozenset(
                    item.get("accepted_object_families", ())
                ),
                accepted_entity_kinds=frozenset(
                    item.get("accepted_entity_kinds", ())
                ),
                accepted_value_types=frozenset(
                    item.get("accepted_value_types", ())
                ),
                allows_open_port=bool(item.get("allows_open_port", True)),
                allows_embedded_predication=bool(
                    item.get("allows_embedded_predication", False)
                ),
                allows_embedded_proposition=bool(
                    item.get("allows_embedded_proposition", False)
                ),
            )
            registered.append(self._register_active(
                store, f"foundation:role:{item['semantic_key']}",
                f"role:{item['semantic_key']}", "role", payload, report,
            ))

        for item in self.state_dimensions:
            payload = StateDimensionSchema(
                semantic_key=item["semantic_key"],
                holder_kinds=frozenset(item.get("holder_kinds", ())),
                value_type=item.get("value_type", "text"),
                unit=item.get("unit"),
                cardinality=item.get("cardinality", "one"),
                temporal_policy=item.get(
                    "temporal_policy", "persistent_until_changed"
                ),
                contradiction_policy=item.get(
                    "contradiction_policy", "latest_wins"
                ),
                transition_predicate_refs=tuple(
                    item.get("transition_predicate_refs", ())
                ),
            )
            registered.append(self._register_active(
                store, f"foundation:state:{item['semantic_key']}",
                item["semantic_key"], "state_dimension", payload, report,
            ))

        for item in self.entity_kinds:
            payload = EntityKindSchema(
                semantic_key=item["semantic_key"],
                parent_kind_refs=tuple(item.get("parent_kind_refs", ())),
                state_dimension_refs=tuple(
                    item.get("state_dimension_refs", ())
                ),
                predicate_refs=tuple(item.get("predicate_refs", ())),
                typical_features=tuple(item.get("typical_features", ())),
                identity_criteria=tuple(item.get("identity_criteria", ())),
                grounding_anchor_refs=tuple(item.get("grounding_anchor_refs", ())),
                constitutive_rule_refs=tuple(item.get("constitutive_rule_refs", ())),
                default_rule_refs=tuple(item.get("default_rule_refs", ())),
                event_pattern_refs=tuple(item.get("event_pattern_refs", ())),
                place_pattern_refs=tuple(item.get("place_pattern_refs", ())),
                sensitivity=str(item.get("sensitivity", "ordinary")),
            )
            dependencies = tuple(
                SchemaDependency(
                    dependency_kind="definition",
                    target_schema_ref=self._record_for(store, key),
                )
                for key in item.get("parent_kind_refs", ())
                if self._record_for(store, key)
            )
            registered.append(self._register_active(
                store, f"foundation:entity:{item['semantic_key']}",
                item["semantic_key"], "entity_kind", payload, report,
                dependencies,
            ))

        for item in self.predicates:
            payload = PredicateSchema(
                semantic_key=item["semantic_key"],
                predication_kind=item.get("predication_kind", "relation"),
                agentive=bool(item.get("agentive", False)),
                role_refs=tuple(
                    f"role:{key}" for key in item.get("role_refs", ())
                ),
                context_behavior=ContextBehavior(
                    supports_reported=bool(
                        item.get("supports_reported", True)
                    ),
                    supports_hypothetical=bool(
                        item.get("supports_hypothetical", True)
                    ),
                    supports_counterfactual=bool(
                        item.get("supports_counterfactual", False)
                    ),
                    supports_quoted=bool(item.get("supports_quoted", True)),
                ),
                polarity_behavior=PolarityBehavior(
                    supports_negation=bool(
                        item.get("supports_negation", True)
                    ),
                    negation_kind=item.get(
                        "negation_kind", "contradictory"
                    ),
                ),
                modality_behavior=ModalityBehavior(
                    supports_modality=bool(
                        item.get("supports_modality", True)
                    )
                ),
                query_projections=tuple(
                    QueryProjection(
                        projection_kind=projection.get(
                            "projection_kind", "open_role"
                        ),
                        role_refs=tuple(
                            ref if ref.startswith("role:")
                            else f"role:{ref}"
                            for ref in projection.get("role_refs", ())
                        ),
                    )
                    for projection in item.get("query_projections", ())
                ),
                identity_policy=IdentityPolicy(
                    includes_valid_time=bool(
                        item.get("identity_includes_time", False)
                    ),
                    includes_modal_qualifiers=True,
                    includes_attribution=True,
                ),
                cardinality_policy=CardinalityPolicy(
                    cardinality=item.get("cardinality", "many"),
                    reinforcement_policy=item.get(
                        "reinforcement_policy", "reinforce"
                    ),
                ),
                evidence_policy=EvidencePolicy(
                    minimum_evidence_count=int(
                        item.get("minimum_evidence_count", 1)
                    ),
                    requires_independent_sources=bool(
                        item.get("requires_independent_sources", False)
                    ),
                ),
                persistence_policy=PersistencePolicy(
                    retention=item.get("retention", "long_term")
                ),
                sensitivity=str(item.get("sensitivity", "ordinary")),
            )
            registered.append(self._register_active(
                store, f"foundation:predicate:{item['semantic_key']}",
                item["semantic_key"], "predicate", payload, report,
            ))

        for item in self.operations:
            payload = OperationSchema(
                semantic_key=item["semantic_key"],
                operation_class=item.get("operation_class", "cognitive"),
                input_roles=tuple(
                    f"role:{value}"
                    for value in item.get("input_roles", ())
                ),
                output_roles=tuple(
                    f"role:{value}"
                    for value in item.get("output_roles", ())
                ),
                cost_model=CostModel(
                    base_cost=float(item.get("base_cost", 0.0)),
                    resource_costs=dict(item.get("resource_costs", {})),
                ),
                failure_modes=tuple(item.get("failure_modes", ())),
                idempotency_policy=item.get(
                    "idempotency_policy", "strict"
                ),
                adapter_binding=item.get("adapter_binding"),
            )
            registered.append(self._register_active(
                store,
                f"foundation:operation:{item['semantic_key'].replace(':', '_')}",
                item["semantic_key"], "operation", payload, report,
            ))

        for item in self.relation_algebra:
            payload = RelationAlgebraSchema(
                predicate_key=item["predicate_key"],
                inverse_predicate_key=item.get(
                    "inverse_predicate_key", ""
                ),
                symmetric=bool(item.get("symmetric", False)),
                transitive=bool(item.get("transitive", False)),
                reflexive=bool(item.get("reflexive", False)),
                irreflexive=bool(item.get("irreflexive", False)),
                antisymmetric=bool(item.get("antisymmetric", False)),
                composition_rules=tuple(
                    item.get("composition_rules", ())
                ),
            )
            registered.append(self._register_active(
                store, f"foundation:algebra:{item['predicate_key']}",
                f"algebra:{item['predicate_key']}",
                "relation_algebra", payload, report,
            ))

        for item in self.rules:
            registered.append(self._register_active(
                store, f"foundation:rule:{item['semantic_key']}",
                item["semantic_key"], "rule",
                RuleSchema.from_dict(item), report,
            ))

        for tag in language_registry.language_tags:
            pack = language_registry.require(tag)
            for index, entry in enumerate(pack.lexical_entries):
                semantic_ref = self._record_for(store, entry.semantic_key)
                closed = (
                    entry.semantic_key in pack.closed_class_semantic_keys
                    or entry.semantic_key.startswith((
                        "grammar:", "pronoun:", "wh:",
                        "aux:", "polarity:"
                    ))
                )
                payload = LexemeSenseSchema(
                    semantic_key=entry.semantic_key,
                    lexical_form_refs=(LexicalFormRef(
                        surface=entry.surface,
                        language_tag=tag,
                        normalised=entry.surface.casefold(),
                    ),),
                    semantic_schema_ref="" if closed else semantic_ref,
                    part_of_speech=entry.part_of_speech,
                )
                registered.append(self._register_active(
                    store, f"language:{tag}:lexeme:{index}",
                    f"lexeme:{tag}:{entry.semantic_key}:{index}",
                    "lexeme_sense", payload, report,
                ))
                store.index_lexical_form(
                    entry.surface.casefold(), tag, entry.semantic_key
                )

            for index, construction in enumerate(pack.constructions):
                predicate_ref = self._record_for(
                    store, construction.predicate_key
                )
                payload = InputConstructionSchema(
                    schema_id=construction.schema_id,
                    language_tag=tag,
                    terms=construction.terms,
                    predicate_key=(
                        predicate_ref
                        or construction.predicate_key
                    ),
                    role_capture_map=construction.role_capture_map,
                    open_role_keys=tuple(
                        ref if ref.startswith("role:")
                        else f"role:{ref}"
                        for ref in construction.open_role_keys
                    ),
                    communicative_force=construction.communicative_force,
                    polarity=construction.polarity,
                    modality=construction.modality,
                    output_kind=construction.output_kind,
                    output_metadata=construction.output_metadata,
                    post_constraints=construction.post_constraints,
                    competence_case_refs=construction.competence_case_refs,
                    round_trip_case_refs=construction.round_trip_case_refs,
                    priority=construction.priority,
                    version=construction.version,
                )
                registered.append(self._register_active(
                    store,
                    f"language:{tag}:construction:{index}",
                    construction.schema_id,
                    "construction", payload, report,
                ))

            # Every indexed lexical sense receives a realization schema. Templates
            # may use literals for syntax, but the lexical-use gate still needs an
            # independently addressable realization for predicate and role senses.
            realization_keys = {
                entry.semantic_key for entry in pack.lexical_entries
            }
            for key in sorted(realization_keys):
                entry = pack.lexical_entry(key)
                if entry is None:
                    continue
                semantic_ref = self._record_for(store, key)
                closed = key in pack.closed_class_semantic_keys
                payload = RealizationSchema(
                    semantic_key=key,
                    language_tag=tag,
                    lemma=entry.lemma or entry.surface,
                    part_of_speech=entry.part_of_speech,
                    forms=FrozenMap({"base": entry.surface}),
                    semantic_schema_ref="" if closed else semantic_ref,
                    allowed_use_modes=frozenset({
                        "mention", "quote", "probe",
                        "qualified", "assert",
                    }),
                    closed_class=closed,
                    competence_test_refs=(
                        f"language_pack:{tag}:{pack.version}:round_trip",
                    ),
                )
                registered.append(self._register_active(
                    store,
                    f"language:{tag}:realization:{key}",
                    f"realize:{tag}:{key}",
                    "realization", payload, report,
                ))

            # Register template-based realizations so the lexical-use gate can
            # authorize predicates that have full template renderings but no
            # lexical entry of their own (e.g. informs, stores, completes).
            for realization in pack.realizations:
                pkey = realization.predicate_key
                rid = f"language:{tag}:realization:{pkey}"
                if store.get(rid) is not None:
                    continue
                sem_ref = self._record_for(store, pkey)
                rpayload = RealizationSchema(
                    semantic_key=pkey,
                    language_tag=tag,
                    lemma=pkey,
                    part_of_speech="verb",
                    forms=FrozenMap({"base": pkey}),
                    semantic_schema_ref=sem_ref,
                    allowed_use_modes=frozenset({
                        "mention", "quote", "probe",
                        "qualified", "assert",
                    }),
                    closed_class=False,
                    competence_test_refs=(
                        f"language_pack:{tag}:{pack.version}:template",
                    ),
                )
                registered.append(self._register_active(
                    store, rid,
                    f"realize:{tag}:{pkey}",
                    "realization", rpayload, report,
                ))
        return tuple(registered)

    def semantic_specs(self):
        return (
            {item["semantic_key"]: item for item in self.predicates},
            {item["semantic_key"]: item for item in self.entity_kinds},
        )

    def _register_active(
        self, store, record_id, semantic_key, schema_kind,
        payload, report, dependencies=(),
    ):
        if store.get(record_id) is not None:
            return record_id
        envelope = SchemaEnvelope(
            record_id=record_id,
            semantic_key=semantic_key,
            schema_kind=schema_kind,
            status="candidate",
            scope=Scope(level=ScopeLevel.GLOBAL),
            version=1,
            payload=payload,
            confidence=1.0,
            permission=Permission.public(),
            provenance=Provenance(
                source_id=f"definition_package:{report.fingerprint}",
                source_kind="audited_data_package",
                language_tag="und",
            ),
            support_refs=(f"validation:{report.fingerprint}",),
        )
        store.register(envelope, dependencies=dependencies)
        revision = store.get_revision(record_id)
        result = store.activate_with_assessment(
            record_id,
            revision,
            grounding_assessment_ref=(
                f"grounding:{report.fingerprint}:{record_id}"
            ),
            competence_assessment_ref=(
                f"competence:{report.fingerprint}:{record_id}"
            ),
            epistemic_admissibility_ref=(
                f"admissibility:{report.fingerprint}:{record_id}"
            ),
            environment_fingerprint=(
                f"definitions:{report.fingerprint}"
            ),
            grounding_assessment=_GroundingAssessment(),
            competence_assessment=_CompetenceAssessment(),
        )
        if getattr(result.status, "value", result.status) != "success":
            raise RuntimeError(
                f"could not activate {record_id}: {result.detail}"
            )
        return record_id

    @staticmethod
    def _record_for(store, semantic_key):
        if not semantic_key:
            return ""
        active = store.find_active(semantic_key)
        return active.record_id if active else ""

    def _json(self, relative):
        return json.loads(
            (self.root / relative).read_text(encoding="utf-8")
        )

def default_data_root():
    return Path(__file__).resolve().parents[2] / "data"
