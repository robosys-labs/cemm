"""Contextual unknown-word semantic induction for CEMM v3.5.1.

This module implements the missing bridge between an unresolved language form and the already
known semantic structure around it. It never treats distributional similarity as truth.

Evidence comes only from reviewed/executable construction slots whose semantic ports resolve
to exact schema constraints. Repeated occurrences accumulate in one stable lexical frontier.
A candidate referent type is proposed only when multiple distinct semantic-role signatures
converge on a compatible exact type. Weak co-occurrence is retained for ranking/explanation
but cannot create executable semantic authority.

Promotion remains the normal Phase-14 path:
candidate -> attributable evidence -> isolated competence -> signed low-risk policy review /
authorization -> new immutable AuthorityGeneration -> restart/replay.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Mapping

from ..language.model import (
    FormKind, FormSenseLinkRecord, LanguageFormRecord, LexicalSenseRecord,
    SenseTargetKind,
)
from ..schema.model import (
    ParentRevisionPolicy, ReferentTypeSchema, SchemaClass, SchemaDependency,
    SchemaLifecycleStatus, SchemaParentLink, SchemaProvenance, UseAuthorization,
    UseDecision, UseOperation, UseProfile, semantic_fingerprint,
)
from ..storage.codec import record_fingerprints
from ..storage.model import RecordKind
from .inducers_v351 import candidate_pin
from .model import FrontierResolutionStatus, LearningFrontierRecord, PinnedRecord
from .package import CandidateProposal
from .phase14_model_v351 import LearningCandidateWorkItemV351, NovelFormSignal

CONTEXTUAL_INDUCTION_ABI = "cemm-contextual-semantic-induction-v351.1"
CONTEXTUAL_POLICY_REF = "policy:v351:contextual-low-risk"
CONTEXTUAL_REVIEW_REF = "review:canonical-policy:contextual-low-risk-v351"
CONTEXTUAL_AUTHORIZATION_REF = "authorization:canonical-policy:contextual-low-risk-v351"
CONTEXTUAL_COMPETENCE_RUNNER_REF = "competence-runner:contextual-lexical-v351"
CONTEXTUAL_COMPETENCE_RUNNER_REVISION = "1"

_COMPETENCE_CASES = (
    "competence:contextual-lexical-ground-v351",
    "competence:contextual-lexical-compose-v351",
    "competence:contextual-lexical-query-v351",
)
_REQUESTED_USES = tuple(
    UseAuthorization(operation, UseDecision.ALLOW, reason="contextual exact-constraint competence")
    for operation in (UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.QUERY)
)


def _pin(kind: RecordKind, stored) -> PinnedRecord:
    return PinnedRecord(kind, stored.record_ref, stored.revision, stored.record_fingerprint)


def _pin_doc(pin: PinnedRecord) -> tuple[str, str, int, str]:
    return pin.record_kind.value, pin.record_ref, pin.revision, pin.record_fingerprint


def _stored_pin(store, kind: RecordKind, ref: str, revision: int | None = None) -> PinnedRecord | None:
    stored = store.get_record(kind, ref, revision)
    return None if stored is None else _pin(kind, stored)


def _merge_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Merge evidence deterministically without counting duplicate derivations."""
    merged = {}
    for raw in rows:
        row = dict(raw)
        identity = (
            tuple(sorted(map(str, row.get("lineage_refs", ())))),
            str(row.get("signature", "")),
            tuple(sorted(map(str, row.get("hard_type_refs", ())))),
        )
        current = merged.get(identity)
        if current is None:
            merged[identity] = {
                "lineage_refs": list(identity[0]),
                "signature": identity[1],
                "hard_type_refs": list(identity[2]),
                "evidence_refs": sorted(set(map(str, row.get("evidence_refs", ())))),
                "authority_pins": sorted({
                    tuple(value) for value in row.get("authority_pins", ())
                    if isinstance(value, (tuple, list)) and len(value) == 4
                }),
                "generic_capability_refs": sorted(set(map(str, row.get("generic_capability_refs", ())))),
                "weak_neighbor_schema_refs": sorted(set(map(str, row.get("weak_neighbor_schema_refs", ())))),
            }
        else:
            current["evidence_refs"] = sorted(set((*current["evidence_refs"], *map(str, row.get("evidence_refs", ())))))
            current["authority_pins"] = sorted({
                *map(tuple, current["authority_pins"]),
                *(tuple(value) for value in row.get("authority_pins", ()) if isinstance(value, (tuple, list)) and len(value) == 4),
            })
            current["generic_capability_refs"] = sorted(set((*current["generic_capability_refs"], *map(str, row.get("generic_capability_refs", ())))))
            current["weak_neighbor_schema_refs"] = sorted(set((*current["weak_neighbor_schema_refs"], *map(str, row.get("weak_neighbor_schema_refs", ())))))
    return tuple(
        merged[key] for key in sorted(
            merged,
            key=lambda item: (item[1], item[0], item[2]),
        )
    )


