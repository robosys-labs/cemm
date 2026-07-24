"""Deterministic restart projection of CEMM v3.5.1 split semantic authority.

This module is the canonical bridge between persisted/promoted authority and the immutable
AuthoritySnapshotV351 pinned at Stage 0.  It does not invent lexical or ontology meaning:
semantic definitions are projected from exact revisioned MeaningSchema content; lifecycle/use
authority remains in separate OperationalProfile/UseAuthorization artifacts; language records
are auxiliary projection authority; optional multimodal ObservationModels come only from an
explicit signed supplement.

The same store AuthorityGeneration must deterministically produce the same snapshot fingerprint
across process restart.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .authority_v351 import (
    AuthoritySnapshotV351,
    DynamicsParameterArtifact,
    FormalPort,
    ObservationModel,
    OperationalProfile,
    SemanticAuthorityError,
    SemanticDefinition,
    UseAuthorization,
)
from .model import (
    CSIRGraph,
    CSIRNodeKind,
    CSIRRef,
    ExactAuthorityPin,
    PortBinding,
    SemanticApplication,
    SemanticVariable,
)
from ..schema.model import (
    MeaningSchema,
    ParentRevisionPolicy,
    PortFillerClass,
    SchemaLifecycleStatus,
    UseDecision,
    canonical_data,
    semantic_fingerprint,
)
from ..storage.model import RecordKind

SEMANTIC_AUTHORITY_PROJECTION_ABI = "cemm-runtime-semantic-authority-projection-v351.1"
SEMANTIC_AUTHORITY_SUPPLEMENT_SCHEMA = 1


class RuntimeSemanticAuthorityProjectionError(SemanticAuthorityError):
    pass


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _definition_pin(schema: MeaningSchema, content_hash: str | None = None) -> ExactAuthorityPin:
    # Lifecycle/use/permission/provenance remain outside semantic identity. Resolved floating
    # parent/schema dependencies are folded into content_hash by _effective_schema_hash.
    return ExactAuthorityPin(
        "semantic_definition", "cemm.schema", schema.schema_ref, schema.revision,
        content_hash or schema.content_fingerprint, "global",
    )


def _effective_schema_hash(schema: MeaningSchema, registry, memo: dict, visiting: set) -> str:
    key = (schema.schema_ref, schema.revision)
    if key in memo:
        return memo[key]
    if key in visiting:
        raise RuntimeSemanticAuthorityProjectionError(
            f"semantic schema dependency cycle prevents exact authority projection:{key}"
        )
    visiting.add(key)
    resolved = []
    for link in schema.parent_links:
        parent = (
            registry.schema(link.parent_ref, link.revision)
            if link.revision_policy is ParentRevisionPolicy.EXACT
            else registry.resolve_parent(link)
        )
        resolved.append(
            ("parent", parent.schema_ref, parent.revision,
             _effective_schema_hash(parent, registry, memo, visiting))
        )
    for dep in schema.dependencies:
        if not dep.required:
            continue
        try:
            target = _schema_exact(registry, dep.dependency_ref, dep.exact_revision)
        except KeyError:
            continue
        if dep.minimum_revision is not None and target.revision < dep.minimum_revision:
            raise RuntimeSemanticAuthorityProjectionError(
                f"schema dependency revision below minimum:{schema.schema_ref}@{schema.revision}:"
                f"{dep.dependency_ref}@{target.revision}<{dep.minimum_revision}"
            )
        resolved.append(
            ("schema_dependency", dep.dependency_kind, target.schema_ref, target.revision,
             _effective_schema_hash(target, registry, memo, visiting))
        )
    visiting.remove(key)
    value = _sha((schema.content_fingerprint, tuple(sorted(resolved))))
    memo[key] = value
    return value


def _port_pin(schema: MeaningSchema, port) -> ExactAuthorityPin:
    payload = {
        "schema_ref": schema.schema_ref,
        "schema_revision": schema.revision,
        "port_ref": port.port_ref,
        "filler_classes": tuple(sorted(item.value for item in port.filler_classes)),
        "accepted_type_refs": tuple(sorted(port.accepted_type_refs)),
        "accepted_storage_kinds": tuple(sorted(item.value for item in port.accepted_storage_kinds)),
        "accepted_schema_classes": tuple(sorted(item.value for item in port.accepted_schema_classes)),
        "cardinality": (port.cardinality.minimum, port.cardinality.maximum),
        "queryable": bool(port.queryable),
        "open_binding_purposes": tuple(sorted(item.value for item in port.open_binding_purposes)),
        "role_family": port.role_family,
        "context_policy": port.context_policy,
        "time_policy": port.time_policy,
        "identity_contribution": bool(port.identity_contribution),
        "ordered_fillers": bool(port.ordered_fillers),
        "constraint_refs": tuple(sorted(port.constraint_refs)),
    }
    return ExactAuthorityPin(
        "semantic_port", f"cemm.schema:{schema.schema_ref}", port.port_ref, schema.revision,
        semantic_fingerprint("semantic-port-content", payload, 64), "global",
    )


def _allowed_node_kinds(filler_classes: Iterable[PortFillerClass]) -> frozenset[CSIRNodeKind]:
    result: set[CSIRNodeKind] = set()
    for item in filler_classes:
        if item in {PortFillerClass.REFERENT, PortFillerClass.QUOTED_LITERAL}:
            result.add(CSIRNodeKind.TERM)
        elif item is PortFillerClass.SEMANTIC_APPLICATION:
            result.add(CSIRNodeKind.APPLICATION)
        elif item is PortFillerClass.COORDINATION_GROUP:
            result.add(CSIRNodeKind.COORDINATION)
        elif item is PortFillerClass.SEMANTIC_VARIABLE:
            # A formal variable may be bound to concrete semantic nodes; variables are not
            # permitted as variable allowed_kinds by the CSIR kernel.
            result.update({CSIRNodeKind.TERM, CSIRNodeKind.APPLICATION, CSIRNodeKind.COORDINATION})
    return frozenset(result or {CSIRNodeKind.TERM, CSIRNodeKind.APPLICATION, CSIRNodeKind.COORDINATION})


def _context_scopes(scope_ref: str) -> tuple[str, ...]:
    return () if scope_ref in {"", "global"} else (scope_ref,)


def _permission_scopes(permission_ref: str) -> tuple[str, ...]:
    # "public" is universal permission authority, not a context name.
    return () if permission_ref in {"", "public"} else (permission_ref,)


def _schema_exact(registry, ref: str, revision: int | None = None):
    if revision is not None:
        return registry.schema(ref, revision)
    return registry.authoritative_schema(ref)


def _resolve_schema_dependency(
    registry, definition_pins, ref: str, revision: int | None, minimum_revision: int | None = None
):
    try:
        target = _schema_exact(registry, ref, revision)
    except KeyError:
        return None
    if minimum_revision is not None and target.revision < minimum_revision:
        return None
    return definition_pins.get((target.schema_ref, target.revision))


def _resolve_stored_exact_pin(
    store,
    snapshot,
    ref: str,
    *,
    exact_revision: int | None = None,
    minimum_revision: int | None = None,
) -> ExactAuthorityPin | None:
    """Resolve one exact non-schema authority record without interpreting its name."""
    candidates = []
    for kind in RecordKind:
        if exact_revision is not None:
            item = store.get_record(kind, ref, exact_revision, snapshot=snapshot)
            if item is not None and not store.is_invalidated(
                item.record_kind, item.record_ref, item.revision, snapshot=snapshot
            ):
                candidates.append(item)
            continue
        for item in store.records(kind, all_revisions=True, snapshot=snapshot):
            if item.record_ref != ref:
                continue
            if minimum_revision is not None and item.revision < minimum_revision:
                continue
            if store.is_invalidated(
                item.record_kind, item.record_ref, item.revision, snapshot=snapshot
            ):
                continue
            candidates.append(item)
    if not candidates:
        return None
    kinds = {item.record_kind for item in candidates}
    if len(kinds) != 1:
        raise RuntimeSemanticAuthorityProjectionError(
            f"exact non-schema authority ref is cross-kind ambiguous:{ref}:"
            f"{sorted(kind.value for kind in kinds)}"
        )
    selected = max(candidates, key=lambda item: item.revision)
    return ExactAuthorityPin(
        selected.record_kind.value,
        "cemm.store",
        selected.record_ref,
        selected.revision,
        selected.record_fingerprint,
        "global",
    )


def _language_pin(kind: str, item, ref_attr: str) -> ExactAuthorityPin:
    ref = str(getattr(item, ref_attr))
    revision = int(getattr(item, "revision"))
    content_hash = str(getattr(item, "record_fingerprint", "") or semantic_fingerprint(f"{kind}-record", item, 64))
    return ExactAuthorityPin(kind, "cemm.language", ref, revision, content_hash, "global")


_LANGUAGE_COLLECTIONS = (
    ("packs", "language_pack", "pack_ref"),
    ("forms", "language_form", "form_ref"),
    ("lexemes", "lexeme", "lexeme_ref"),
    ("form_lexeme_links", "form_lexeme_link", "link_ref"),
    ("senses", "lexical_sense", "sense_ref"),
    ("lexeme_sense_links", "lexeme_sense_link", "link_ref"),
    ("links", "form_sense_link", "link_ref"),
    ("contribution_specs", "semantic_contribution_spec", "spec_ref"),
    ("morphology_analysis_rules", "morphology_analysis_rule", "rule_ref"),
    ("constructions", "construction", "construction_ref"),
    ("construction_programs", "construction_program", "program_ref"),
)


def _competence_pin(schema: MeaningSchema, hook) -> ExactAuthorityPin:
    return ExactAuthorityPin(
        "competence_case", f"cemm.schema:{schema.schema_ref}", hook.case_ref, schema.revision,
        semantic_fingerprint("competence-hook-content", canonical_data(hook), 64), "global",
    )


def _merge_exact(values: Iterable[Any], pin_attr: str, label: str) -> tuple[Any, ...]:
    result = {}
    identity = {}
    for item in values:
        pin = getattr(item, pin_attr)
        logical = (pin.kind, pin.namespace, pin.ref, pin.revision, pin.scope_ref)
        prior_key = identity.get(logical)
        if prior_key is not None and prior_key != pin.key:
            raise RuntimeSemanticAuthorityProjectionError(
                f"conflicting exact {label} for logical revision:{logical}"
            )
        identity[logical] = pin.key
        prior = result.get(pin.key)
        if prior is not None and prior != item:
            raise RuntimeSemanticAuthorityProjectionError(f"exact {label} identity collision:{pin.key}")
        result[pin.key] = item
    return tuple(result[key] for key in sorted(result))


def load_semantic_authority_supplement_v351(
    path: str | Path | None, *, expected_sha256: str = ""
) -> Mapping[str, Any]:
    if path is None:
        if expected_sha256:
            raise RuntimeSemanticAuthorityProjectionError("signed semantic authority supplement path is missing")
        return {"schema_version": SEMANTIC_AUTHORITY_SUPPLEMENT_SCHEMA, "observation_models": [], "auxiliary_exact_pins": []}
    raw = Path(path).read_bytes()
    observed_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and observed_sha256 != expected_sha256:
        raise RuntimeSemanticAuthorityProjectionError("semantic authority supplement changed after release attestation")
    document = json.loads(raw.decode("utf-8"))
    if int(document.get("schema_version", 0)) != SEMANTIC_AUTHORITY_SUPPLEMENT_SCHEMA:
        raise RuntimeSemanticAuthorityProjectionError("unsupported semantic authority supplement schema")
    if not isinstance(document.get("canonical_authority_sets", []), list):
        raise RuntimeSemanticAuthorityProjectionError(
            "supplement canonical_authority_sets must be a list"
        )
    if not isinstance(document.get("observation_models", []), list):
        raise RuntimeSemanticAuthorityProjectionError("supplement observation_models must be a list")
    if not isinstance(document.get("auxiliary_exact_pins", []), list):
        raise RuntimeSemanticAuthorityProjectionError("supplement auxiliary_exact_pins must be a list")
    return document


def _pin_from_document(document: Mapping[str, Any]) -> ExactAuthorityPin:
    required = ("kind", "namespace", "ref", "revision", "content_hash")
    if any(key not in document for key in required):
        raise RuntimeSemanticAuthorityProjectionError("supplement exact pin is incomplete")
    return ExactAuthorityPin(
        str(document["kind"]), str(document["namespace"]), str(document["ref"]),
        int(document["revision"]), str(document["content_hash"]),
        str(document.get("scope_ref", "global")),
    )


CANONICAL_AUTHORITY_SET_REFS = (
    "minimum_discourse_v351",
    "minimum_response_v351",
    "minimum_english_realization_v351",
)


def _artifact_set_fingerprint(
    set_ref: str,
    definitions=(),
    profiles=(),
    authorizations=(),
    auxiliary=(),
) -> str:
    payload = {
        "set_ref": set_ref,
        "definitions": tuple(
            canonical_data(item) for item in sorted(
                definitions, key=lambda item: item.definition_pin.key
            )
        ),
        "profiles": tuple(
            canonical_data(item) for item in sorted(
                profiles, key=lambda item: item.profile_pin.key
            )
        ),
        "authorizations": tuple(
            canonical_data(item) for item in sorted(
                authorizations, key=lambda item: item.authorization_pin.key
            )
        ),
        "auxiliary": tuple(pin.key for pin in sorted(auxiliary, key=lambda pin: pin.key)),
    }
    return _sha(payload)


def compile_canonical_authority_set_v351(set_ref: str):
    """Compile one fixed reviewed candidate set. No arbitrary import path is accepted."""
    if set_ref == "minimum_discourse_v351":
        from ..discourse.minimum_authority_v351 import compile_minimum_discourse_authority
        artifacts = compile_minimum_discourse_authority()
        definitions = tuple(artifacts.semantic_definitions)
        profiles = tuple(artifacts.operational_profiles)
        authorizations = tuple(artifacts.use_authorizations)
        auxiliary = tuple(artifacts.competence_case_pins)
    elif set_ref == "minimum_response_v351":
        from ..response.minimum_authority_v351 import compile_minimum_response_authority
        artifacts = compile_minimum_response_authority()
        definitions = tuple(artifacts.semantic_definitions)
        profiles = tuple(artifacts.operational_profiles)
        authorizations = tuple(artifacts.use_authorizations)
        auxiliary = tuple(artifacts.competence_case_pins)
    elif set_ref == "minimum_english_realization_v351":
        from ..realization.english_v351 import compile_minimum_english_realization_package
        package = compile_minimum_english_realization_package()
        definitions = ()
        profiles = ()
        authorizations = tuple(package.use_authorizations)
        auxiliary = tuple(package.exact_pins)
    else:
        raise RuntimeSemanticAuthorityProjectionError(
            f"unknown canonical authority set:{set_ref}"
        )
    fingerprint = _artifact_set_fingerprint(
        set_ref, definitions, profiles, authorizations, auxiliary
    )
    return fingerprint, definitions, profiles, authorizations, auxiliary


def canonical_authority_set_fingerprints_v351() -> dict[str, str]:
    return {
        set_ref: compile_canonical_authority_set_v351(set_ref)[0]
        for set_ref in CANONICAL_AUTHORITY_SET_REFS
    }


def _supplement_authority(
    supplement: Mapping[str, Any],
    definitions: Iterable[SemanticDefinition],
) -> tuple[
    tuple[ObservationModel, ...],
    tuple[ExactAuthorityPin, ...],
    tuple[SemanticDefinition, ...],
    tuple[OperationalProfile, ...],
    tuple[UseAuthorization, ...],
]:
    authority_definitions = []
    authority_profiles = []
    authority_authorizations = []
    auxiliary = [_pin_from_document(item) for item in supplement.get("auxiliary_exact_pins", ())]
    seen_sets = set()
    for raw_set in supplement.get("canonical_authority_sets", ()):
        if not isinstance(raw_set, Mapping):
            raise RuntimeSemanticAuthorityProjectionError("canonical authority set entry must be an object")
        set_ref = str(raw_set.get("set_ref", ""))
        expected = str(raw_set.get("expected_fingerprint", ""))
        if set_ref in seen_sets:
            raise RuntimeSemanticAuthorityProjectionError(f"duplicate canonical authority set:{set_ref}")
        seen_sets.add(set_ref)
        if set_ref not in CANONICAL_AUTHORITY_SET_REFS:
            raise RuntimeSemanticAuthorityProjectionError(f"unsupported canonical authority set:{set_ref}")
        if not expected:
            raise RuntimeSemanticAuthorityProjectionError(
                f"canonical authority set lacks signed expected fingerprint:{set_ref}"
            )
        observed, defs, profiles, auths, pins = compile_canonical_authority_set_v351(set_ref)
        if observed != expected:
            raise RuntimeSemanticAuthorityProjectionError(
                f"canonical authority set content differs from signed fingerprint:{set_ref}"
            )
        authority_definitions.extend(defs)
        authority_profiles.extend(profiles)
        authority_authorizations.extend(auths)
        auxiliary.extend(pins)

    all_definitions = tuple((*definitions, *authority_definitions))
    definition_by_revision = {
        (item.definition_pin.ref, item.definition_pin.revision): item.definition_pin
        for item in all_definitions
    }
    models = []
    for raw in supplement.get("observation_models", ()):
        if not isinstance(raw, Mapping):
            raise RuntimeSemanticAuthorityProjectionError("observation model supplement entry must be an object")
        outputs = []
        for output in raw.get("output_definitions", ()):
            key = (str(output.get("schema_ref", "")), int(output.get("revision", 0)))
            pin = definition_by_revision.get(key)
            if pin is None:
                raise RuntimeSemanticAuthorityProjectionError(
                    f"observation model output is not an exact projected definition:{key}"
                )
            outputs.append(pin)
        if not outputs:
            raise RuntimeSemanticAuthorityProjectionError("observation model requires exact output definitions")
        calibration_doc = raw.get("calibration")
        calibration_pin = None
        if calibration_doc is not None:
            calibration_pin = _pin_from_document(calibration_doc)
            auxiliary.append(calibration_pin)
        identity_payload = {
            "model_ref": raw.get("model_ref"),
            "revision": raw.get("revision"),
            "modality_ref": raw.get("modality_ref"),
            "outputs": tuple(pin.key for pin in outputs),
            "calibration": None if calibration_pin is None else calibration_pin.key,
            "evidence_refs": tuple(sorted(map(str, raw.get("evidence_refs", ())))),
        }
        model_pin = ExactAuthorityPin(
            "observation_model", "cemm.observation", str(raw.get("model_ref", "")),
            int(raw.get("revision", 0)), _sha(identity_payload), "global",
        )
        models.append(ObservationModel(
            model_pin=model_pin,
            modality_ref=str(raw.get("modality_ref", "")),
            output_definition_pins=tuple(sorted(outputs, key=lambda pin: pin.key)),
            calibration_pin=calibration_pin,
        ))
    return (
        tuple(models),
        tuple(auxiliary),
        tuple(authority_definitions),
        tuple(authority_profiles),
        tuple(authority_authorizations),
    )


def project_runtime_semantic_authority_v351(
    store,
    base_snapshot: AuthoritySnapshotV351,
    *,
    dynamics_parameters: Iterable[DynamicsParameterArtifact] = (),
    supplement: Mapping[str, Any] | None = None,
) -> AuthoritySnapshotV351:
    """Reconstruct one exact split authority snapshot from the current immutable store generation.

    A caller-provided base snapshot is treated as additional already-attested authority and merged
    exactly. Conflicting logical revisions fail closed. No "latest" lookup crosses the pinned
    store snapshot.
    """
    store_authority = store.current_authority_snapshot()
    if (base_snapshot.generation, base_snapshot.authority_fingerprint) != (
        store_authority.generation, store_authority.authority_fingerprint
    ):
        raise RuntimeSemanticAuthorityProjectionError(
            "base semantic snapshot belongs to another store AuthorityGeneration"
        )

    with store.snapshot() as pinned:
        store.assert_snapshot(pinned)
        if (pinned.authority_generation, pinned.authority_fingerprint) != (
            base_snapshot.generation, base_snapshot.authority_fingerprint
        ):
            raise RuntimeSemanticAuthorityProjectionError("store generation changed during semantic authority projection")

        schema_registry = store.repositories.schemas.registry(snapshot=pinned)
        schemas = tuple(schema_registry.iter_schemas(all_revisions=True))
        effective_hashes = {}
        all_definition_pins = {
            (schema.schema_ref, schema.revision): _definition_pin(
                schema,
                _effective_schema_hash(schema, schema_registry, effective_hashes, set()),
            )
            for schema in schemas
        }

        definitions = []
        profiles = []
        authorizations = []
        auxiliary: list[ExactAuthorityPin] = []

        for schema in schemas:
            definition_pin = all_definition_pins[(schema.schema_ref, schema.revision)]
            dependencies: dict[tuple, ExactAuthorityPin] = {}
            constraint_pins: dict[tuple, ExactAuthorityPin] = {}
            unresolved = []

            for link in schema.parent_links:
                try:
                    parent = (
                        schema_registry.schema(link.parent_ref, link.revision)
                        if link.revision_policy is ParentRevisionPolicy.EXACT
                        else schema_registry.resolve_parent(link)
                    )
                except (KeyError, TypeError, ValueError):
                    unresolved.append(f"parent:{link.parent_ref}")
                    continue
                pin = all_definition_pins.get((parent.schema_ref, parent.revision))
                if pin is None:
                    unresolved.append(f"parent:{parent.schema_ref}@{parent.revision}")
                else:
                    dependencies[pin.key] = pin

            for dep in schema.dependencies:
                if not dep.required:
                    continue
                # Only semantic-schema dependencies belong in SemanticDefinition closure.
                # A durable non-schema dependency (policy, adapter, evidence, transition contract,
                # etc.) is exact operational authority and is kept in auxiliary authority instead.
                semantic_pin = _resolve_schema_dependency(
                    schema_registry, all_definition_pins, dep.dependency_ref,
                    dep.exact_revision, dep.minimum_revision
                )
                if semantic_pin is not None:
                    dependencies[semantic_pin.key] = semantic_pin
                    continue
                operational_pin = _resolve_stored_exact_pin(
                    store,
                    pinned,
                    dep.dependency_ref,
                    exact_revision=dep.exact_revision,
                    minimum_revision=dep.minimum_revision,
                )
                if operational_pin is None:
                    unresolved.append(
                        f"dependency:{dep.dependency_kind}:{dep.dependency_ref}"
                    )
                else:
                    auxiliary.append(operational_pin)

            variables = []
            formal_ports = []
            bindings = []
            for index, port in enumerate(schema.local_ports):
                port_pin = _port_pin(schema, port)
                required_types = {}
                for type_ref in port.accepted_type_refs:
                    pin = _resolve_schema_dependency(schema_registry, all_definition_pins, type_ref, None)
                    if pin is None:
                        unresolved.append(f"port-type:{port.port_ref}:{type_ref}")
                    else:
                        required_types[pin.key] = pin
                        dependencies[pin.key] = pin
                for constraint_ref in port.constraint_refs:
                    pin = _resolve_schema_dependency(
                        schema_registry, all_definition_pins, constraint_ref, None
                    )
                    if pin is None:
                        pin = _resolve_stored_exact_pin(store, pinned, constraint_ref)
                        if pin is not None:
                            auxiliary.append(pin)
                    if pin is None:
                        unresolved.append(f"constraint:{port.port_ref}:{constraint_ref}")
                    else:
                        constraint_pins[pin.key] = pin
                variable_ref = f"formal:{index}:{semantic_fingerprint('formal-variable', (schema.schema_ref, schema.revision, port.port_ref), 20)}"
                open_purpose = (
                    sorted(item.value for item in port.open_binding_purposes)[0]
                    if port.open_binding_purposes else "partial"
                )
                variable = SemanticVariable(
                    variable_ref=variable_ref,
                    allowed_kinds=_allowed_node_kinds(port.filler_classes),
                    required_type_pins=tuple(required_types[key] for key in sorted(required_types)),
                    scope_ref="global",
                    open_purpose=open_purpose,
                )
                variables.append(variable)
                formal_ports.append(FormalPort(
                    port_pin=port_pin,
                    variable_ref=variable_ref,
                    minimum=port.cardinality.minimum,
                    maximum=port.cardinality.maximum,
                ))
                bindings.append(PortBinding(
                    binding_ref=f"definition-binding:{index}",
                    application_ref="definition-root",
                    port_pin=port_pin,
                    fillers=(CSIRRef(CSIRNodeKind.VARIABLE, variable_ref),),
                    ordered=bool(port.ordered_fillers),
                ))

            if unresolved:
                if schema.lifecycle_status is SchemaLifecycleStatus.ACTIVE:
                    raise RuntimeSemanticAuthorityProjectionError(
                        f"active schema lacks exact semantic projection dependencies:{schema.schema_ref}@{schema.revision}:{sorted(set(unresolved))}"
                    )
                # An incomplete non-active proposal is intentionally absent from executable
                # split authority; a later promoted revision will enter a new generation.
                continue

            graph = CSIRGraph(
                variables=tuple(variables),
                applications=(SemanticApplication("definition-root", definition_pin),),
                bindings=tuple(bindings),
                root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, "definition-root"),),
            )
            definition = SemanticDefinition(
                definition_pin=definition_pin,
                body=graph,
                formal_ports=tuple(formal_ports),
                semantic_dependency_pins=tuple(dependencies[key] for key in sorted(dependencies)),
                constraint_pins=tuple(constraint_pins[key] for key in sorted(constraint_pins)),
                executable=True,
                provenance_refs=tuple(sorted(set((
                    *tuple(schema.provenance.source_refs),
                    *tuple(schema.provenance.evidence_refs),
                    *tuple(schema.provenance.lineage_refs),
                )))),
            )
            definitions.append(definition)

            # Competence hooks are promotion requirements embedded in the schema record; they are
            # not themselves competence-result authority and therefore are not fabricated as pins.
            competence = ()
            allowed_operations = tuple(sorted(
                item.operation.value for item in schema.use_profile.authorizations
                if item.decision is UseDecision.ALLOW
            ))
            profile_payload = {
                "definition": definition_pin.key,
                "lifecycle_status": schema.lifecycle_status.value,
                "allowed_operations": allowed_operations,
                "permission_scopes": _permission_scopes(schema.permission_ref),
                "competence": tuple(pin.key for pin in competence),
            }
            profile_pin = ExactAuthorityPin(
                "operational_profile", "cemm.schema", f"profile:{schema.schema_ref}",
                schema.revision, _sha(profile_payload), "global",
            )
            profiles.append(OperationalProfile(
                profile_pin=profile_pin,
                definition_pin=definition_pin,
                lifecycle_status=schema.lifecycle_status.value,
                allowed_operations=allowed_operations,
                permission_scopes=_permission_scopes(schema.permission_ref),
                competence_case_pins=competence,
            ))
            for item in schema.use_profile.authorizations:
                auth_payload = {
                    "target": definition_pin.key,
                    "operation": item.operation.value,
                    "decision": item.decision.value,
                    "context_scopes": _context_scopes(schema.scope_ref),
                    "permission_scopes": _permission_scopes(schema.permission_ref),
                    "evidence_refs": tuple(sorted(item.evidence_refs)),
                }
                auth_pin = ExactAuthorityPin(
                    "use_authorization", "cemm.schema",
                    f"use:{schema.schema_ref}:{item.operation.value}", schema.revision,
                    _sha(auth_payload), "global",
                )
                authorizations.append(UseAuthorization(
                    authorization_pin=auth_pin,
                    target_pin=definition_pin,
                    operation=item.operation.value,
                    decision=item.decision.value,
                    context_scopes=_context_scopes(schema.scope_ref),
                    permission_scopes=_permission_scopes(schema.permission_ref),
                    evidence_refs=tuple(sorted(item.evidence_refs)),
                ))

        language_repository = store.repositories.language
        language_registry = language_repository.registry(snapshot=pinned)
        language_snapshot = language_registry.snapshot()
        for collection, kind, ref_attr in _LANGUAGE_COLLECTIONS:
            repository = getattr(language_repository, collection, None)
            if repository is not None and callable(getattr(repository, "all", None)):
                for stored in repository.all(all_revisions=True, snapshot=pinned):
                    item = stored.payload
                    auxiliary.append(ExactAuthorityPin(
                        kind, "cemm.language", str(getattr(item, ref_attr)), int(item.revision),
                        str(stored.record_fingerprint), "global",
                    ))
            else:
                # Small test/dry-run stores may expose only a registry; preserve deterministic fallback.
                for item in getattr(language_snapshot, collection):
                    auxiliary.append(_language_pin(kind, item, ref_attr))

        # Any active schema-backed lexical sense must resolve to the exact semantic revision it
        # names.  This catches stale boot language authority at restart, before a user turn.
        available_definitions = {
            (item.definition_pin.ref, item.definition_pin.revision)
            for item in (*base_snapshot.semantic_definitions, *definitions)
        }
        for sense in language_registry.active_senses():
            if (
                sense.lifecycle_status is SchemaLifecycleStatus.ACTIVE
                and sense.target_ref is not None
                and sense.target_revision is not None
                and (sense.target_ref, sense.target_revision) not in available_definitions
            ):
                raise RuntimeSemanticAuthorityProjectionError(
                    f"active lexical sense targets missing exact semantic definition:{sense.sense_ref}:{sense.target_ref}@{sense.target_revision}"
                )

    (
        supplement_models,
        supplement_aux,
        supplement_definitions,
        supplement_profiles,
        supplement_authorizations,
    ) = _supplement_authority(
        supplement or {
            "schema_version": 1,
            "canonical_authority_sets": [],
            "observation_models": [],
            "auxiliary_exact_pins": [],
        },
        (*base_snapshot.semantic_definitions, *definitions),
    )
    auxiliary.extend(supplement_aux)

    return AuthoritySnapshotV351(
        generation=base_snapshot.generation,
        authority_fingerprint=base_snapshot.authority_fingerprint,
        semantic_definitions=_merge_exact(
            (*base_snapshot.semantic_definitions, *definitions, *supplement_definitions),
            "definition_pin", "semantic definition"
        ),
        operational_profiles=_merge_exact(
            (*base_snapshot.operational_profiles, *profiles, *supplement_profiles),
            "profile_pin", "operational profile"
        ),
        dynamics_parameters=_merge_exact(
            (*base_snapshot.dynamics_parameters, *tuple(dynamics_parameters)), "parameter_pin", "dynamics parameter"
        ),
        observation_models=_merge_exact(
            (*base_snapshot.observation_models, *supplement_models), "model_pin", "observation model"
        ),
        causal_mechanisms=_merge_exact(
            base_snapshot.causal_mechanisms, "mechanism_pin", "causal mechanism"
        ),
        use_authorizations=_merge_exact(
            (*base_snapshot.use_authorizations, *authorizations, *supplement_authorizations),
            "authorization_pin", "use authorization"
        ),
        auxiliary_exact_pins=tuple({
            pin.key: pin
            for pin in (*base_snapshot.auxiliary_exact_pins, *auxiliary)
        }[key] for key in sorted({
            pin.key: pin
            for pin in (*base_snapshot.auxiliary_exact_pins, *auxiliary)
        })),
    )


__all__ = [
    "RuntimeSemanticAuthorityProjectionError",
    "SEMANTIC_AUTHORITY_PROJECTION_ABI",
    "SEMANTIC_AUTHORITY_SUPPLEMENT_SCHEMA",
    "CANONICAL_AUTHORITY_SET_REFS",
    "canonical_authority_set_fingerprints_v351",
    "compile_canonical_authority_set_v351",
    "load_semantic_authority_supplement_v351",
    "project_runtime_semantic_authority_v351",
]
