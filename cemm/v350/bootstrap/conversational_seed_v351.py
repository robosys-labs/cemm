"""Signed deterministic conversational semantic/language bootstrap for CEMM v3.5.1.

The pack is intentionally small and high precision. It installs reusable semantic frames,
state/type structure, lexicalizations, and generic constructions. It does not seed named
entity instances or treat a word-frequency list as ontology.

The JSON bytes are release-attested before this function is called. Installation is idempotent
and occurs before public cognitive service begins; every installed active record therefore
participates in the store AuthorityGeneration pinned at Stage 0.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..language.model import (
    ConstructionKind,
    ConstructionProgramOperation,
    ConstructionProgramRecord,
    ConstructionProgramStep,
    ConstructionRecord,
    ConstructionSlot,
    FormKind,
    FormSenseLinkRecord,
    LanguageFormRecord,
    LanguagePackRecord,
    LexicalSenseRecord,
    SenseTargetKind,
)
from ..schema.model import (
    ActionSchema,
    MeaningSchema,
    OpenBindingPurpose,
    Cardinality,
    LocalPortSchema,
    ParentRevisionPolicy,
    PropertySchema,
    ReferentTypeSchema,
    RelationSchema,
    SchemaClass,
    SchemaLifecycleStatus,
    SchemaParentLink,
    SchemaProvenance,
    StateDimensionSchema,
    StateValueSchema,
    UseAuthorization,
    UseDecision,
    UseOperation,
    UseProfile,
    semantic_fingerprint,
)
from ..storage.codec import encode_record, record_fingerprints, record_ref, record_revision
from ..storage.model import (
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
)

CONVERSATIONAL_SEED_ABI = "cemm-conversational-seed-v351.1"
CONTEXTUAL_POLICY_REVIEW_REF = "review:canonical-policy:contextual-low-risk-v351"
CONTEXTUAL_POLICY_AUTHORIZATION_REF = "authorization:canonical-policy:contextual-low-risk-v351"


class ConversationalSeedError(RuntimeError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _schema_ref(kind: str, identifier: str) -> str:
    return f"schema:bootstrap:v351:{kind}:{identifier}"


def _type_ref(identifier: str) -> str:
    return _schema_ref("type", identifier)


def _target_ref(raw: str) -> str:
    family, _, identifier = raw.partition(":")
    if family == "type":
        return _type_ref(identifier)
    if family == "state" and ":" in identifier:
        return _schema_ref("state_value", identifier)
    return _schema_ref(family, identifier)


def _profile(*operations: UseOperation) -> UseProfile:
    return UseProfile(tuple(
        UseAuthorization(op, UseDecision.ALLOW, reason="reviewed conversational bootstrap")
        for op in operations
    ))


def _provenance(document: Mapping[str, Any]) -> SchemaProvenance:
    return SchemaProvenance(
        evidence_refs=(str(document["evidence_ref"]),),
        source_refs=(str(document["source_ref"]),),
        created_by=CONVERSATIONAL_SEED_ABI,
    )


def _port(name: str, type_ref: str, minimum: int) -> LocalPortSchema:
    return LocalPortSchema(
        port_ref=name,
        accepted_type_refs=(_type_ref(type_ref),),
        cardinality=Cardinality(minimum=minimum, maximum=1),
        queryable=True,
        role_family=name,
    )


def _compile_schemas(doc: Mapping[str, Any]):
    provenance = _provenance(doc)
    common_profile = _profile(
        UseOperation.MENTION, UseOperation.GROUND, UseOperation.COMPOSE,
        UseOperation.QUERY, UseOperation.INFER,
    )
    result = []
    for item in doc.get("types", ()):
        parents = ()
        if item.get("parent"):
            parents = (SchemaParentLink(
                parent_ref=_type_ref(str(item["parent"])),
                revision_policy=ParentRevisionPolicy.EXACT,
                revision=1,
            ),)
        result.append(ReferentTypeSchema(
            schema_ref=_type_ref(str(item["id"])),
            semantic_key="bootstrap:" + semantic_fingerprint(
                "bootstrap-type-key", str(item["id"]), 20
            ),
            parent_links=parents,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            revision=1,
            provenance=provenance,
            use_profile=common_profile,
            metadata=dict(item.get("metadata", {})),
        ))
    for item in doc.get("relations", ()):
        result.append(RelationSchema(
            schema_ref=_schema_ref("relation", str(item["id"])),
            semantic_key="bootstrap:" + semantic_fingerprint(
                "bootstrap-relation-key", str(item["id"]), 20
            ),
            local_ports=tuple(
                _port(str(port[0]), str(port[1]), int(port[2]))
                for port in item.get("ports", ())
            ),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            revision=1,
            provenance=provenance,
            use_profile=common_profile,
        ))
    # Value super-types used by state dimensions.
    for value_type in ("color_value", "texture_value", "size_value"):
        if not any(getattr(x, "schema_ref", "") == _type_ref(value_type) for x in result):
            result.append(ReferentTypeSchema(
                schema_ref=_type_ref(value_type),
                semantic_key="bootstrap:" + semantic_fingerprint(
                    "bootstrap-value-type-key", value_type, 20
                ),
                parent_links=(SchemaParentLink(
                    parent_ref=_type_ref("abstract_entity"),
                    revision_policy=ParentRevisionPolicy.EXACT,
                    revision=1,
                ),),
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                revision=1,
                provenance=provenance,
                use_profile=common_profile,
            ))
    for item in doc.get("states", ()):
        dim_ref = _schema_ref("state", str(item["id"]))
        values = tuple(
            _schema_ref("state_value", f"{item['id']}:{value}")
            for value in item.get("values", ())
        )
        for index, value in enumerate(item.get("values", ())):
            result.append(StateValueSchema(
                schema_ref=_schema_ref("state_value", f"{item['id']}:{value}"),
                semantic_key="bootstrap:" + semantic_fingerprint(
                    "bootstrap-state-value-key", (item["id"], value), 20
                ),
                dimension_ref=dim_ref,
                ordering_key=index,
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                revision=1,
                provenance=provenance,
                use_profile=common_profile,
            ))
        result.append(StateDimensionSchema(
            schema_ref=dim_ref,
            semantic_key="bootstrap:" + semantic_fingerprint(
                "bootstrap-state-key", str(item["id"]), 20
            ),
            holder_type_refs=(_type_ref(str(item["holder"])),),
            value_schema_refs=values,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            revision=1,
            provenance=provenance,
            use_profile=common_profile,
        ))
    for item in doc.get("properties", ()):
        result.append(PropertySchema(
            schema_ref=_schema_ref("property", str(item["id"])),
            semantic_key="bootstrap:" + semantic_fingerprint(
                "bootstrap-property-key", str(item["id"]), 20
            ),
            holder_type_refs=(_type_ref(str(item["holder"])),),
            value_type_refs=(_type_ref(str(item["value"])),),
            local_ports=(
                _port("holder", str(item["holder"]), 1),
                _port("value", str(item["value"]), 1),
            ),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            revision=1,
            provenance=provenance,
            use_profile=common_profile,
        ))
    action_profile = _profile(
        UseOperation.MENTION, UseOperation.GROUND, UseOperation.COMPOSE,
        UseOperation.QUERY, UseOperation.INFER, UseOperation.TRANSITION,
    )
    for item in doc.get("actions", ()):
        ports = tuple(
            _port(str(name), str(type_ref), int(minimum))
            for name, type_ref, minimum, *_ in item.get("ports", ())
        )
        result.append(ActionSchema(
            schema_ref=_schema_ref("action", str(item["id"])),
            semantic_key="bootstrap:" + semantic_fingerprint(
                "bootstrap-action-key", str(item["id"]), 20
            ),
            local_ports=ports,
            controlling_port_ref=ports[0].port_ref if ports else None,
            intentional_required=False,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            revision=1,
            provenance=provenance,
            use_profile=action_profile,
        ))
    return tuple(result)


def _active_english_pack(store):
    registry = store.repositories.language.registry()
    packs = tuple(
        item for item in registry.active_packs()
        if item.language_tag.casefold() == "en"
    )
    if len(packs) > 1:
        raise ConversationalSeedError(
            "conversational bootstrap requires a singular active English language pack"
        )
    return packs[0] if packs else None


def _compile_language(doc: Mapping[str, Any], store, schemas):
    provenance_source = str(doc["source_ref"])
    evidence_ref = str(doc["evidence_ref"])
    competence = (str(doc["competence_case_ref"]),)
    existing_pack = _active_english_pack(store)
    records = []
    if existing_pack is None:
        pack = LanguagePackRecord(
            pack_ref="language-pack:bootstrap:v351:en",
            language_tag="en",
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            scripts=("Latin",),
            tokenizer_profile="unicode_default",
            normalization_profile="nfkc_casefold",
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi":CONVERSATIONAL_SEED_ABI},
        )
        records.append((RecordKind.LANGUAGE_PACK, pack))
    else:
        pack = existing_pack

    schema_by_ref = {item.schema_ref: item for item in schemas}
    form_by_surface = {}
    target_entries = defaultdict(list)
    structural_entries = []

    for entry in doc.get("lexicalizations", ()):
        surface = str(entry["form"])
        normalized = surface.casefold()
        category = str(entry["category"])
        token_count = len(normalized.split())
        form_ref = "language-form:bootstrap:v351:" + semantic_fingerprint(
            "bootstrap-form-ref", (pack.pack_ref, pack.revision, normalized, category), 24
        )
        existing_form = form_by_surface.get(surface)
        if existing_form is not None and existing_form.form_ref == form_ref:
            form = existing_form
        else:
            form = LanguageFormRecord(
                form_ref=form_ref,
                pack_ref=pack.pack_ref,
                pack_revision=pack.revision,
                written_form=surface,
                normalized_form=normalized,
                form_kind=FormKind.MULTIWORD if token_count > 1 else FormKind.TOKEN,
                revision=1,
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                script="Latin",
                token_count=token_count,
                feature_values=(("category", category),),
                source_refs=(provenance_source,),
                evidence_refs=(evidence_ref,),
                permission_ref="public",
                metadata=dict(entry.get("metadata", {})),
            )
            records.append((RecordKind.LANGUAGE_FORM, form))
            form_by_surface[surface] = form
        if entry.get("target"):
            target_entries[str(entry["target"])].append((entry, form))
        elif entry.get("metadata", {}).get("structural_target"):
            structural_entries.append((entry, form))

    sense_by_target = {}
    for target, entries in sorted(target_entries.items()):
        target_ref = _target_ref(target)
        schema = schema_by_ref.get(target_ref)
        if schema is None:
            raise ConversationalSeedError(f"lexical target missing from seed schemas:{target}")
        first = entries[0][0]
        class_raw = str(first["target_class"])
        target_kind = (
            SenseTargetKind.REFERENT_TYPE
            if class_raw == "referent_type" else SenseTargetKind.SCHEMA
        )
        sense_ref = "lexical-sense:bootstrap:v351:" + semantic_fingerprint(
            "bootstrap-sense-ref", (pack.pack_ref, target_ref, schema.revision), 24
        )
        sense = LexicalSenseRecord(
            sense_ref=sense_ref,
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            target_kind=target_kind,
            target_ref=target_ref,
            target_revision=schema.revision,
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            target_schema_class=schema.schema_class,
            use_operation=UseOperation.GROUND,
            authorized_use_operations=(UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.QUERY),
            use_authority_explicit=True,
            lexical_category=str(first["category"]),
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi":CONVERSATIONAL_SEED_ABI},
        )
        records.append((RecordKind.LEXICAL_SENSE, sense))
        sense_by_target[target] = sense
        for entry, form in entries:
            link = FormSenseLinkRecord(
                link_ref="form-sense-link:bootstrap:v351:" + semantic_fingerprint(
                    "bootstrap-form-sense-ref", (form.form_ref, sense.sense_ref), 24
                ),
                form_ref=form.form_ref,
                form_revision=form.revision,
                sense_ref=sense.sense_ref,
                sense_revision=sense.revision,
                revision=1,
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                source_refs=(provenance_source,),
                evidence_refs=(evidence_ref,),
                permission_ref="public",
                metadata={"abi":CONVERSATIONAL_SEED_ABI},
            )
            records.append((RecordKind.FORM_SENSE_LINK, link))

    # Structural participant/deictic lexicalizations. These forms identify discourse roles,
    # not fixed referents and not ontology schemas.
    for entry, form in structural_entries:
        metadata = dict(entry.get("metadata", {}))
        target_ref = str(metadata["structural_target"])
        sense = LexicalSenseRecord(
            sense_ref="lexical-sense:bootstrap:v351:structural:" + semantic_fingerprint(
                "bootstrap-structural-sense-ref",
                (pack.pack_ref, form.form_ref, target_ref),
                24,
            ),
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            target_kind=SenseTargetKind.STRUCTURAL,
            target_ref=target_ref,
            target_revision=None,
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            target_schema_class=None,
            use_operation=UseOperation.GROUND,
            authorized_use_operations=(UseOperation.GROUND,),
            use_authority_explicit=True,
            lexical_category=str(entry["category"]),
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={
                **metadata,
                "abi": CONVERSATIONAL_SEED_ABI,
            },
        )
        link = FormSenseLinkRecord(
            link_ref="form-sense-link:bootstrap:v351:structural:" + semantic_fingerprint(
                "bootstrap-structural-form-sense-ref",
                (form.form_ref, sense.sense_ref),
                24,
            ),
            form_ref=form.form_ref,
            form_revision=form.revision,
            sense_ref=sense.sense_ref,
            sense_revision=sense.revision,
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            permission_ref="public",
            metadata={"abi": CONVERSATIONAL_SEED_ABI},
        )
        records.extend((
            (RecordKind.LEXICAL_SENSE, sense),
            (RecordKind.FORM_SENSE_LINK, link),
        ))

    # Generic action constructions, one per semantic frame. Unknown observations are explicitly
    # licensed as candidate fillers; exact port/type semantics later constrain them.
    for action in doc.get("actions", ()):
        target = f"action:{action['id']}"
        sense = sense_by_target.get(target)
        if sense is None:
            continue
        slots = []
        open_slots = {}
        steps = [ConstructionProgramStep(
            step_ref="instantiate",
            operation=ConstructionProgramOperation.INSTANTIATE_SCHEMA,
            result_ref="root",
            schema_ref=_schema_ref("action", str(action["id"])),
            schema_revision=1,
        )]
        for raw_port in action.get("ports", ()):
            name, _type_ref_raw, minimum = raw_port[:3]
            relative_position = str(raw_port[3]) if len(raw_port) > 3 else "either"
            linear_rank = int(raw_port[4]) if len(raw_port) > 4 and raw_port[4] is not None else None
            slot_name = str(name)
            slots.append(ConstructionSlot(
                slot_ref=slot_name,
                minimum=int(minimum),
                maximum=1,
                accepted_categories=("noun","pronoun","proper_noun"),
                optional_when_licensed=int(minimum) == 0,
                semantic_port_ref=slot_name,
                relative_position=relative_position,
                linear_rank=linear_rank,
            ))
            open_slots[slot_name] = {"observation_categories":("word",)}
            steps.append(ConstructionProgramStep(
                step_ref=f"bind:{slot_name}",
                operation=ConstructionProgramOperation.BIND_PORT_FROM_SLOT,
                input_refs=("root",),
                slot_ref=slot_name,
                port_ref=slot_name,
            ))
        construction = ConstructionRecord(
            construction_ref="construction:bootstrap:v351:action:" + str(action["id"]),
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
            slots=tuple(slots),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            trigger_sense_refs=(sense.sense_ref,),
            output_schema_ref=_schema_ref("action", str(action["id"])),
            output_schema_revision=1,
            output_schema_class=SchemaClass.ACTION,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={
                "open_observation_slots":open_slots,
                "abi":CONVERSATIONAL_SEED_ABI,
            },
        )
        program = ConstructionProgramRecord(
            program_ref=construction.construction_ref + ":program",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_ref=construction.construction_ref,
            construction_revision=construction.revision,
            steps=tuple(steps),
            root_symbol_refs=("root",),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_operation=UseOperation.COMPOSE,
            use_decision=UseDecision.ALLOW,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi":CONVERSATIONAL_SEED_ABI},
        )
        records.extend(((RecordKind.CONSTRUCTION, construction),(RecordKind.CONSTRUCTION_PROGRAM, program)))

    # Participant name assertion: "<possessive> name ... <value>".
    # The value may be an unresolved surface; exact property-port constraints type the provisional
    # referent as information for this occurrence without globally assigning lexical meaning.
    name_form = form_by_surface.get("name")
    if name_form is not None:
        name_schema = schema_by_ref[_schema_ref("property", "name")]
        name_assertion = ConstructionRecord(
            construction_ref="construction:bootstrap:v351:property:name:assert",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
            slots=(
                ConstructionSlot(
                    slot_ref="holder", minimum=1, maximum=1,
                    accepted_categories=("possessive",),
                    semantic_port_ref="holder",
                    relative_position="before", linear_rank=0,
                ),
                ConstructionSlot(
                    slot_ref="value", minimum=1, maximum=1,
                    accepted_categories=("noun", "proper_noun", "word"),
                    semantic_port_ref="value",
                    relative_position="after", linear_rank=0,
                ),
            ),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            trigger_form_refs=(name_form.form_ref,),
            output_schema_ref=name_schema.schema_ref,
            output_schema_revision=name_schema.revision,
            output_schema_class=name_schema.schema_class,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={
                "open_observation_slots": {
                    "value": {"observation_categories": ("word",)}
                },
                "identity_introduction_slots": ("value",),
                "abi": CONVERSATIONAL_SEED_ABI,
            },
        )
        name_assertion_program = ConstructionProgramRecord(
            program_ref=name_assertion.construction_ref + ":program",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_ref=name_assertion.construction_ref,
            construction_revision=1,
            steps=(
                ConstructionProgramStep(
                    step_ref="instantiate:name",
                    operation=ConstructionProgramOperation.INSTANTIATE_SCHEMA,
                    result_ref="root",
                    schema_ref=name_schema.schema_ref,
                    schema_revision=name_schema.revision,
                ),
                ConstructionProgramStep(
                    step_ref="bind:holder",
                    operation=ConstructionProgramOperation.BIND_PORT_FROM_SLOT,
                    input_refs=("root",), slot_ref="holder", port_ref="holder",
                ),
                ConstructionProgramStep(
                    step_ref="bind:value",
                    operation=ConstructionProgramOperation.BIND_PORT_FROM_SLOT,
                    input_refs=("root",), slot_ref="value", port_ref="value",
                ),
            ),
            root_symbol_refs=("root",),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_operation=UseOperation.COMPOSE,
            use_decision=UseDecision.ALLOW,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi": CONVERSATIONAL_SEED_ABI},
        )
        records.extend((
            (RecordKind.CONSTRUCTION, name_assertion),
            (RecordKind.CONSTRUCTION_PROGRAM, name_assertion_program),
        ))

        # "what ... <possessive> name" -> query(name(holder, ?value))
        what_form = form_by_surface.get("what")
        if what_form is not None:
            name_query = ConstructionRecord(
                construction_ref="construction:bootstrap:v351:property:name:query",
                pack_ref=pack.pack_ref,
                pack_revision=pack.revision,
                construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
                slots=(
                    ConstructionSlot(
                        slot_ref="question", minimum=1, maximum=1,
                        accepted_categories=("wh",),
                        relative_position="before", linear_rank=0,
                    ),
                    ConstructionSlot(
                        slot_ref="holder", minimum=1, maximum=1,
                        accepted_categories=("possessive",),
                        semantic_port_ref="holder",
                        relative_position="before", linear_rank=0,
                    ),
                ),
                revision=1,
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                trigger_form_refs=(name_form.form_ref,),
                output_schema_ref=name_schema.schema_ref,
                output_schema_revision=name_schema.revision,
                output_schema_class=name_schema.schema_class,
                source_refs=(provenance_source,),
                evidence_refs=(evidence_ref,),
                competence_case_refs=competence,
                permission_ref="public",
                metadata={"abi": CONVERSATIONAL_SEED_ABI},
            )
            name_query_program = ConstructionProgramRecord(
                program_ref=name_query.construction_ref + ":program",
                pack_ref=pack.pack_ref,
                pack_revision=pack.revision,
                construction_ref=name_query.construction_ref,
                construction_revision=1,
                steps=(
                    ConstructionProgramStep(
                        step_ref="introduce:value",
                        operation=ConstructionProgramOperation.INTRODUCE_VARIABLE,
                        result_ref="value",
                        open_binding_purpose=OpenBindingPurpose.QUERY,
                    ),
                    ConstructionProgramStep(
                        step_ref="instantiate:name",
                        operation=ConstructionProgramOperation.INSTANTIATE_SCHEMA,
                        result_ref="prop",
                        schema_ref=name_schema.schema_ref,
                        schema_revision=name_schema.revision,
                    ),
                    ConstructionProgramStep(
                        step_ref="bind:holder",
                        operation=ConstructionProgramOperation.BIND_PORT_FROM_SLOT,
                        input_refs=("prop",), slot_ref="holder", port_ref="holder",
                    ),
                    ConstructionProgramStep(
                        step_ref="bind:value",
                        operation=ConstructionProgramOperation.BIND_PORT_FROM_SYMBOL,
                        input_refs=("prop", "value"), port_ref="value",
                    ),
                    ConstructionProgramStep(
                        step_ref="wrap:query",
                        operation=ConstructionProgramOperation.WRAP_DISCOURSE_ACT,
                        input_refs=("prop",),
                        result_ref="query",
                        schema_ref="discourse:query",
                        schema_revision=1,
                        port_ref="content",
                    ),
                ),
                root_symbol_refs=("query",),
                revision=1,
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                use_operation=UseOperation.COMPOSE,
                use_decision=UseDecision.ALLOW,
                source_refs=(provenance_source,),
                evidence_refs=(evidence_ref,),
                competence_case_refs=competence,
                permission_ref="public",
                metadata={"abi": CONVERSATIONAL_SEED_ABI},
            )
            records.extend((
                (RecordKind.CONSTRUCTION, name_query),
                (RecordKind.CONSTRUCTION_PROGRAM, name_query_program),
            ))

    # "how ... you" -> query(condition(you, ?value)); this is language-pack projection data,
    # not a core semantic branch. If no state/belief is known, the normal query path says so.
    how_form = form_by_surface.get("how")
    if how_form is not None:
        condition_schema = schema_by_ref[_schema_ref("property", "condition")]
        how_query = ConstructionRecord(
            construction_ref="construction:bootstrap:v351:property:condition:how-query",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
            slots=(ConstructionSlot(
                slot_ref="holder", minimum=1, maximum=1,
                accepted_categories=("pronoun",),
                semantic_port_ref="holder",
                relative_position="after", linear_rank=0,
            ),),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            trigger_form_refs=(how_form.form_ref,),
            output_schema_ref=condition_schema.schema_ref,
            output_schema_revision=condition_schema.revision,
            output_schema_class=condition_schema.schema_class,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi": CONVERSATIONAL_SEED_ABI},
        )
        how_query_program = ConstructionProgramRecord(
            program_ref=how_query.construction_ref + ":program",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_ref=how_query.construction_ref,
            construction_revision=1,
            steps=(
                ConstructionProgramStep(
                    step_ref="introduce:value",
                    operation=ConstructionProgramOperation.INTRODUCE_VARIABLE,
                    result_ref="value",
                    open_binding_purpose=OpenBindingPurpose.QUERY,
                ),
                ConstructionProgramStep(
                    step_ref="instantiate:condition",
                    operation=ConstructionProgramOperation.INSTANTIATE_SCHEMA,
                    result_ref="prop",
                    schema_ref=condition_schema.schema_ref,
                    schema_revision=condition_schema.revision,
                ),
                ConstructionProgramStep(
                    step_ref="bind:holder",
                    operation=ConstructionProgramOperation.BIND_PORT_FROM_SLOT,
                    input_refs=("prop",), slot_ref="holder", port_ref="holder",
                ),
                ConstructionProgramStep(
                    step_ref="bind:value",
                    operation=ConstructionProgramOperation.BIND_PORT_FROM_SYMBOL,
                    input_refs=("prop", "value"), port_ref="value",
                ),
                ConstructionProgramStep(
                    step_ref="wrap:query",
                    operation=ConstructionProgramOperation.WRAP_DISCOURSE_ACT,
                    input_refs=("prop",),
                    result_ref="query",
                    schema_ref="discourse:query",
                    schema_revision=1,
                    port_ref="content",
                ),
            ),
            root_symbol_refs=("query",),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_operation=UseOperation.COMPOSE,
            use_decision=UseDecision.ALLOW,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi": CONVERSATIONAL_SEED_ABI},
        )
        records.extend((
            (RecordKind.CONSTRUCTION, how_query),
            (RecordKind.CONSTRUCTION_PROGRAM, how_query_program),
        ))

    # Greeting discourse construction. The semantic definition itself is supplied by the
    # signed canonical minimum_discourse_v351 authority set, not duplicated in storage schemas.
    greeting_forms = tuple(
        form_by_surface[value] for value in ("hello", "hi", "hey")
        if value in form_by_surface
    )
    if greeting_forms:
        construction = ConstructionRecord(
            construction_ref="construction:bootstrap:v351:discourse:greeting",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
            slots=(ConstructionSlot(
                slot_ref="greeting_form",
                minimum=1,
                maximum=1,
                accepted_categories=("greeting",),
            ),),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            trigger_form_refs=tuple(item.form_ref for item in greeting_forms),
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi":CONVERSATIONAL_SEED_ABI},
        )
        program = ConstructionProgramRecord(
            program_ref=construction.construction_ref + ":program",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_ref=construction.construction_ref,
            construction_revision=construction.revision,
            steps=(ConstructionProgramStep(
                step_ref="wrap:greeting",
                operation=ConstructionProgramOperation.INSTANTIATE_SCHEMA,
                result_ref="root",
                schema_ref="discourse:greeting",
                schema_revision=1,
            ),),
            root_symbol_refs=("root",),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_operation=UseOperation.COMPOSE,
            use_decision=UseDecision.ALLOW,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi":CONVERSATIONAL_SEED_ABI},
        )
        records.extend((
            (RecordKind.CONSTRUCTION, construction),
            (RecordKind.CONSTRUCTION_PROGRAM, program),
        ))

    # Data-authorized subtype teaching: "<unknown> is/are/was/were <known type>".
    classification = schema_by_ref[_schema_ref("relation","classification")]
    for copula in ("is","are","was","were"):
        trigger = form_by_surface.get(copula)
        if trigger is None:
            continue
        construction = ConstructionRecord(
            construction_ref=f"construction:bootstrap:v351:definition:{copula}",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
            slots=(
                ConstructionSlot(
                    slot_ref="form", minimum=1, maximum=1,
                    accepted_categories=("noun","word"),
                    relative_position="before", linear_rank=0,
                ),
                ConstructionSlot(
                    slot_ref="parent", minimum=1, maximum=1,
                    accepted_categories=("noun",),
                    accepted_target_classes=(SchemaClass.REFERENT_TYPE,),
                    semantic_port_ref="class",
                    relative_position="after", linear_rank=0,
                ),
            ),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            trigger_form_refs=(trigger.form_ref,),
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={
                "open_observation_slots":{"form":{"observation_categories":("word",)}},
                "semantic_definition_projection_v351":{
                    "form_slot_ref":"form",
                    "parent_slot_ref":"parent",
                    "definition_relation":"subtype",
                    "competence_case_refs":[
                        "competence:contextual-lexical-ground-v351",
                        "competence:contextual-lexical-compose-v351",
                        "competence:contextual-lexical-query-v351",
                    ],
                    "requested_uses":[
                        {"operation":"ground","decision":"allow"},
                        {"operation":"compose","decision":"allow"},
                        {"operation":"query","decision":"allow"},
                    ],
                    "review_refs":[CONTEXTUAL_POLICY_REVIEW_REF],
                    "authorization_refs":[CONTEXTUAL_POLICY_AUTHORIZATION_REF],
                    "promotion_policy_ref":"policy:v351:contextual-low-risk",
                },
                "abi":CONVERSATIONAL_SEED_ABI,
            },
        )
        program = ConstructionProgramRecord(
            program_ref=construction.construction_ref + ":program",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_ref=construction.construction_ref,
            construction_revision=1,
            steps=(
                ConstructionProgramStep(
                    step_ref="instantiate",
                    operation=ConstructionProgramOperation.INSTANTIATE_SCHEMA,
                    result_ref="root",
                    schema_ref=classification.schema_ref,
                    schema_revision=classification.revision,
                ),
                ConstructionProgramStep(
                    step_ref="bind:class",
                    operation=ConstructionProgramOperation.BIND_PORT_FROM_SLOT,
                    input_refs=("root",),
                    slot_ref="parent",
                    port_ref="class",
                ),
            ),
            root_symbol_refs=("root",),
            revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_operation=UseOperation.COMPOSE,
            use_decision=UseDecision.ALLOW,
            source_refs=(provenance_source,),
            evidence_refs=(evidence_ref,),
            competence_case_refs=competence,
            permission_ref="public",
            metadata={"abi":CONVERSATIONAL_SEED_ABI},
        )
        records.extend(((RecordKind.CONSTRUCTION,construction),(RecordKind.CONSTRUCTION_PROGRAM,program)))
    return tuple(records)


def _dependency(kind, ref, revision, fingerprint, why):
    return RecordDependency(kind, ref, revision, fingerprint, why)


def _plan_record(store, kind, record, staged_fps):
    ref = record_ref(kind, record)
    revision = record_revision(kind, record)
    existing = store.get_record(kind, ref, revision)
    fingerprint = record_fingerprints(kind, record)[1]
    if existing is not None:
        if existing.record_fingerprint != fingerprint:
            raise ConversationalSeedError(
                f"signed conversational seed collides with existing exact record:{kind.value}:{ref}@{revision}"
            )
        return None, fingerprint
    deps = []
    if isinstance(record, MeaningSchema):
        dependency_refs = set()
        for parent in record.parent_links:
            if parent.revision_policy is not ParentRevisionPolicy.EXACT or parent.revision is None:
                raise ConversationalSeedError(
                    f"bootstrap schema parent must be exact:{record.schema_ref}:{parent.parent_ref}"
                )
            dependency_refs.add((parent.parent_ref, parent.revision, "schema_parent"))
        for port in record.local_ports:
            dependency_refs.update(
                (ref, 1, f"port_type:{port.port_ref}") for ref in port.accepted_type_refs
            )
            dependency_refs.update(
                (ref, 1, f"port_constraint:{port.port_ref}") for ref in port.constraint_refs
            )
        if isinstance(record, PropertySchema):
            dependency_refs.update((ref,1,"property_holder_type") for ref in record.holder_type_refs)
            dependency_refs.update((ref,1,"property_value_type") for ref in record.value_type_refs)
            dependency_refs.update((ref,1,"property_value_schema") for ref in record.value_schema_refs)
        if isinstance(record, StateDimensionSchema):
            dependency_refs.update((ref,1,"state_holder_type") for ref in record.holder_type_refs)
            dependency_refs.update((ref,1,"state_value_schema") for ref in record.value_schema_refs)
        if isinstance(record, StateValueSchema):
            dependency_refs.add((record.dimension_ref,1,"state_dimension"))
        for schema_ref, schema_revision, why in sorted(dependency_refs):
            key=(RecordKind.SCHEMA,schema_ref,int(schema_revision))
            fp=staged_fps.get(key)
            stored=store.get_record(*key)
            if fp is None and stored is not None:
                fp=stored.record_fingerprint
            if not fp:
                raise ConversationalSeedError(
                    f"seed schema dependency missing:{record.schema_ref}:{key}:{why}"
                )
            deps.append(_dependency(*key,fp,why))
    if isinstance(record, LanguageFormRecord):
        key=(RecordKind.LANGUAGE_PACK,record.pack_ref,record.pack_revision)
        fp=staged_fps.get(key) or getattr(store.get_record(*key),"record_fingerprint",None)
        if not fp: raise ConversationalSeedError(f"seed language pack missing:{key}")
        deps.append(_dependency(*key,fp,"language_pack"))
    elif isinstance(record, LexicalSenseRecord):
        keys = [
            ((RecordKind.LANGUAGE_PACK, record.pack_ref, record.pack_revision), "language_pack")
        ]
        if record.target_revision is not None and record.target_ref is not None:
            keys.append((
                (RecordKind.SCHEMA, str(record.target_ref), int(record.target_revision)),
                "lexical_target",
            ))
        for key,why in keys:
            fp=staged_fps.get(key) or getattr(store.get_record(*key),"record_fingerprint",None)
            if not fp: raise ConversationalSeedError(f"seed dependency missing:{key}")
            deps.append(_dependency(*key,fp,why))
    elif isinstance(record, FormSenseLinkRecord):
        for key,why in (
            ((RecordKind.LANGUAGE_FORM,record.form_ref,record.form_revision),"form"),
            ((RecordKind.LEXICAL_SENSE,record.sense_ref,record.sense_revision),"sense"),
        ):
            fp=staged_fps.get(key) or getattr(store.get_record(*key),"record_fingerprint",None)
            if not fp: raise ConversationalSeedError(f"seed dependency missing:{key}")
            deps.append(_dependency(*key,fp,why))
    elif isinstance(record, ConstructionRecord):
        key=(RecordKind.LANGUAGE_PACK,record.pack_ref,record.pack_revision)
        fp=staged_fps.get(key) or getattr(store.get_record(*key),"record_fingerprint",None)
        if not fp: raise ConversationalSeedError(f"seed construction pack missing:{key}")
        deps.append(_dependency(*key,fp,"language_pack"))
        for trigger_ref in record.trigger_form_refs:
            stored=store.get_record(RecordKind.LANGUAGE_FORM,trigger_ref)
            candidates=[
                (key,fp) for key,fp in staged_fps.items()
                if key[0] is RecordKind.LANGUAGE_FORM and key[1]==trigger_ref
            ]
            if stored is not None:
                deps.append(_dependency(RecordKind.LANGUAGE_FORM,trigger_ref,stored.revision,stored.record_fingerprint,"construction_trigger"))
            elif candidates:
                key,fp=max(candidates,key=lambda item:item[0][2]); deps.append(_dependency(*key,fp,"construction_trigger"))
        for trigger_ref in record.trigger_sense_refs:
            candidates=[
                (key,fp) for key,fp in staged_fps.items()
                if key[0] is RecordKind.LEXICAL_SENSE and key[1]==trigger_ref
            ]
            stored=store.get_record(RecordKind.LEXICAL_SENSE,trigger_ref)
            if stored is not None:
                deps.append(_dependency(RecordKind.LEXICAL_SENSE,trigger_ref,stored.revision,stored.record_fingerprint,"construction_trigger"))
            elif candidates:
                key,fp=max(candidates,key=lambda item:item[0][2]); deps.append(_dependency(*key,fp,"construction_trigger"))
    elif isinstance(record, ConstructionProgramRecord):
        for key,why in (
            ((RecordKind.LANGUAGE_PACK,record.pack_ref,record.pack_revision),"language_pack"),
            ((RecordKind.CONSTRUCTION,record.construction_ref,record.construction_revision),"construction"),
        ):
            fp=staged_fps.get(key) or getattr(store.get_record(*key),"record_fingerprint",None)
            if not fp: raise ConversationalSeedError(f"seed program dependency missing:{key}")
            deps.append(_dependency(*key,fp,why))
        for step in record.steps:
            if step.schema_ref and step.schema_revision:
                key=(RecordKind.SCHEMA,step.schema_ref,step.schema_revision)
                fp=staged_fps.get(key) or getattr(store.get_record(*key),"record_fingerprint",None)
                if fp:
                    deps.append(_dependency(*key,fp,"program_schema"))
                elif not step.schema_ref.startswith("discourse:"):
                    raise ConversationalSeedError(f"seed program schema missing:{key}")
    return PatchOperation(
        operation_ref="patch-operation:conversational-seed:" + semantic_fingerprint(
            "conversational-seed-op",(kind.value,ref,revision,fingerprint),20
        ),
        operation_kind=PatchOperationKind.UPSERT,
        record_kind=kind,
        target_ref=ref,
        record_revision=revision,
        payload=encode_record(kind,record),
        dependencies=tuple(deps),
        reason="install exact release-attested conversational bootstrap authority",
    ), fingerprint


def install_signed_conversational_seed_v351(
    store, path: str | Path, *, expected_sha256: str
):
    raw=Path(path).read_bytes()
    if not expected_sha256 or _sha(raw)!=expected_sha256:
        raise ConversationalSeedError("conversational seed hash differs from release authority")
    doc=json.loads(raw.decode("utf-8"))
    if int(doc.get("schema_version",0))!=1:
        raise ConversationalSeedError("unsupported conversational seed schema")
    schemas=_compile_schemas(doc)
    language=_compile_language(doc,store,schemas)
    ordered=[
        *((RecordKind.SCHEMA,x) for x in schemas),
        *language,
    ]
    staged_fps={}
    # Pre-populate fingerprints for all schema records to resolve inter-schema
    # dependencies (e.g. StateDimensionSchema <-> StateValueSchema).
    for kind, record in ordered:
        if kind is RecordKind.SCHEMA:
            key = (kind, record_ref(kind, record), record_revision(kind, record))
            staged_fps[key] = record_fingerprints(kind, record)[1]
    operations=[]
    for kind,record in ordered:
        op,fp=_plan_record(store,kind,record,staged_fps)
        key=(kind,record_ref(kind,record),record_revision(kind,record))
        staged_fps[key]=fp
        if op is not None: operations.append(op)
    if not operations:
        return None
    with store.snapshot() as snapshot:
        patch=GraphPatch(
            patch_ref="graph-patch:conversational-seed:" + semantic_fingerprint(
                "conversational-seed-patch",
                (doc["seed_ref"],expected_sha256,tuple(op.operation_ref for op in operations)),
                24,
            ),
            context_ref="bootstrap:conversational",
            scope_ref="global",
            source_ref=str(doc["source_ref"]),
            permission_ref="public",
            operations=tuple(operations),
            expected_store_revision=snapshot.store_revision,
            validation_requirements=(
                "release_attested_conversational_seed",
                "exact_bootstrap_authority",
                "no_named_entity_instance_seeding",
            ),
            metadata={
                "authoritative_bootstrap":True,
                "seed_ref":str(doc["seed_ref"]),
                "seed_sha256":expected_sha256,
                "abi":CONVERSATIONAL_SEED_ABI,
            },
        )
    result=store.apply_patch(patch)
    if not getattr(result,"committed",False):
        raise ConversationalSeedError(
            "failed to install conversational bootstrap:"+";".join(getattr(result,"errors",()) or ())
        )
    return result


__all__=[
    "CONVERSATIONAL_SEED_ABI",
    "CONTEXTUAL_POLICY_REVIEW_REF",
    "CONTEXTUAL_POLICY_AUTHORIZATION_REF",
    "ConversationalSeedError",
    "install_signed_conversational_seed_v351",
]
