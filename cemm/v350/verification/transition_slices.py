"""Phase-12 cross-domain transition vertical-slice proof harness.

Synthetic package definitions are competence fixtures, never boot ontology.
The harness knows only generic record families and structural fields.  Package
semantic refs and lexical forms arrive as data in the competence case.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any, Mapping

from ..composition import MeaningComposer
from ..grounding import DiscourseAnchor, JointGrounder
from ..language import (
    ConstructionKind, ConstructionRecord, ConstructionSlot, DependencyArc,
    DependencyParseEvidence, FormKind, FormLatticeAnalyzer, FormSenseLinkRecord,
    LanguageFormRecord, LexicalSenseRecord, SenseTargetKind, SyntaxAdapterHub,
)
from ..schema.model import (
    ActionSchema, Cardinality, CompetenceHook, EventSchema, LocalPortSchema,
    ParentRevisionPolicy, PortFillerClass, SchemaClass, SchemaLifecycleStatus, SchemaParentLink, SchemaProvenance,
    StateDimensionSchema, StateValueSchema, StorageKind, UseOperation, UseProfile,
)
from ..storage import (
    AdmissionDecision, AssignmentStatus, CapabilityInstance, EpistemicAdmissionRecord,
    EvidenceRecord, GraphPatch, KnowledgeStatus, PatchOperation, PatchOperationKind,
    RecordKind, SemanticStore, SourceAssessmentRecord, StateAssignment, encode_record,
    record_ref, record_revision,
)
from ..transitions import (
    CapabilityDependencyRecord, ConditionOperator, EffectCommitError, StateConditionSpec, StateEffectSpec,
    TransitionContractRecord, TransitionCoordinator,
)
from ..uol.model import (
    ApplicationBinding, CapabilityStatus, ChangeOperation, EventOccurrence, FillerRef,
    IdentityStatus, OccurrenceStatus, Polarity, PropositionReferent, Referent,
    SemanticApplication,
)


@dataclass(frozen=True, slots=True)
class TransitionSliceResult:
    case_ref: str
    package_ref: str
    raw_text: str
    composed_schema_ref: str | None
    grounding_selected: bool
    transition_authorized: bool
    committed: bool
    blocked_reasons: tuple[str, ...]
    frontier_reasons: tuple[str, ...]
    final_state_value_ref: str | None
    capability_status: str | None
    state_history_revisions: int
    proof_event_revision: int | None
    proof_application_revision: int | None
    restart_verified: bool
    timings_ms: Mapping[str, float]

    @property
    def structural_signature(self) -> tuple[Any, ...]:
        return (
            self.grounding_selected,
            self.transition_authorized,
            self.committed,
            tuple(sorted(reason.split(":", 1)[0] for reason in self.blocked_reasons)),
            tuple(sorted(self.frontier_reasons)),
            self.capability_status,
            self.state_history_revisions,
            self.restart_verified,
        )


class _ActorDependencyAdapter:
    adapter_ref = "phase12-verifier:declared-actor"

    def analyze(self, request):
        observations = tuple(
            item for item in request.observations
            if item.category not in {"whitespace", "punctuation", "symbol"}
        )
        if len(observations) < 2:
            return None
        return DependencyParseEvidence(
            parse_ref=f"parse:phase12:{request.source_ref}",
            observation_refs=tuple(item.observation_ref for item in observations),
            arcs=(DependencyArc(
                observations[1].observation_ref,
                observations[0].observation_ref,
                "actor",
                evidence_refs=(self.adapter_ref,),
            ),),
            root_observation_refs=(observations[1].observation_ref,),
            adapter_ref=self.adapter_ref,
            confidence=1.0,
        )


def _profile(**values: str) -> UseProfile:
    return UseProfile.from_mapping(values)


def _operation(kind: RecordKind, record: Any) -> PatchOperation:
    return PatchOperation(
        operation_ref=f"operation:phase12:{kind.value}:{record_ref(kind, record)}:{record_revision(kind, record)}",
        operation_kind=PatchOperationKind.UPSERT,
        record_kind=kind,
        target_ref=record_ref(kind, record),
        record_revision=record_revision(kind, record),
        payload=encode_record(kind, record),
        reason="Phase-12 synthetic vertical-slice competence fixture",
    )


class TransitionSliceHarness:
    """Execute declarative synthetic packages through Phases 7 -> 11.

    Every call uses a fresh overlay so packages cannot become canonical source
    authority or leak state into another competence case.
    """

    def __init__(self, boot_path: str | Path) -> None:
        self.boot_path = Path(boot_path)

    def run(self, case: Mapping[str, Any]) -> TransitionSliceResult | Mapping[str, Any]:
        operation = str(case["operation"])
        if operation in {"full_slice", "blocked_slice", "context_isolation"}:
            return self._run_slice(case)
        if operation == "rename_equivalence":
            left_case = dict(case["left"])
            right_case = dict(case["right"])
            left_case.update(case_ref=f"{case['case_ref']}:left", operation="full_slice")
            right_case.update(case_ref=f"{case['case_ref']}:right", operation="full_slice")
            left = self._run_slice(left_case)
            right = self._run_slice(right_case)
            return {
                "case_ref": case["case_ref"],
                "equivalent": left.structural_signature == right.structural_signature,
                "left_signature": left.structural_signature,
                "right_signature": right.structural_signature,
            }
        if operation == "polysemy_type_selection":
            return self._run_polysemy(case)
        raise ValueError(f"unknown Phase-12 competence operation: {operation}")

    def _run_slice(self, case: Mapping[str, Any]) -> TransitionSliceResult:
        timings: dict[str, float] = {}
        with TemporaryDirectory(prefix="cemm-v350-phase12-case-") as directory:
            overlay = Path(directory) / "overlay.sqlite"
            store = SemanticStore(overlay, boot_path=self.boot_path)
            try:
                t0 = perf_counter()
                fixture = self._install_package(store, case)
                timings["package_install"] = _ms(t0)

                t0 = perf_counter()
                source_application, grounding_selected = self._compose_raw(store, case, fixture)
                timings["form_ground_compose"] = _ms(t0)

                t0 = perf_counter()
                event = self._install_epistemic_bridge(store, case, fixture, source_application)
                timings["epistemic_bridge"] = _ms(t0)

                t0 = perf_counter()
                coordinator = TransitionCoordinator(store)
                effective_time = str(case.get("effective_time", "2026-07-18T12:00:00Z"))
                plans = coordinator.plans_for_event(event, effective_time_ref=effective_time)
                timings["transition_preview"] = _ms(t0)
                plan = next((item for item in plans if item.preview.contract_ref == fixture["contract_ref"]), None)
                authorized = bool(plan and plan.preview.authorized)
                blocked = () if plan is None else plan.preview.blocked_reasons
                frontier_reasons = () if plan is None else tuple(item.reason for item in plan.preview.frontiers)

                committed = False
                proof_event_revision = None
                proof_application_revision = None
                if plan is not None and plan.preview.proof is not None:
                    proof_event_revision = plan.preview.proof.event_revision
                    proof_application_revision = plan.preview.proof.participant_application_revision
                if authorized and bool(case.get("commit", True)):
                    if bool(case.get("mutate_prestate_before_commit")):
                        self._mutate_prestate_after_preview(store, fixture)
                    t0 = perf_counter()
                    try:
                        patch = coordinator.build_patch(
                            event, plan,
                            source_ref=fixture["holder_ref"], permission_ref="internal",
                        )
                    except EffectCommitError as exc:
                        blocked = tuple(sorted((*blocked, str(exc))))
                    else:
                        result = store.apply_patch(patch)
                        timings["transition_commit"] = _ms(t0)
                        if not result.committed:
                            raise AssertionError(f"Phase-12 transition patch rejected: {result.errors}")
                        committed = True
                    timings.setdefault("transition_commit", _ms(t0))

                final_value, history_count = self._state_summary(store, fixture)
                capability_status = self._capability_summary(store, fixture)
                expected = dict(case.get("expected", {}))
                self._assert_expected(
                    expected,
                    grounding_selected=grounding_selected,
                    authorized=authorized,
                    committed=committed,
                    final_value=final_value,
                    capability_status=capability_status,
                    blocked=blocked,
                    frontier_reasons=frontier_reasons,
                )
                if case.get("operation") == "context_isolation" and committed:
                    self._assert_context_isolation(store, fixture)
            finally:
                store.close()

            restart_verified = False
            if committed:
                t0 = perf_counter()
                reopened = SemanticStore(overlay, boot_path=self.boot_path)
                try:
                    final_after_restart, history_after_restart = self._state_summary(reopened, fixture)
                    restart_verified = (
                        final_after_restart == final_value
                        and history_after_restart == history_count
                        and any(
                            item.payload.event_ref == fixture["event_ref"]
                            for item in reopened.records(RecordKind.TRANSITION_PROOF, all_revisions=True)
                        )
                    )
                finally:
                    reopened.close()
                timings["restart_verify"] = _ms(t0)
                if not restart_verified:
                    raise AssertionError("Phase-12 restart/history verification failed")

        return TransitionSliceResult(
            case_ref=str(case["case_ref"]),
            package_ref=str(case["package_ref"]),
            raw_text=f"I {case['lexeme']}",
            composed_schema_ref=fixture["event_schema_ref"],
            grounding_selected=grounding_selected,
            transition_authorized=authorized,
            committed=committed,
            blocked_reasons=tuple(blocked),
            frontier_reasons=tuple(frontier_reasons),
            final_state_value_ref=final_value,
            capability_status=capability_status,
            state_history_revisions=history_count,
            proof_event_revision=proof_event_revision,
            proof_application_revision=proof_application_revision,
            restart_verified=restart_verified,
            timings_ms=timings,
        )

    def _install_package(self, store: SemanticStore, case: Mapping[str, Any]) -> dict[str, str]:
        tag = _tag(case["package_ref"])
        reported_context = f"context:phase12:{tag}:reported"
        target_context = str(case.get("target_context", "actual"))
        holder_ref = f"referent:phase12:{tag}:holder"
        evidence = EvidenceRecord(
            f"evidence:phase12:{tag}:package", f"source:phase12:{tag}", 1.0,
            f"lineage:phase12:{tag}:package", context_ref=target_context,
        )
        raw_evidence = EvidenceRecord(
            f"evidence:phase12:{tag}:raw", holder_ref, 1.0,
            f"lineage:phase12:{tag}:raw", context_ref=reported_context,
        )
        holder = Referent(
            holder_ref, StorageKind.ORDINARY, IdentityStatus.RESOLVED,
            type_refs=("type:software_agent",),
            context_refs=tuple(sorted(set(("actual", reported_context, target_context)))),
            provenance_refs=(raw_evidence.evidence_ref,),
        )
        contract_ref = f"transition-contract:phase12:{tag}"
        duplicate_contract_ref = (
            f"transition-contract:phase12:{tag}:competing"
            if case.get("duplicate_transition_contract") else ""
        )
        transition_contract_refs = (contract_ref,) if not duplicate_contract_ref else (contract_ref, duplicate_contract_ref)
        event_schema_ref = f"event:phase12:{tag}"
        dimension_ref = f"state:phase12:{tag}"
        initial_ref = f"state-value:phase12:{tag}:initial"
        target_ref = f"state-value:phase12:{tag}:target"
        event_schema = EventSchema(
            schema_ref=event_schema_ref,
            semantic_key=f"phase12_{tag}_event",
            local_ports=(LocalPortSchema(
                "affected",
                filler_classes=(PortFillerClass.REFERENT,),
                accepted_type_refs=("type:referent",),
                cardinality=Cardinality(1, 1),
            ),),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            transition_contract_refs=transition_contract_refs,
            use_profile=_profile(ground="allow", compose="allow", query="allow", transition="allow"),
            competence_hooks=(
                CompetenceHook(f"competence:phase12:{tag}:compose", UseOperation.COMPOSE),
                CompetenceHook(f"competence:phase12:{tag}:transition", UseOperation.TRANSITION),
            ),
            provenance=SchemaProvenance(evidence_refs=(evidence.evidence_ref,)),
        )
        ordered = bool(case.get("ordered", False))
        dimension = StateDimensionSchema(
            schema_ref=dimension_ref,
            semantic_key=f"phase12_{tag}_dimension",
            holder_type_refs=("type:referent",),
            value_schema_refs=(initial_ref, target_ref),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            ordered=ordered,
            transition_contract_refs=transition_contract_refs,
            use_profile=_profile(compose="allow", query="allow", transition="allow"),
            competence_hooks=(CompetenceHook(
                f"competence:phase12:{tag}:state-transition", UseOperation.TRANSITION
            ),),
            provenance=SchemaProvenance(evidence_refs=(evidence.evidence_ref,)),
        )
        initial_value = StateValueSchema(
            initial_ref, f"phase12_{tag}_initial", dimension_ref=dimension_ref,
            ordering_key=case.get("initial_order"),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=_profile(compose="allow", query="allow"),
        )
        target_value = StateValueSchema(
            target_ref, f"phase12_{tag}_target", dimension_ref=dimension_ref,
            ordering_key=case.get("target_order"),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=_profile(compose="allow", query="allow"),
        )
        effect_operation = ChangeOperation(str(case.get("effect_operation", "set")))
        contract = TransitionContractRecord(
            contract_ref,
            event_schema_ref,
            1,
            (StateConditionSpec(
                f"condition:phase12:{tag}:initial", "affected", dimension_ref, 1,
                ConditionOperator.EQUALS, initial_ref, 1,
            ),),
            (StateEffectSpec(
                f"effect:phase12:{tag}:target", "affected", dimension_ref, 1,
                effect_operation,
                from_value_ref=initial_ref, from_value_revision=1,
                to_value_ref=target_ref, to_value_revision=1,
            ),),
            (evidence.evidence_ref,),
            SchemaLifecycleStatus.ACTIVE,
        )
        duplicate_contract = None
        if duplicate_contract_ref:
            duplicate_contract = replace(contract, contract_ref=duplicate_contract_ref)

        assignment = StateAssignment(
            f"assignment:phase12:{tag}:state", holder_ref, dimension_ref, 1,
            initial_ref, 1, AssignmentStatus.ACTIVE, target_context, 1.0,
            valid_from="2026-01-01T00:00:00Z", evidence_refs=(evidence.evidence_ref,),
        )

        form_ref = f"form:phase12:{tag}"
        sense_ref = f"sense:phase12:{tag}"
        form = LanguageFormRecord(
            form_ref, "language-pack:en", 1, str(case["lexeme"]), str(case["lexeme"]).casefold(),
            FormKind.TOKEN, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            source_refs=(f"source:phase12:{tag}",), evidence_refs=(evidence.evidence_ref,),
        )
        sense = LexicalSenseRecord(
            sense_ref, "language-pack:en", 1, SenseTargetKind.SCHEMA,
            event_schema_ref, 1, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            target_schema_class=SchemaClass.EVENT, use_operation=UseOperation.GROUND,
            lexical_category="verb", source_refs=(f"source:phase12:{tag}",),
            evidence_refs=(evidence.evidence_ref,),
            competence_case_refs=(str(case["case_ref"]),),
        )
        link = FormSenseLinkRecord(
            f"form-sense-link:phase12:{tag}", form_ref, 1, sense_ref, 1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            source_refs=(f"source:phase12:{tag}",), evidence_refs=(evidence.evidence_ref,),
        )
        construction = ConstructionRecord(
            f"construction:phase12:{tag}", "language-pack:en", 1,
            ConstructionKind.ARGUMENT_STRUCTURE,
            (ConstructionSlot(
                "affected", accepted_categories=("pronoun",),
                dependency_relations=("actor",), dependency_position="dependent",
                semantic_port_ref="affected",
            ),),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            trigger_sense_refs=(sense_ref,), output_schema_ref=event_schema_ref,
            output_schema_revision=1, output_schema_class=SchemaClass.EVENT,
            source_refs=(f"source:phase12:{tag}",), evidence_refs=(evidence.evidence_ref,),
            competence_case_refs=(str(case["case_ref"]),),
        )

        records: list[tuple[RecordKind, Any]] = [
            (RecordKind.EVIDENCE, evidence), (RecordKind.EVIDENCE, raw_evidence),
            (RecordKind.REFERENT, holder),
            (RecordKind.SCHEMA, event_schema), (RecordKind.SCHEMA, dimension),
            (RecordKind.SCHEMA, initial_value), (RecordKind.SCHEMA, target_value),
            (RecordKind.TRANSITION_CONTRACT, contract),
            *(((RecordKind.TRANSITION_CONTRACT, duplicate_contract),) if duplicate_contract is not None else ()),
            (RecordKind.STATE_ASSIGNMENT, assignment),
            (RecordKind.LANGUAGE_FORM, form), (RecordKind.LEXICAL_SENSE, sense),
            (RecordKind.FORM_SENSE_LINK, link), (RecordKind.CONSTRUCTION, construction),
        ]
        action_ref = ""
        if case.get("capability_mode") or case.get("external_capability_unavailable"):
            action_ref = f"action:phase12:{tag}"
            action = ActionSchema(
                schema_ref=action_ref, semantic_key=f"phase12_{tag}_action",
                local_ports=(LocalPortSchema(
                    "actor", accepted_type_refs=("type:referent",), cardinality=Cardinality(1, 1)
                ),),
                controlling_port_ref="actor",
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                use_profile=_profile(compose="allow", query="allow"),
                provenance=SchemaProvenance(evidence_refs=(evidence.evidence_ref,)),
            )
            records.append((RecordKind.SCHEMA, action))
            mode = case.get("capability_mode")
            if mode:
                expected_value = target_ref if mode == "available_on_target" else initial_ref
                dependency = CapabilityDependencyRecord(
                    f"capability-dependency:phase12:{tag}", ("type:referent",), action_ref, 1,
                    (StateConditionSpec(
                        f"condition:phase12:{tag}:capability", "holder", dimension_ref, 1,
                        ConditionOperator.EQUALS, expected_value, 1,
                    ),),
                    CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE, CapabilityStatus.UNKNOWN,
                    (evidence.evidence_ref,), SchemaLifecycleStatus.ACTIVE,
                )
                records.append((RecordKind.CAPABILITY_DEPENDENCY, dependency))
                if case.get("duplicate_capability_dependency"):
                    records.append((RecordKind.CAPABILITY_DEPENDENCY, replace(
                        dependency, dependency_ref=f"{dependency.dependency_ref}:competing"
                    )))
            if case.get("external_capability_unavailable"):
                records.append((RecordKind.CAPABILITY_INSTANCE, CapabilityInstance(
                    f"capability:phase12:{tag}", holder_ref, action_ref, 1,
                    CapabilityStatus.UNAVAILABLE, 1.0, target_context,
                    valid_from="2026-01-01T00:00:00Z", evidence_refs=(evidence.evidence_ref,),
                )))

        if case.get("parallel_actual_state") and target_context != "actual":
            records.append((RecordKind.STATE_ASSIGNMENT, StateAssignment(
                f"assignment:phase12:{tag}:actual-parallel", holder_ref, dimension_ref, 1,
                initial_ref, 1, AssignmentStatus.ACTIVE, "actual", 1.0,
                valid_from="2026-01-01T00:00:00Z", evidence_refs=(evidence.evidence_ref,),
            )))

        result = store.apply_patch(GraphPatch(
            patch_ref=f"patch:phase12:{tag}:package",
            context_ref=target_context, scope_ref="phase12-competence",
            source_ref=f"source:phase12:{tag}", permission_ref="internal",
            operations=tuple(_operation(kind, record) for kind, record in records),
            expected_store_revision=store.revision,
            validation_requirements=("phase12_synthetic_competence_only", "no_boot_promotion"),
        ))
        if not result.committed:
            raise AssertionError(f"Phase-12 package install failed: {result.errors}")
        return {
            "tag": tag,
            "reported_context": reported_context,
            "target_context": target_context,
            "holder_ref": holder_ref,
            "event_schema_ref": event_schema_ref,
            "dimension_ref": dimension_ref,
            "initial_ref": initial_ref,
            "target_ref": target_ref,
            "contract_ref": contract_ref,
            "raw_evidence_ref": raw_evidence.evidence_ref,
            "package_evidence_ref": evidence.evidence_ref,
            "assignment_ref": assignment.assignment_ref,
            "action_ref": action_ref,
            "event_ref": f"referent:phase12:{tag}:event",
        }

    def _compose_raw(
        self, store: SemanticStore, case: Mapping[str, Any], fixture: Mapping[str, str]
    ) -> tuple[SemanticApplication, bool]:
        analyzer = FormLatticeAnalyzer(
            store.repositories.language.registry(),
            syntax_adapters=SyntaxAdapterHub(dependency_adapters=(_ActorDependencyAdapter(),)),
        )
        grounder = JointGrounder(store, analyzer)
        anchor = DiscourseAnchor(
            f"anchor:phase12:{fixture['tag']}:participant", fixture["holder_ref"],
            fixture["reported_context"], 1.0, 0, role_refs=("self", "speaker"),
            evidence_refs=(fixture["raw_evidence_ref"],),
        )
        lattice, grounding = grounder.ground_text(
            f"I {case['lexeme']}", source_ref=fixture["raw_evidence_ref"],
            context_ref=fixture["reported_context"], discourse_anchors=(anchor,),
            language_hints=("en",),
        )
        composition = MeaningComposer(store).compose(
            lattice, grounding, context_ref=fixture["reported_context"]
        )
        graph = composition.bundle.uol_graph
        if graph is None:
            raise AssertionError(
                f"Phase-12 raw pipeline did not materialize UOL: {composition.bundle.selection.uncertainty_reasons}"
            )
        application = next(
            (item for item in graph.applications.values() if item.schema_ref == fixture["event_schema_ref"]),
            None,
        )
        if application is None:
            raise AssertionError("Phase-12 raw pipeline did not compose the fixture event schema")
        return application, grounding.selected is not None

    def _install_epistemic_bridge(
        self,
        store: SemanticStore,
        case: Mapping[str, Any],
        fixture: Mapping[str, str],
        source_application: SemanticApplication,
    ) -> EventOccurrence:
        tag = fixture["tag"]
        proposition_ref = f"referent:phase12:{tag}:proposition"
        proposition_referent = Referent(
            proposition_ref, StorageKind.PROPOSITION, IdentityStatus.CANDIDATE,
            type_refs=("type:proposition",), context_refs=(fixture["reported_context"],),
            provenance_refs=(fixture["raw_evidence_ref"],),
        )
        proposition = PropositionReferent(
            proposition_referent,
            (FillerRef(PortFillerClass.SEMANTIC_APPLICATION, source_application.application_ref),),
            fixture["reported_context"],
            polarity=Polarity(str(case.get("polarity", "positive"))),
            evidence_refs=(fixture["raw_evidence_ref"],),
        )
        source_assessment = SourceAssessmentRecord(
            f"source-assessment:phase12:{tag}", fixture["holder_ref"],
            1.0, 1.0, 1.0, 0.0, fixture["reported_context"],
            (fixture["raw_evidence_ref"],),
        )
        admit = bool(case.get("admit", True))
        admission = None
        if admit:
            admission = EpistemicAdmissionRecord(
                f"admission:phase12:{tag}", proposition_ref,
                fixture["reported_context"], fixture["target_context"],
                AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 1.0,
                (fixture["holder_ref"],), (fixture["raw_evidence_ref"],),
                (f"proof:phase12:{tag}:admission",), f"policy:phase12:{tag}",
                source_assessment_pins=((source_assessment.assessment_ref, 1),),
                authorization_ref=f"authorization:phase12:{tag}",
            )
        retraction = None
        if admission is not None and bool(case.get("retract_admission")):
            retraction = EpistemicAdmissionRecord(
                f"admission-retraction:phase12:{tag}", proposition_ref,
                fixture["reported_context"], fixture["target_context"],
                AdmissionDecision.RETRACT, KnowledgeStatus.UNDETERMINED, 1.0,
                (fixture["holder_ref"],), (fixture["raw_evidence_ref"],),
                (f"proof:phase12:{tag}:retraction",), f"policy:phase12:{tag}:retraction",
                authorization_ref=f"authorization:phase12:{tag}:retraction",
                retracts_admission_ref=admission.admission_ref,
            )
        target_application = replace(
            source_application,
            application_ref=f"application:phase12:{tag}:target-context",
            context_ref=fixture["target_context"],
        )
        event_referent = Referent(
            fixture["event_ref"], StorageKind.EVENT_OCCURRENCE, IdentityStatus.RESOLVED,
            type_refs=("type:event_occurrence",), context_refs=(fixture["target_context"],),
            provenance_refs=(fixture["raw_evidence_ref"],),
        )
        status = OccurrenceStatus(str(case.get("event_status", "admitted")))
        event = EventOccurrence(
            event_referent, fixture["event_schema_ref"], 1,
            target_application.application_ref, fixture["target_context"],
            occurrence_status=status,
            admission_refs=() if admission is None else (admission.admission_ref,),
        )
        records: list[tuple[RecordKind, Any]] = [
            (RecordKind.SEMANTIC_APPLICATION, source_application),
            (RecordKind.REFERENT, proposition_referent),
            (RecordKind.PROPOSITION, proposition),
            (RecordKind.SOURCE_ASSESSMENT, source_assessment),
            (RecordKind.SEMANTIC_APPLICATION, target_application),
            (RecordKind.REFERENT, event_referent),
            (RecordKind.EVENT_OCCURRENCE, event),
        ]
        if admission is not None:
            records.append((RecordKind.EPISTEMIC_ADMISSION, admission))
        if retraction is not None:
            records.append((RecordKind.EPISTEMIC_ADMISSION, retraction))
        result = store.apply_patch(GraphPatch(
            patch_ref=f"patch:phase12:{tag}:epistemic-bridge",
            context_ref=fixture["target_context"], scope_ref="phase12-competence",
            source_ref=fixture["holder_ref"], permission_ref="internal",
            operations=tuple(_operation(kind, record) for kind, record in records),
            expected_store_revision=store.revision,
            validation_requirements=("phase12_explicit_epistemic_bridge",),
        ))
        if not result.committed:
            raise AssertionError(f"Phase-12 epistemic bridge failed: {result.errors}")
        stored = store.get_record(RecordKind.EVENT_OCCURRENCE, event.event_ref)
        if stored is None:
            raise AssertionError("Phase-12 target-context event did not persist")
        return stored.payload

    @staticmethod
    def _mutate_prestate_after_preview(store: SemanticStore, fixture: Mapping[str, str]) -> None:
        """Simulate an independently changed pre-state after a transition plan was pinned.

        This is competence-only adversarial state, not a transition shortcut.  The
        stale execution plan must fail before canonical patch generation.
        """
        current = store.get_record(RecordKind.STATE_ASSIGNMENT, fixture["assignment_ref"])
        if current is None or not isinstance(current.payload, StateAssignment):
            raise AssertionError("Phase-12 stale-plan fixture pre-state is unresolved")
        changed = replace(
            current.payload,
            value_ref=fixture["target_ref"],
            value_revision=1,
            evidence_refs=tuple(sorted(set((*current.payload.evidence_refs, fixture["package_evidence_ref"])))),
        )
        operation = PatchOperation(
            operation_ref=f"operation:phase12:stale-prestate:{fixture['assignment_ref']}",
            operation_kind=PatchOperationKind.UPSERT,
            record_kind=RecordKind.STATE_ASSIGNMENT,
            target_ref=fixture["assignment_ref"],
            record_revision=current.revision + 1,
            payload=encode_record(RecordKind.STATE_ASSIGNMENT, changed),
            reason="Phase-12 adversarial pre-state mutation after preview",
        )
        result = store.apply_patch(GraphPatch(
            patch_ref=f"patch:phase12:stale-prestate:{fixture['assignment_ref']}",
            context_ref=fixture["target_context"], scope_ref="phase12-competence",
            source_ref=fixture["holder_ref"], permission_ref="internal",
            operations=(operation,), expected_store_revision=store.revision,
            validation_requirements=("phase12_stale_plan_adversarial",),
        ))
        if not result.committed:
            raise AssertionError(f"Phase-12 stale-plan pre-state mutation failed: {result.errors}")

    @staticmethod
    def _state_summary(store: SemanticStore, fixture: Mapping[str, str]) -> tuple[str | None, int]:
        items = [
            item for item in store.records(RecordKind.STATE_ASSIGNMENT, all_revisions=True)
            if item.payload.holder_ref == fixture["holder_ref"]
            and item.payload.dimension_ref == fixture["dimension_ref"]
            and item.payload.context_ref == fixture["target_context"]
        ]
        latest: dict[str, Any] = {}
        for item in items:
            prior = latest.get(item.record_ref)
            if prior is None or item.revision > prior.revision:
                latest[item.record_ref] = item
        active = [item.payload for item in latest.values() if item.payload.status == AssignmentStatus.ACTIVE]
        value = active[0].value_ref if len(active) == 1 else None
        return value, len(items)

    @staticmethod
    def _capability_summary(store: SemanticStore, fixture: Mapping[str, str]) -> str | None:
        action_ref = fixture.get("action_ref") or ""
        if not action_ref:
            return None
        items = [
            item for item in store.records(RecordKind.CAPABILITY_INSTANCE, all_revisions=True)
            if item.payload.holder_ref == fixture["holder_ref"]
            and item.payload.action_schema_ref == action_ref
            and item.payload.context_ref == fixture["target_context"]
        ]
        if not items:
            return None
        latest: dict[str, Any] = {}
        for item in items:
            prior = latest.get(item.record_ref)
            if prior is None or item.revision > prior.revision:
                latest[item.record_ref] = item
        selected = max(latest.values(), key=lambda item: (item.revision, item.record_ref))
        return selected.payload.status.value

    @staticmethod
    def _assert_expected(expected: Mapping[str, Any], **actual: Any) -> None:
        if "transition_authorized" in expected and actual["authorized"] is not bool(expected["transition_authorized"]):
            raise AssertionError(f"unexpected transition authorization: {actual['authorized']}")
        if "committed" in expected and actual["committed"] is not bool(expected["committed"]):
            raise AssertionError(f"unexpected commit state: {actual['committed']}")
        if expected.get("final_state") == "target" and actual["final_value"] is None:
            raise AssertionError("expected exactly one active target state")
        if "capability_status" in expected and actual["capability_status"] != expected["capability_status"]:
            raise AssertionError(
                f"unexpected capability status: {actual['capability_status']} != {expected['capability_status']}"
            )
        reason = expected.get("blocked_reason_contains")
        if reason and not any(str(reason) in item for item in actual["blocked"]):
            raise AssertionError(f"expected blocked reason containing {reason}: {actual['blocked']}")
        frontier = expected.get("frontier_reason")
        if frontier and frontier not in actual["frontier_reasons"]:
            raise AssertionError(f"expected frontier {frontier}: {actual['frontier_reasons']}")

    @staticmethod
    def _assert_context_isolation(store: SemanticStore, fixture: Mapping[str, str]) -> None:
        actual_items = [
            item for item in store.records(RecordKind.STATE_ASSIGNMENT, all_revisions=True)
            if item.payload.holder_ref == fixture["holder_ref"]
            and item.payload.dimension_ref == fixture["dimension_ref"]
            and item.payload.context_ref == "actual"
        ]
        latest: dict[str, Any] = {}
        for item in actual_items:
            prior = latest.get(item.record_ref)
            if prior is None or item.revision > prior.revision:
                latest[item.record_ref] = item
        active = [item.payload for item in latest.values() if item.payload.status == AssignmentStatus.ACTIVE]
        if len(active) != 1 or active[0].value_ref != fixture["initial_ref"]:
            raise AssertionError("context-local transition leaked into actual-world state")

    def _run_polysemy(self, case: Mapping[str, Any]) -> Mapping[str, Any]:
        # This proof intentionally uses a fresh overlay and one shared surface form.
        # Competing event senses differ only by reviewed holder type/port contracts.
        with TemporaryDirectory(prefix="cemm-v350-phase12-polysemy-") as directory:
            store = SemanticStore(Path(directory) / "overlay.sqlite", boot_path=self.boot_path)
            try:
                tag = _tag(case["case_ref"])
                evidence = EvidenceRecord(
                    f"evidence:phase12:{tag}", "source:phase12:polysemy", 1.0,
                    f"lineage:phase12:{tag}", context_ref="actual",
                )
                type_a = _synthetic_type(f"type:phase12:{tag}:a", evidence.evidence_ref)
                type_b = _synthetic_type(f"type:phase12:{tag}:b", evidence.evidence_ref)
                holder = Referent(
                    f"referent:phase12:{tag}:holder", StorageKind.ORDINARY, IdentityStatus.RESOLVED,
                    type_refs=(type_a.schema_ref,), context_refs=("actual",),
                    provenance_refs=(evidence.evidence_ref,),
                )
                schemas = []
                language_records = []
                form_ref = f"form:phase12:{tag}:shared"
                form = LanguageFormRecord(
                    form_ref, "language-pack:en", 1, str(case["lexeme"]), str(case["lexeme"]).casefold(),
                    lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                    source_refs=("source:phase12:polysemy",), evidence_refs=(evidence.evidence_ref,),
                )
                language_records.append((RecordKind.LANGUAGE_FORM, form))
                for suffix, type_schema in (("a", type_a), ("b", type_b)):
                    event = EventSchema(
                        schema_ref=f"event:phase12:{tag}:{suffix}", semantic_key=f"phase12_{tag}_{suffix}",
                        local_ports=(LocalPortSchema(
                            "affected", accepted_type_refs=(type_schema.schema_ref,), cardinality=Cardinality(1, 1)
                        ),),
                        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                        use_profile=_profile(ground="allow", compose="allow", query="allow"),
                        competence_hooks=(CompetenceHook(
                            f"competence:phase12:{tag}:{suffix}", UseOperation.COMPOSE
                        ),),
                        provenance=SchemaProvenance(evidence_refs=(evidence.evidence_ref,)),
                    )
                    schemas.append(event)
                    sense = LexicalSenseRecord(
                        f"sense:phase12:{tag}:{suffix}", "language-pack:en", 1,
                        SenseTargetKind.SCHEMA, event.schema_ref, 1,
                        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                        target_schema_class=SchemaClass.EVENT, use_operation=UseOperation.GROUND,
                        lexical_category="verb", expected_type_refs=(type_schema.schema_ref,),
                        source_refs=("source:phase12:polysemy",), evidence_refs=(evidence.evidence_ref,),
                        competence_case_refs=(str(case["case_ref"]),),
                    )
                    language_records.extend((
                        (RecordKind.LEXICAL_SENSE, sense),
                        (RecordKind.FORM_SENSE_LINK, FormSenseLinkRecord(
                            f"form-sense-link:phase12:{tag}:{suffix}", form_ref, 1, sense.sense_ref, 1,
                            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                            source_refs=("source:phase12:polysemy",), evidence_refs=(evidence.evidence_ref,),
                        )),
                        (RecordKind.CONSTRUCTION, ConstructionRecord(
                            f"construction:phase12:{tag}:{suffix}", "language-pack:en", 1,
                            ConstructionKind.ARGUMENT_STRUCTURE,
                            (ConstructionSlot(
                                "affected", accepted_categories=("pronoun",),
                                dependency_relations=("actor",), dependency_position="dependent",
                                semantic_port_ref="affected",
                            ),),
                            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                            trigger_sense_refs=(sense.sense_ref,), output_schema_ref=event.schema_ref,
                            output_schema_revision=1, output_schema_class=SchemaClass.EVENT,
                            source_refs=("source:phase12:polysemy",), evidence_refs=(evidence.evidence_ref,),
                            competence_case_refs=(str(case["case_ref"]),),
                        )),
                    ))
                records = [
                    (RecordKind.EVIDENCE, evidence), (RecordKind.SCHEMA, type_a),
                    (RecordKind.SCHEMA, type_b), (RecordKind.REFERENT, holder),
                    *((RecordKind.SCHEMA, item) for item in schemas), *language_records,
                ]
                result = store.apply_patch(GraphPatch(
                    f"patch:phase12:{tag}:polysemy", "actual", "phase12-competence",
                    "source:phase12:polysemy", "internal",
                    tuple(_operation(kind, record) for kind, record in records),
                    expected_store_revision=store.revision,
                ))
                if not result.committed:
                    raise AssertionError(f"polysemy package rejected: {result.errors}")
                analyzer = FormLatticeAnalyzer(
                    store.repositories.language.registry(),
                    syntax_adapters=SyntaxAdapterHub(dependency_adapters=(_ActorDependencyAdapter(),)),
                )
                lattice, grounding = JointGrounder(store, analyzer).ground_text(
                    f"I {case['lexeme']}", source_ref=str(case["case_ref"]), context_ref="actual",
                    discourse_anchors=(DiscourseAnchor(
                        f"anchor:phase12:{tag}", holder.referent_ref, "actual", 1.0, 0,
                        role_refs=("self", "speaker"), type_refs=(type_a.schema_ref,),
                        evidence_refs=(evidence.evidence_ref,),
                    ),),
                    language_hints=("en",),
                )
                composition = MeaningComposer(store).compose(lattice, grounding, context_ref="actual")
                graph = composition.bundle.uol_graph
                selected = set() if graph is None else {item.schema_ref for item in graph.applications.values()}
                expected_ref = schemas[0].schema_ref
                rejected_ref = schemas[1].schema_ref
                if expected_ref not in selected or rejected_ref in selected:
                    raise AssertionError(
                        "type/port constraints did not resolve polysemy structurally: "
                        f"selected={sorted(selected)} grounding_selected={grounding.selected} "
                        f"frontiers={grounding.frontier_refs} constructions="
                        f"{[(item.construction_ref, item.slot_fillers) for item in lattice.construction_candidates]} "
                        f"selection={composition.bundle.selection}"
                    )
                return {
                    "case_ref": case["case_ref"],
                    "selected_schema_ref": expected_ref,
                    "rejected_schema_ref": rejected_ref,
                    "sense_candidate_count": len([
                        item for item in lattice.sense_candidates if item.target_ref in {expected_ref, rejected_ref}
                    ]),
                }
            finally:
                store.close()


def _synthetic_type(schema_ref: str, evidence_ref: str):
    from ..schema.model import ReferentTypeSchema
    return ReferentTypeSchema(
        schema_ref=schema_ref, semantic_key=schema_ref.replace(":", "_"),
        parent_links=(SchemaParentLink("type:software_agent", ParentRevisionPolicy.EXACT, 1),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        storage_kinds=frozenset({StorageKind.ORDINARY}),
        use_profile=_profile(mention="allow", ground="allow", compose="allow", query="allow"),
        provenance=SchemaProvenance(evidence_refs=(evidence_ref,)),
    )


def _tag(value: Any) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in str(value)).strip("-").lower()


def _ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)
