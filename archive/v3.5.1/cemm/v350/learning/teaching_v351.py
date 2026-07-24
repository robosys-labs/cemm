"""Exact construction-authorized extraction of learnable teaching projections.

This module is the bridge that lets Phase 14 learn from an ordinary successful semantic
parse without introducing phrase handlers.  A reviewed construction opts into learning by
publishing ``learning_projection_v351`` metadata.  The metadata names *construction slots*,
not English words or grammatical roles.  The extractor then binds an unresolved observation
slot to an already-grounded exact semantic target slot and preserves the construction,
evidence, competence, review and authorization lineage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..language.model import FormObservation, SenseCandidate
from ..schema.model import UseAuthorization, UseDecision, UseOperation, semantic_fingerprint
from ..storage.codec import record_fingerprints
from ..storage.model import RecordKind
from .model import PinnedRecord
from .phase14_model_v351 import DefinitionTeachingProjectionV351, NovelFormSignal, TeachingProjectionEvidenceV351


@dataclass(frozen=True, slots=True)
class ExtractedTeachingProjectionV351:
    form_signal: NovelFormSignal
    projection: TeachingProjectionEvidenceV351
    review_refs: tuple[str, ...] = ()
    authorization_refs: tuple[str, ...] = ()
    risk_refs: tuple[str, ...] = ()
    promotion_policy_ref: str = "policy:v351:reviewed-learning-promotion"


@dataclass(frozen=True, slots=True)
class ExtractedDefinitionTeachingProjectionV351:
    form_signal: NovelFormSignal
    projection: DefinitionTeachingProjectionV351
    review_refs: tuple[str, ...] = ()
    authorization_refs: tuple[str, ...] = ()
    risk_refs: tuple[str, ...] = ()
    promotion_policy_ref: str = "policy:v351:reviewed-learning-promotion"


def _pin(kind: RecordKind, stored) -> PinnedRecord:
    return PinnedRecord(
        kind,
        str(stored.record_ref),
        int(stored.revision),
        str(stored.record_fingerprint),
    )


def _as_refs(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    return tuple(sorted({str(item) for item in value if str(item).strip()}))


def _requested_uses(raw: Any) -> tuple[UseAuthorization, ...]:
    if not raw:
        return ()
    values = []
    for item in raw:
        if isinstance(item, UseAuthorization):
            values.append(item)
            continue
        if not isinstance(item, Mapping):
            raise TypeError("learning_projection_v351 requested_uses must be UseAuthorization or mappings")
        values.append(UseAuthorization(
            operation=UseOperation(str(item["operation"])),
            decision=UseDecision(str(item["decision"])),
            evidence_refs=_as_refs(item.get("evidence_refs")),
            reason=str(item.get("reason", "")),
        ))
    values.sort(key=lambda item: item.operation.value)
    if len({item.operation for item in values}) != len(values):
        raise ValueError("learning_projection_v351 requested uses must be unique per operation")
    return tuple(values)


class TeachingProjectionExtractorV351:
    """Extract exact lexical teaching events from reviewed construction executions.

    Required construction metadata contract::

        learning_projection_v351 = {
            "form_slot_ref": "...",              # must also be in open_observation_slots
            "target_slot_ref": "...",            # exactly one resolved SenseCandidate
            "target_record_kind": "schema",      # exact durable target family
            "competence_case_refs": [...],        # mandatory for executable promotion
            "requested_uses": [
                {"operation": "ground", "decision": "allow"}, ...
            ],
            "review_refs": [...],                 # optional; absence keeps candidate unpromotable
            "authorization_refs": [...],          # optional; absence keeps candidate unpromotable
            "risk_refs": [...],
            "promotion_policy_ref": "...",
        }

    No raw wording, dependency-label interpretation or subject/object mapping is used here.
    """

    METADATA_KEY = "learning_projection_v351"
    DEFINITION_METADATA_KEY = "semantic_definition_projection_v351"

    def extract(self, *, cycle, store) -> tuple[ExtractedTeachingProjectionV351, ...]:
        evidence_lattice = cycle.artifacts.get("evidence_lattice")
        lattice = None if evidence_lattice is None else getattr(evidence_lattice, "form_lattice", None)
        if lattice is None:
            return ()

        observations = {item.observation_ref: item for item in lattice.observations}
        senses = {item.candidate_ref: item for item in lattice.sense_candidates}
        results: dict[str, ExtractedTeachingProjectionV351] = {}

        for candidate in sorted(lattice.construction_candidates, key=lambda item: item.candidate_ref):
            stored_construction = store.get_record(
                RecordKind.CONSTRUCTION,
                candidate.construction_ref,
                candidate.construction_revision,
            )
            if stored_construction is None:
                continue
            construction = stored_construction.payload
            contract = getattr(construction, "metadata", {}).get(self.METADATA_KEY)
            if not isinstance(contract, Mapping):
                continue

            form_slot = str(contract.get("form_slot_ref", ""))
            target_slot = str(contract.get("target_slot_ref", ""))
            if not form_slot or not target_slot or form_slot == target_slot:
                raise ValueError("learning_projection_v351 requires distinct form/target slots")
            open_slots = {str(value) for value in construction.metadata.get("open_observation_slots", ())}
            if form_slot not in open_slots:
                raise ValueError("learning projection form slot must be an explicitly open observation slot")

            fillers = dict(candidate.slot_fillers)
            form_fillers = tuple(fillers.get(form_slot, ()))
            target_fillers = tuple(fillers.get(target_slot, ()))
            if len(form_fillers) != 1 or len(target_fillers) != 1:
                # Ambiguous/multi filler teaching remains a frontier; never guess one target.
                continue
            observation = observations.get(form_fillers[0])
            target_sense = senses.get(target_fillers[0])
            if not isinstance(observation, FormObservation) or not isinstance(target_sense, SenseCandidate):
                continue
            if target_sense.target_ref is None or target_sense.target_revision is None or target_sense.target_kind is None:
                continue

            kind_raw = str(contract.get("target_record_kind", ""))
            if not kind_raw:
                raise ValueError("learning_projection_v351 requires exact target_record_kind")
            target_kind = RecordKind(kind_raw)
            target_stored = store.get_record(target_kind, target_sense.target_ref, target_sense.target_revision)
            if target_stored is None:
                continue
            target_pin = _pin(target_kind, target_stored)

            pack_stored = store.get_record(RecordKind.LANGUAGE_PACK, construction.pack_ref, construction.pack_revision)
            if pack_stored is None:
                raise ValueError("teaching construction references unavailable exact language pack")
            pack_pin = _pin(RecordKind.LANGUAGE_PACK, pack_stored)
            construction_pin = _pin(RecordKind.CONSTRUCTION, stored_construction)

            competence = _as_refs(contract.get("competence_case_refs"))
            requested = _requested_uses(contract.get("requested_uses"))
            evidence_refs = tuple(sorted(set((
                *observation.evidence_refs,
                *target_sense.evidence_refs,
                *candidate.evidence_refs,
            ))))
            source_lineage = tuple(sorted(set((
                *observation.evidence_refs,
                *target_sense.evidence_refs,
                f"construction:{candidate.construction_ref}@{candidate.construction_revision}",
            ))))
            language_tag = str(getattr(pack_stored.payload, "language_tag", ""))
            signal_ref = "novel-form-signal:" + semantic_fingerprint(
                "novel-form-signal-v351",
                (
                    observation.observation_ref,
                    pack_pin.key,
                    observation.canonical,
                    candidate.candidate_ref,
                ),
                24,
            )
            form_signal = NovelFormSignal(
                signal_ref=signal_ref,
                observation_ref=observation.observation_ref,
                pack_pin=pack_pin,
                language_tag=language_tag,
                written_form=observation.original,
                normalized_form=observation.canonical,
                script=observation.script,
                category=observation.category,
                token_count=1,
                evidence_refs=evidence_refs,
                source_lineage_refs=source_lineage,
                permission_ref=cycle.permission_ref,
            )
            projection_ref = "teaching-projection:" + semantic_fingerprint(
                "teaching-projection-v351",
                (
                    candidate.candidate_ref,
                    form_slot,
                    target_slot,
                    target_pin.key,
                    construction_pin.key,
                ),
                24,
            )
            projection = TeachingProjectionEvidenceV351(
                projection_ref=projection_ref,
                form_signal_ref=form_signal.signal_ref,
                target_pin=target_pin,
                target_kind=target_sense.target_kind,
                target_schema_class=target_sense.target_schema_class,
                use_operation=target_sense.use_operation,
                construction_pin=construction_pin,
                evidence_refs=evidence_refs,
                source_lineage_refs=source_lineage,
                competence_case_refs=competence,
                requested_uses=requested,
                lexical_category=str(contract.get("lexical_category") or observation.category or ""),
                metadata={
                    "construction_candidate_ref": candidate.candidate_ref,
                    "form_slot_ref": form_slot,
                    "target_slot_ref": target_slot,
                    "target_record_kind": target_kind.value,
                },
            )
            key = semantic_fingerprint(
                "teaching-projection-dedupe-v351",
                (form_signal.normalized_form, target_pin.key, construction_pin.key),
                32,
            )
            results[key] = ExtractedTeachingProjectionV351(
                form_signal=form_signal,
                projection=projection,
                review_refs=_as_refs(contract.get("review_refs")),
                authorization_refs=_as_refs(contract.get("authorization_refs")),
                risk_refs=_as_refs(contract.get("risk_refs")),
                promotion_policy_ref=str(
                    contract.get("promotion_policy_ref") or "policy:v351:reviewed-learning-promotion"
                ),
            )
        return tuple(results[key] for key in sorted(results))

    def extract_definitions(self, *, cycle, store) -> tuple[ExtractedDefinitionTeachingProjectionV351, ...]:
        """Extract reviewed subtype-definition teaching for genuinely new referent types.

        Contract metadata::

            semantic_definition_projection_v351 = {
                "form_slot_ref": "...",            # explicit open observation slot
                "parent_slot_ref": "...",          # one resolved exact parent schema
                "definition_relation": "subtype",
                "competence_case_refs": [...],
                "requested_uses": [...],
                "review_refs": [...],
                "authorization_refs": [...],
            }

        The extractor does not interpret copulas, noun phrases, word order, or English. The
        reviewed construction is the authority that says these slots encode subtype teaching.
        """
        evidence_lattice = cycle.artifacts.get("evidence_lattice")
        lattice = None if evidence_lattice is None else getattr(evidence_lattice, "form_lattice", None)
        if lattice is None:
            return ()
        observations = {item.observation_ref: item for item in lattice.observations}
        senses = {item.candidate_ref: item for item in lattice.sense_candidates}
        results = {}
        for candidate in sorted(lattice.construction_candidates, key=lambda item: item.candidate_ref):
            stored_construction = store.get_record(
                RecordKind.CONSTRUCTION, candidate.construction_ref, candidate.construction_revision
            )
            if stored_construction is None:
                continue
            construction = stored_construction.payload
            contract = getattr(construction, "metadata", {}).get(self.DEFINITION_METADATA_KEY)
            if not isinstance(contract, Mapping):
                continue
            form_slot = str(contract.get("form_slot_ref", ""))
            parent_slot = str(contract.get("parent_slot_ref", ""))
            relation = str(contract.get("definition_relation", "subtype"))
            if not form_slot or not parent_slot or form_slot == parent_slot:
                raise ValueError("semantic_definition_projection_v351 requires distinct form/parent slots")
            if relation != "subtype":
                raise ValueError("direct semantic definition projection supports only structural subtype teaching")
            open_slots = {str(value) for value in construction.metadata.get("open_observation_slots", ())}
            if form_slot not in open_slots:
                raise ValueError("semantic definition form slot must be explicitly open to observations")
            fillers = dict(candidate.slot_fillers)
            form_fillers = tuple(fillers.get(form_slot, ()))
            parent_fillers = tuple(fillers.get(parent_slot, ()))
            if len(form_fillers) != 1 or len(parent_fillers) != 1:
                continue
            observation = observations.get(form_fillers[0])
            parent_sense = senses.get(parent_fillers[0])
            if not isinstance(observation, FormObservation) or not isinstance(parent_sense, SenseCandidate):
                continue
            if (
                parent_sense.target_ref is None
                or parent_sense.target_revision is None
                or parent_sense.target_schema_class is None
            ):
                continue
            parent_stored = store.get_record(
                RecordKind.SCHEMA, parent_sense.target_ref, parent_sense.target_revision
            )
            if parent_stored is None:
                continue
            parent_pin = _pin(RecordKind.SCHEMA, parent_stored)
            pack_stored = store.get_record(
                RecordKind.LANGUAGE_PACK, construction.pack_ref, construction.pack_revision
            )
            if pack_stored is None:
                raise ValueError("definition teaching construction references unavailable language pack")
            pack_pin = _pin(RecordKind.LANGUAGE_PACK, pack_stored)
            construction_pin = _pin(RecordKind.CONSTRUCTION, stored_construction)
            evidence_refs = tuple(sorted(set((
                *observation.evidence_refs, *parent_sense.evidence_refs, *candidate.evidence_refs,
            ))))
            source_lineage = tuple(sorted(set((
                *observation.evidence_refs, *parent_sense.evidence_refs,
                f"construction:{candidate.construction_ref}@{candidate.construction_revision}",
            ))))
            signal_ref = "novel-form-signal:" + semantic_fingerprint(
                "novel-definition-form-signal-v351",
                (observation.observation_ref, pack_pin.key, observation.canonical, candidate.candidate_ref),
                24,
            )
            form_signal = NovelFormSignal(
                signal_ref=signal_ref, observation_ref=observation.observation_ref, pack_pin=pack_pin,
                language_tag=str(getattr(pack_stored.payload, "language_tag", "")),
                written_form=observation.original, normalized_form=observation.canonical,
                script=observation.script, category=observation.category, token_count=1,
                evidence_refs=evidence_refs, source_lineage_refs=source_lineage,
                permission_ref=cycle.permission_ref,
            )
            projection = DefinitionTeachingProjectionV351(
                projection_ref="definition-teaching-projection:" + semantic_fingerprint(
                    "definition-teaching-projection-v351",
                    (candidate.candidate_ref, form_slot, parent_slot, parent_pin.key, construction_pin.key, relation),
                    24,
                ),
                form_signal_ref=form_signal.signal_ref,
                parent_schema_pin=parent_pin,
                parent_schema_class=parent_sense.target_schema_class,
                construction_pin=construction_pin,
                evidence_refs=evidence_refs,
                source_lineage_refs=source_lineage,
                competence_case_refs=_as_refs(contract.get("competence_case_refs")),
                requested_uses=_requested_uses(contract.get("requested_uses")),
                lexical_category=str(contract.get("lexical_category") or observation.category or ""),
                definition_relation=relation,
                metadata={
                    "construction_candidate_ref": candidate.candidate_ref,
                    "form_slot_ref": form_slot,
                    "parent_slot_ref": parent_slot,
                    "parent_record_kind": RecordKind.SCHEMA.value,
                },
            )
            key = semantic_fingerprint(
                "definition-teaching-projection-dedupe-v351",
                (form_signal.normalized_form, parent_pin.key, construction_pin.key, relation), 32,
            )
            results[key] = ExtractedDefinitionTeachingProjectionV351(
                form_signal=form_signal, projection=projection,
                review_refs=_as_refs(contract.get("review_refs")),
                authorization_refs=_as_refs(contract.get("authorization_refs")),
                risk_refs=_as_refs(contract.get("risk_refs")),
                promotion_policy_ref=str(
                    contract.get("promotion_policy_ref") or "policy:v351:reviewed-learning-promotion"
                ),
            )
        return tuple(results[key] for key in sorted(results))


__all__ = [
    "ExtractedDefinitionTeachingProjectionV351", "ExtractedTeachingProjectionV351",
    "TeachingProjectionExtractorV351",
]