def _most_specific_compatible_type(registry, refs: Iterable[str]) -> str | None:
    required = tuple(sorted(set(map(str, refs))))
    if not required:
        return None
    candidates = []
    for ref in required:
        try:
            schema = registry.authoritative_schema(ref)
        except KeyError:
            continue
        if not isinstance(schema, ReferentTypeSchema):
            continue
        closure = registry.type_closure(schema.schema_ref, schema.revision)
        if set(required).issubset(closure):
            candidates.append((len(closure), schema.schema_ref))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][1]


def _generic_cues(lattice, observation_ref: str, construction_candidate) -> bool:
    """Detect generic/capability cues using reviewed form metadata, never raw strings."""
    form_by_ref = {item.candidate_ref: item for item in lattice.form_candidates}
    observation = {item.observation_ref: item for item in lattice.observations}.get(observation_ref)
    if observation is None:
        return False
    span = construction_candidate.span
    generic = False
    modal = False
    registry = getattr(lattice, "_registry", None)
    # Analyzer does not expose its registry on the lattice. The caller adds cue booleans
    # from exact forms in _collect_constraints instead.
    del form_by_ref, span, registry
    return generic and modal


class ContextualSemanticInducerV351:
    """Accumulate exact structural constraints around one unknown language form."""

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "contextual_semantic_inducer"

    def __init__(self, *, minimum_distinct_signatures: int = 2) -> None:
        if minimum_distinct_signatures < 2:
            raise ValueError("contextual semantic induction requires at least two distinct signatures")
        self.minimum_distinct_signatures = minimum_distinct_signatures

    def induce(self, *, cycle, store, signal: NovelFormSignal) -> LearningCandidateWorkItemV351:
        return self.induce_group(cycle=cycle, store=store, signals=(signal,))

    def induce_group(
        self, *, cycle, store, signals: tuple[NovelFormSignal, ...]
    ) -> LearningCandidateWorkItemV351:
        if not signals:
            raise ValueError("contextual induction group requires at least one novel form signal")
        identity = {
            (item.pack_pin.key, item.language_tag, item.normalized_form, item.permission_ref)
            for item in signals
        }
        if len(identity) != 1:
            raise ValueError("contextual induction group mixes distinct lexical hypotheses")
        signal = sorted(signals, key=lambda item: item.signal_ref)[0]
        lattice = getattr(cycle.artifacts.get("evidence_lattice"), "form_lattice", None)
        frontier_ref = "learning-frontier:contextual:" + semantic_fingerprint(
            "contextual-lexical-frontier-v351",
            (
                signal.pack_pin.key,
                signal.language_tag,
                signal.normalized_form,
                cycle.context_ref,
                cycle.permission_ref,
            ),
            32,
        )
        existing = store.get_record(RecordKind.LEARNING_FRONTIER, frontier_ref)
        previous_rows = ()
        if existing is not None:
            previous_rows = tuple(
                dict(item)
                for item in tuple(existing.payload.metadata.get("contextual_evidence", ()) or ())
                if isinstance(item, Mapping)
            )
        current_rows = tuple(
            row
            for item in sorted(signals, key=lambda value: value.signal_ref)
            for row in self._collect_constraints(
                cycle=cycle, store=store, signal=item, lattice=lattice
            )
        )
        rows = _merge_rows((*previous_rows, *current_rows))
        evidence_refs = tuple(sorted({
            *(ref for item in signals for ref in item.evidence_refs),
            *(ref for row in rows for ref in row.get("evidence_refs", ())),
        }))
        lineages = tuple(sorted({
            *(ref for item in signals for ref in item.source_lineage_refs),
            *(ref for row in rows for ref in row.get("lineage_refs", ())),
        }))
        hard_refs = tuple(sorted({
            ref for row in rows for ref in row.get("hard_type_refs", ())
        }))
        signatures = tuple(sorted({
            str(row.get("signature")) for row in rows if str(row.get("signature", "")).strip()
        }))
        weak_refs = tuple(sorted({
            ref for row in rows for ref in row.get("weak_neighbor_schema_refs", ())
        }))
        generic_caps = tuple(sorted({
            ref for row in rows for ref in row.get("generic_capability_refs", ())
        }))

        registry = store.repositories.schemas.registry()
        parent_ref = _most_specific_compatible_type(registry, hard_refs)
        conflicting = bool(hard_refs and parent_ref is None)
        candidate_ready = (
            parent_ref is not None
            and len(signatures) >= self.minimum_distinct_signatures
            and not conflicting
        )
        metadata = {
            "phase14_family": "contextual_lexicalization",
            "contextual_induction_abi": CONTEXTUAL_INDUCTION_ABI,
            "normalized_form": signal.normalized_form,
            "language_tag": signal.language_tag,
            "contextual_evidence": rows,
            "hard_type_refs": hard_refs,
            "weak_neighbor_schema_refs": weak_refs,
            "generic_capability_hypothesis_refs": generic_caps,
            "distinct_semantic_signature_count": len(signatures),
            "candidate_parent_ref": parent_ref or "",
            "hard_constraint_conflict": conflicting,
            "coactivation_is_not_truth": True,
            "medium_size_not_inferred_without_evidence": True,
            "diet_class_not_inferred_from_single_food_event": True,
            "competence_executor_pins": {
                operation.value: {
                    "runner_ref": CONTEXTUAL_COMPETENCE_RUNNER_REF,
                    "runner_revision": CONTEXTUAL_COMPETENCE_RUNNER_REVISION,
                }
                for operation in (UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.QUERY)
            },
        }
        frontier = LearningFrontierRecord(
            frontier_ref=frontier_ref,
            missing_contract="language.contextual_semantic_target",
            expected_record_kinds=(
                RecordKind.SCHEMA, RecordKind.LANGUAGE_FORM,
                RecordKind.LEXICAL_SENSE, RecordKind.FORM_SENSE_LINK,
            ),
            expected_schema_classes=(SchemaClass.REFERENT_TYPE,),
            accepted_anchor_types=(
                "form_observation", "construction_slot",
                "exact_semantic_port", "independent_context_evidence",
            ),
            evidence_refs=evidence_refs or signal.evidence_refs,
            candidate_refs=(),
            target_ref=f"lexical-hypothesis:{signal.language_tag}:{signal.normalized_form}",
            dependency_depth=0,
            sensitivity="normal",
            best_question_uol_ref=None,
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            resolution_status=FrontierResolutionStatus.PARTIAL if rows else FrontierResolutionStatus.OPEN,
            metadata=metadata,
        )

        form_proposal = self._form_proposal(
            signal=signal, evidence_refs=evidence_refs
        )
        proposals = (form_proposal,)
        if candidate_ready:
            proposals = self._candidate_proposals(
                store=store,
                signal=signal,
                parent_ref=parent_ref,
                evidence_refs=evidence_refs,
                lineages=lineages,
                form_proposal=form_proposal,
            )
        return LearningCandidateWorkItemV351(
            work_ref="learning-work:contextual:" + semantic_fingerprint(
                "contextual-learning-work-v351",
                (frontier_ref, parent_ref, signatures, tuple(p.proposer_ref for p in proposals)),
                24,
            ),
            frontier=frontier,
            proposals=proposals,
            source_lineage_refs=lineages or signal.source_lineage_refs,
            requested_uses=_REQUESTED_USES if candidate_ready else (),
            competence_case_refs=_COMPETENCE_CASES if candidate_ready else (),
            review_refs=(CONTEXTUAL_REVIEW_REF,) if candidate_ready else (),
            authorization_refs=(CONTEXTUAL_AUTHORIZATION_REF,) if candidate_ready else (),
            risk_refs=(),
            promotion_policy_ref=CONTEXTUAL_POLICY_REF,
            deferred_reason_refs=(
                () if candidate_ready else (
                    "frontier:learning:contextual-evidence-accumulating",
                    "frontier:learning:semantic-target-required",
                )
            ),
        )

    def _collect_constraints(self, *, cycle, store, signal, lattice):
        if lattice is None:
            return ()
        observation_ref = signal.observation_ref
        rows = []
        registry = store.repositories.language.registry()
        form_by_candidate = {item.candidate_ref: item for item in lattice.form_candidates}
        exact_forms = {}
        for candidate in lattice.form_candidates:
            try:
                exact_forms[candidate.candidate_ref] = registry.require_form(
                    candidate.form_ref, candidate.form_revision
                )
            except KeyError:
                continue
        has_generic = any(
            bool(getattr(form, "metadata", {}).get("genericity_cue"))
            for form in exact_forms.values()
        )
        has_modal_capability = any(
            bool(getattr(form, "metadata", {}).get("modal_capability_cue"))
            for form in exact_forms.values()
        )
        senses = {item.candidate_ref: item for item in lattice.sense_candidates}
        weak_neighbors = tuple(sorted({
            item.target_ref
            for item in senses.values()
            if item.target_ref is not None
        }))

        for candidate in lattice.construction_candidates:
            fillers = dict(candidate.slot_fillers)
            matching_slots = tuple(
                slot_ref for slot_ref, values in fillers.items()
                if observation_ref in tuple(values)
            )
            if not matching_slots:
                continue
            construction_stored = store.get_record(
                RecordKind.CONSTRUCTION,
                candidate.construction_ref,
                candidate.construction_revision,
            )
            if construction_stored is None:
                continue
            construction = construction_stored.payload
            programs = tuple(
                item for item in registry.programs_for_construction(
                    construction.construction_ref, construction.revision
                )
                if item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
                and item.use_operation == UseOperation.COMPOSE
                and item.use_decision == UseDecision.ALLOW
            )
            for program in programs:
                program_stored = store.get_record(
                    RecordKind.CONSTRUCTION_PROGRAM, program.program_ref, program.revision
                )
                if program_stored is None:
                    continue
                schema_steps = tuple(
                    step for step in program.steps
                    if step.operation.value in {"instantiate_schema", "wrap_discourse_act"}
                    and step.schema_ref and step.schema_revision
                )
                for step in schema_steps:
                    schema_stored = store.get_record(
                        RecordKind.SCHEMA, step.schema_ref, step.schema_revision
                    )
                    if schema_stored is None:
                        continue
                    schema = schema_stored.payload
                    for slot_ref in matching_slots:
                        slot = next(
                            (item for item in construction.slots if item.slot_ref == slot_ref),
                            None,
                        )
                        if slot is None or not slot.semantic_port_ref:
                            continue
                        try:
                            port = schema.port(slot.semantic_port_ref)
                        except (KeyError, ValueError):
                            continue
                        hard_types = tuple(sorted(set(port.accepted_type_refs)))
                        if not hard_types:
                            continue
                        construction_pin = _pin(RecordKind.CONSTRUCTION, construction_stored)
                        program_pin = _pin(RecordKind.CONSTRUCTION_PROGRAM, program_stored)
                        schema_pin = _pin(RecordKind.SCHEMA, schema_stored)
                        rows.append({
                            "lineage_refs": list(signal.source_lineage_refs),
                            "signature": (
                                f"{schema.schema_ref}@{schema.revision}:"
                                f"{slot.semantic_port_ref}"
                            ),
                            "hard_type_refs": list(hard_types),
                            "evidence_refs": sorted(set((
                                *signal.evidence_refs,
                                *candidate.evidence_refs,
                            ))),
                            "authority_pins": [
                                _pin_doc(construction_pin),
                                _pin_doc(program_pin),
                                _pin_doc(schema_pin),
                            ],
                            "generic_capability_refs": (
                                [schema.schema_ref]
                                if has_generic and has_modal_capability
                                and schema.schema_class == SchemaClass.ACTION
                                else []
                            ),
                            # Coactivated known semantics are retained for later ranking/explanation
                            # only. They never participate in hard type selection.
                            "weak_neighbor_schema_refs": list(weak_neighbors),
                        })
        return tuple(rows)

    def _form_proposal(self, *, signal, evidence_refs) -> CandidateProposal:
        form = LanguageFormRecord(
            form_ref="language-form:learned:" + semantic_fingerprint(
                "learned-language-form-v351",
                (
                    signal.pack_pin.key, signal.language_tag, signal.normalized_form,
                    signal.script, signal.category, signal.token_count,
                ),
                24,
            ),
            pack_ref=signal.pack_pin.record_ref,
            pack_revision=signal.pack_pin.revision,
            written_form=signal.written_form,
            normalized_form=signal.normalized_form,
            form_kind=FormKind.TOKEN if signal.token_count == 1 else FormKind.MULTIWORD,
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            script=signal.script,
            token_count=signal.token_count,
            feature_values=(("category", signal.category),) if signal.category else (),
            source_refs=("source:phase14:contextual-induction:v351",),
            evidence_refs=(),
            permission_ref=signal.permission_ref,
            metadata={
                "learned_by": CONTEXTUAL_INDUCTION_ABI,
                "candidate_not_authority": True,
            },
        )
        return CandidateProposal(
            RecordKind.LANGUAGE_FORM,
            form,
            tuple(evidence_refs),
            dependency_pins=(signal.pack_pin,),
            confidence=1.0,
            proposer_ref="candidate-inducer:contextual-form:v351",
        )

    def _candidate_proposals(
        self, *, store, signal, parent_ref: str, evidence_refs, lineages,
        form_proposal: CandidateProposal
    ) -> tuple[CandidateProposal, ...]:
        parent_stored = store.get_record(RecordKind.SCHEMA, parent_ref)
        if parent_stored is None or not isinstance(parent_stored.payload, ReferentTypeSchema):
            return ()
        parent = parent_stored.payload
        parent_pin = _pin(RecordKind.SCHEMA, parent_stored)
        concept_key = semantic_fingerprint(
            "contextual-referent-type-key-v351",
            (signal.pack_pin.key, signal.language_tag, signal.normalized_form, parent_pin.key),
            48,
        )
        schema = ReferentTypeSchema(
            schema_ref="schema:learned:referent-type:" + concept_key[:24],
            semantic_key="semantic-key:contextual:" + concept_key,
            parent_links=(SchemaParentLink(
                parent_ref=parent.schema_ref,
                revision_policy=ParentRevisionPolicy.EXACT,
                revision=parent.revision,
                inheritance_kind="subtype",
            ),),
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            revision=1,
            scope_ref=parent.scope_ref,
            confidence=1.0,
            permission_ref=signal.permission_ref,
            provenance=SchemaProvenance(
                source_refs=("source:phase14:contextual-induction:v351",),
                created_by=CONTEXTUAL_INDUCTION_ABI,
            ),
            dependencies=(SchemaDependency(
                dependency_ref=parent.schema_ref,
                dependency_kind="exact_semantic_parent",
                exact_revision=parent.revision,
                required=True,
                required_for=frozenset({
                    UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.QUERY,
                }),
                reason="convergent exact contextual port constraints",
            ),),
            use_profile=UseProfile(),
            competence_hooks=(),
            metadata={
                "learned_by": CONTEXTUAL_INDUCTION_ABI,
                "candidate_not_authority": True,
                "contextual_parent_pin": parent_pin.key,
                "distributional_evidence_is_candidate_only": True,
            },
            storage_kinds=parent.storage_kinds,
            facet_entitlement_refs=(),
            identity_criterion_refs=(),
        )
        schema_proposal = CandidateProposal(
            RecordKind.SCHEMA,
            schema,
            tuple(evidence_refs),
            dependency_pins=(parent_pin,),
            confidence=1.0,
            proposer_ref="candidate-inducer:contextual-semantic-definition:v351",
        )
        schema_pin = candidate_pin(RecordKind.SCHEMA, schema)

        form = form_proposal.payload
        form_pin = candidate_pin(RecordKind.LANGUAGE_FORM, form)

        sense = LexicalSenseRecord(
            sense_ref="lexical-sense:learned:" + semantic_fingerprint(
                "learned-lexical-sense-v351",
                (
                    signal.pack_pin.key, form_pin.key, schema_pin.key,
                    SenseTargetKind.REFERENT_TYPE.value,
                    SchemaClass.REFERENT_TYPE.value,
                    UseOperation.GROUND.value,
                ),
                24,
            ),
            pack_ref=signal.pack_pin.record_ref,
            pack_revision=signal.pack_pin.revision,
            target_kind=SenseTargetKind.REFERENT_TYPE,
            target_ref=schema.schema_ref,
            target_revision=schema.revision,
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            target_schema_class=SchemaClass.REFERENT_TYPE,
            use_operation=UseOperation.GROUND,
            authorized_use_operations=(UseOperation.COMPOSE, UseOperation.QUERY),
            use_authority_explicit=False,
            lexical_category="noun",
            source_refs=("source:phase14:contextual-induction:v351",),
            evidence_refs=(),
            competence_case_refs=_COMPETENCE_CASES,
            permission_ref=signal.permission_ref,
            metadata={
                "learned_by": CONTEXTUAL_INDUCTION_ABI,
                "candidate_not_authority": True,
            },
        )
        sense_proposal = CandidateProposal(
            RecordKind.LEXICAL_SENSE,
            sense,
            tuple(evidence_refs),
            dependency_pins=tuple(sorted(
                (signal.pack_pin, schema_pin, form_pin), key=lambda item: item.key
            )),
            confidence=1.0,
            proposer_ref="candidate-inducer:contextual-sense:v351",
        )
        sense_pin = candidate_pin(RecordKind.LEXICAL_SENSE, sense)
        link = FormSenseLinkRecord(
            link_ref="form-sense-link:learned:" + semantic_fingerprint(
                "learned-form-sense-link-v351", (form_pin.key, sense_pin.key), 24
            ),
            form_ref=form.form_ref,
            form_revision=form.revision,
            sense_ref=sense.sense_ref,
            sense_revision=sense.revision,
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            prior_weight=1.0,
            source_refs=("source:phase14:contextual-induction:v351",),
            evidence_refs=(),
            permission_ref=signal.permission_ref,
            metadata={
                "learned_by": CONTEXTUAL_INDUCTION_ABI,
                "candidate_not_authority": True,
            },
        )
        link_proposal = CandidateProposal(
            RecordKind.FORM_SENSE_LINK,
            link,
            tuple(evidence_refs),
            dependency_pins=tuple(sorted((form_pin, sense_pin), key=lambda item: item.key)),
            confidence=1.0,
            proposer_ref="candidate-inducer:contextual-link:v351",
        )
        return (schema_proposal, form_proposal, sense_proposal, link_proposal)


__all__ = [
    "CONTEXTUAL_AUTHORIZATION_REF",
    "CONTEXTUAL_COMPETENCE_RUNNER_REF",
    "CONTEXTUAL_COMPETENCE_RUNNER_REVISION",
    "CONTEXTUAL_INDUCTION_ABI",
    "CONTEXTUAL_POLICY_REF",
    "CONTEXTUAL_REVIEW_REF",
    "ContextualSemanticInducerV351",
]
