"""Deterministic document codecs for Phase-7 reviewed language records."""
from __future__ import annotations

from typing import Any, Mapping

from ..schema.model import SchemaClass, SchemaLifecycleStatus, UseOperation, canonical_data
from .model import (
    ConstructionKind,
    ConstructionRecord,
    ConstructionSlot,
    FormKind,
    FormSenseLinkRecord,
    LanguageFormRecord,
    LanguagePackRecord,
    LexicalSenseRecord,
    SenseTargetKind,
)


class LanguageRecordDecodeError(ValueError):
    pass


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise LanguageRecordDecodeError("expected array, not string")
    return tuple(str(item) for item in value)


def _pairs(value: Any) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), str(item)) for key, item in value.items()))
    result = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise LanguageRecordDecodeError("expected two-item pairs")
        result.append((str(item[0]), str(item[1])))
    return tuple(result)


def language_pack_from_document(value: Mapping[str, Any]) -> LanguagePackRecord:
    data = dict(value)
    try:
        return LanguagePackRecord(
            pack_ref=str(data["pack_ref"]),
            language_tag=str(data["language_tag"]),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", "candidate")),
            scripts=_tuple_str(data.get("scripts")),
            tokenizer_profile=str(data.get("tokenizer_profile", "unicode_default")),
            normalization_profile=str(data.get("normalization_profile", "nfkc_casefold")),
            source_refs=_tuple_str(data.get("source_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            competence_case_refs=_tuple_str(data.get("competence_case_refs")),
            permission_ref=str(data.get("permission_ref", "public")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LanguageRecordDecodeError(str(exc)) from exc


def language_form_from_document(value: Mapping[str, Any]) -> LanguageFormRecord:
    data = dict(value)
    try:
        return LanguageFormRecord(
            form_ref=str(data["form_ref"]),
            pack_ref=str(data["pack_ref"]),
            pack_revision=int(data["pack_revision"]),
            written_form=str(data["written_form"]),
            normalized_form=str(data["normalized_form"]),
            form_kind=FormKind(data.get("form_kind", "token")),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", "candidate")),
            script=str(data.get("script", "")),
            token_count=int(data.get("token_count", 1)),
            feature_values=_pairs(data.get("feature_values")),
            variant_of_ref=None if data.get("variant_of_ref") is None else str(data["variant_of_ref"]),
            source_refs=_tuple_str(data.get("source_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            permission_ref=str(data.get("permission_ref", "public")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LanguageRecordDecodeError(str(exc)) from exc


def lexical_sense_from_document(value: Mapping[str, Any]) -> LexicalSenseRecord:
    data = dict(value)
    try:
        target_class = data.get("target_schema_class")
        return LexicalSenseRecord(
            sense_ref=str(data["sense_ref"]),
            pack_ref=str(data["pack_ref"]),
            pack_revision=int(data["pack_revision"]),
            target_kind=SenseTargetKind(data["target_kind"]),
            target_ref=str(data["target_ref"]),
            target_revision=None if data.get("target_revision") is None else int(data["target_revision"]),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", "candidate")),
            target_schema_class=None if target_class is None else SchemaClass(target_class),
            use_operation=UseOperation(data.get("use_operation", "ground")),
            lexical_category=str(data.get("lexical_category", "")),
            frame_ref=str(data.get("frame_ref", "")),
            argument_map=_pairs(data.get("argument_map")),
            expected_type_refs=_tuple_str(data.get("expected_type_refs")),
            scope_behavior=str(data.get("scope_behavior", "none")),
            context_constraints=_tuple_str(data.get("context_constraints")),
            feature_constraints=_pairs(data.get("feature_constraints")),
            source_refs=_tuple_str(data.get("source_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            competence_case_refs=_tuple_str(data.get("competence_case_refs")),
            permission_ref=str(data.get("permission_ref", "public")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LanguageRecordDecodeError(str(exc)) from exc


def form_sense_link_from_document(value: Mapping[str, Any]) -> FormSenseLinkRecord:
    data = dict(value)
    try:
        return FormSenseLinkRecord(
            link_ref=str(data["link_ref"]),
            form_ref=str(data["form_ref"]),
            form_revision=int(data["form_revision"]),
            sense_ref=str(data["sense_ref"]),
            sense_revision=int(data["sense_revision"]),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", "candidate")),
            prior_weight=float(data.get("prior_weight", 1.0)),
            register_refs=_tuple_str(data.get("register_refs")),
            condition_refs=_tuple_str(data.get("condition_refs")),
            source_refs=_tuple_str(data.get("source_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            permission_ref=str(data.get("permission_ref", "public")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LanguageRecordDecodeError(str(exc)) from exc


def construction_from_document(value: Mapping[str, Any]) -> ConstructionRecord:
    data = dict(value)
    try:
        slots = tuple(
            ConstructionSlot(
                slot_ref=str(item["slot_ref"]),
                minimum=int(item.get("minimum", 1)),
                maximum=None if item.get("maximum") is None else int(item["maximum"]),
                accepted_categories=_tuple_str(item.get("accepted_categories")),
                accepted_target_classes=tuple(SchemaClass(value) for value in item.get("accepted_target_classes", ())),
                dependency_relations=_tuple_str(item.get("dependency_relations")),
                dependency_position=str(item.get("dependency_position", "either")),
                anchor_to_trigger=bool(item.get("anchor_to_trigger", True)),
                constituency_labels=_tuple_str(item.get("constituency_labels")),
                optional_when_licensed=bool(item.get("optional_when_licensed", False)),
                semantic_port_ref=str(item.get("semantic_port_ref", "")),
            )
            for item in data.get("slots", ())
        )
        output_class = data.get("output_schema_class")
        return ConstructionRecord(
            construction_ref=str(data["construction_ref"]),
            pack_ref=str(data["pack_ref"]),
            pack_revision=int(data["pack_revision"]),
            construction_kind=ConstructionKind(data["construction_kind"]),
            slots=slots,
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", "candidate")),
            trigger_form_refs=_tuple_str(data.get("trigger_form_refs")),
            trigger_sense_refs=_tuple_str(data.get("trigger_sense_refs")),
            output_schema_ref=None if data.get("output_schema_ref") is None else str(data["output_schema_ref"]),
            output_schema_revision=None if data.get("output_schema_revision") is None else int(data["output_schema_revision"]),
            output_schema_class=None if output_class is None else SchemaClass(output_class),
            full_sentence_pattern=bool(data.get("full_sentence_pattern", False)),
            genuine_idiom=bool(data.get("genuine_idiom", False)),
            preserves_gap=bool(data.get("preserves_gap", False)),
            source_refs=_tuple_str(data.get("source_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            competence_case_refs=_tuple_str(data.get("competence_case_refs")),
            permission_ref=str(data.get("permission_ref", "public")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LanguageRecordDecodeError(str(exc)) from exc


def language_record_to_document(record: Any) -> dict[str, Any]:
    return dict(canonical_data(record))
