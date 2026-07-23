"""Deterministic exact semantic composition baseline for CEMM v3.5.1 Phase 10.

The implementation is deliberately language-agnostic.  It executes reviewed generic
ConstructionProgramOperation records, exact semantic definitions and grounding evidence;
it never branches on English strings, concept names or transcript templates.

Before Phase 13 installs recurrent dynamics this baseline is the canonical Stage 5→7
semantic path.  After Phase 13 it remains the deterministic debugging oracle and shadow
comparator; it never becomes a competing semantic representation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import exp
from typing import Any, Iterable, Mapping

from ..csir.authority import CURRENT_KERNEL_ABI
from ..csir.authority_v351 import (
    AuthoritySnapshotV351,
    HardConstraintEvaluation,
    HardConstraintTrace,
    SemanticAuthorityError,
    SemanticDefinition,
    SemanticDefinitionCompiler,
    semantic_structural_exact_fingerprint,
)
from ..csir.canonical_v351 import exact_fingerprint, normalize, semantic_fingerprint
from ..csir.model import (
    CSIRCandidateFragment,
    CSIRGraph,
    CSIRNodeKind,
    CSIRRef,
    ExactAuthorityPin,
    SemanticTerm,
    SemanticVariable,
    TermKind,
)
from ..language.model import ConstructionProgramOperation, SenseCandidate
from ..runtime_abi import (
    ActivationGraph,
    ActivationTrace,
    ConvergenceAssessment,
    SemanticAttractor,
    SemanticAttractorSet,
    artifact_ref,
)
from ..schema.model import SchemaClass, SchemaLifecycleStatus, UseDecision, UseOperation, semantic_fingerprint as runtime_fingerprint
from .model import (
    CandidateActivation,
    CompositionFrontier,
    DeterministicActivationPayload,
    DeterministicCompositionBudget,
)
from .program_vm import DeterministicConstructionProgramVM


class DeterministicCompositionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _RootPlan:
    definition_pin: ExactAuthorityPin
    construction_ref: str
    construction_revision: int
    arguments: tuple[tuple[ExactAuthorityPin, CSIRRef], ...]
    external_terms: tuple[SemanticTerm, ...]
    evidence_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    prior_score: float
    projection_authority_pins: tuple[ExactAuthorityPin, ...] = ()


class DeterministicCSIRComposer:
    """Bounded generic form/construction/grounding → exact CSIR compiler."""

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "deterministic_csir_composer"

    def __init__(
        self,
        store,
        *,
        budget: DeterministicCompositionBudget | None = None,
        constraint_evaluator: Any | None = None,
    ) -> None:
        self.store = store
        self.budget = budget or DeterministicCompositionBudget()
        self.constraint_evaluator = constraint_evaluator

    @staticmethod
    def _definition_for_ref_revision(
        snapshot: AuthoritySnapshotV351, ref: str, revision: int
    ) -> SemanticDefinition:
        matches = tuple(
            item for item in snapshot.semantic_definitions
            if item.definition_pin.ref == ref and item.definition_pin.revision == revision
        )
        if len(matches) != 1:
            raise DeterministicCompositionError(
                f"exact semantic definition selection requires one match:{ref}@{revision}:{len(matches)}"
            )
        return matches[0]

    @staticmethod
    def _definition_for_target(
        snapshot: AuthoritySnapshotV351, target_ref: str | None, target_revision: int | None
    ) -> SemanticDefinition | None:
        if target_ref is None or target_revision is None:
            return None
        matches = tuple(
            item for item in snapshot.semantic_definitions
            if item.definition_pin.ref == target_ref
            and item.definition_pin.revision == target_revision
        )
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _selected_grounding(grounding_candidates) -> tuple[Mapping[str, str], Mapping[str, Any]]:
        result = getattr(grounding_candidates, "result", None)
        if result is None or result.selected_assignment_ref is None:
            return {}, {}
        assignment = next(
            (item for item in result.assignments if item.assignment_ref == result.selected_assignment_ref),
            None,
        )
        if assignment is None:
            return {}, {}
        mention_map = dict(assignment.mention_to_target)
        mentions = {item.mention_ref: item for item in result.mentions}
        return mention_map, mentions

    @staticmethod
    def _candidate_span(ref: str, form_lattice) -> tuple[int, int] | None:
        forms = {item.candidate_ref: item for item in form_lattice.form_candidates}
        senses = {item.candidate_ref: item for item in form_lattice.sense_candidates}
        observations = {item.observation_ref: item for item in form_lattice.observations}
        observation = observations.get(ref)
        if observation is not None:
            return observation.span.start, observation.span.end
        form = forms.get(ref)
        if form is None:
            sense = senses.get(ref)
            if sense is not None:
                form = forms.get(sense.form_candidate_ref)
        if form is None:
            return None
        return form.span.start, form.span.end

    @classmethod
    def _grounded_target_for_candidate(
        cls,
        ref: str,
        form_lattice,
        mention_to_target: Mapping[str, str],
        mentions: Mapping[str, Any],
    ) -> str | None:
        span = cls._candidate_span(ref, form_lattice)
        if span is None:
            return None
        start, end = span
        targets = {
            mention_to_target[mention_ref]
            for mention_ref, mention in mentions.items()
            if mention_ref in mention_to_target
            and mention.span.start <= start
            and end <= mention.span.end
        }
        return next(iter(targets)) if len(targets) == 1 else None

    @staticmethod
    def _term(target_ref: str, *, context_ref: str, evidence_refs: Iterable[str]) -> SemanticTerm:
        token = runtime_fingerprint(
            "composition-grounded-term", (target_ref, context_ref), 20
        )
        return SemanticTerm(
            term_ref=f"grounded:{token}",
            term_kind=TermKind.REFERENT,
            identity_ref=target_ref,
            authority_pins=(),
        )

    @staticmethod
    def _projection_pins(form_lattice, registry, snapshot: AuthoritySnapshotV351) -> tuple[ExactAuthorityPin, ...]:
        """Pin every independently revisioned language authority used by the lattice."""
        auxiliary = tuple(snapshot.auxiliary_exact_pins)
        result: dict[tuple[str, str, str, int, str, str], ExactAuthorityPin] = {}

        def add(kind: str, ref: str, revision: int) -> None:
            matches = tuple(
                pin for pin in auxiliary
                if pin.kind == kind and pin.ref == ref and pin.revision == revision
            )
            if len(matches) != 1:
                raise DeterministicCompositionError(
                    f"exact language projection authority requires one pin:{kind}:{ref}@{revision}:{len(matches)}"
                )
            result[matches[0].key] = matches[0]

        def add_pack(item) -> None:
            if hasattr(item, "pack_ref") and hasattr(item, "pack_revision"):
                add("language_pack", str(item.pack_ref), int(item.pack_revision))

        for candidate in form_lattice.form_candidates:
            form = registry.require_form(candidate.form_ref, candidate.form_revision)
            add("language_form", form.form_ref, form.revision); add_pack(form)
            if candidate.morphology_rule_ref is not None:
                rule = registry.require_morphology_analysis_rule(
                    candidate.morphology_rule_ref, candidate.morphology_rule_revision
                )
                add("morphology_analysis_rule", rule.rule_ref, rule.revision); add_pack(rule)
            if candidate.derived_lexeme_ref is not None:
                lexeme = registry.require_lexeme(candidate.derived_lexeme_ref, candidate.derived_lexeme_revision)
                add("lexeme", lexeme.lexeme_ref, lexeme.revision); add_pack(lexeme)

        for candidate in form_lattice.lexeme_candidates:
            lexeme = registry.require_lexeme(candidate.lexeme_ref, candidate.lexeme_revision)
            add("lexeme", lexeme.lexeme_ref, lexeme.revision); add_pack(lexeme)
            if candidate.link_ref is not None:
                add("form_lexeme_link", candidate.link_ref, int(candidate.link_revision))

        for candidate in form_lattice.sense_candidates:
            sense = registry.require_sense(candidate.sense_ref, candidate.sense_revision)
            add("lexical_sense", sense.sense_ref, sense.revision); add_pack(sense)
            if candidate.lexeme_ref is not None:
                lexeme = registry.require_lexeme(candidate.lexeme_ref, candidate.lexeme_revision)
                add("lexeme", lexeme.lexeme_ref, lexeme.revision); add_pack(lexeme)
            if candidate.authority_ref:
                kind = (
                    "lexeme_sense_link" if candidate.authority_path == "lexeme"
                    else "form_sense_link"
                )
                add(kind, candidate.authority_ref, int(candidate.authority_revision))
            for contribution in candidate.contributions:
                if contribution.spec_ref is not None:
                    add(
                        "semantic_contribution_spec", contribution.spec_ref,
                        int(contribution.spec_revision),
                    )

        for candidate in form_lattice.construction_candidates:
            construction = registry.require_construction(
                candidate.construction_ref, candidate.construction_revision
            )
            add("construction", construction.construction_ref, construction.revision); add_pack(construction)
            for program in registry.programs_for_construction(
                construction.construction_ref, construction.revision
            ):
                add("construction_program", program.program_ref, program.revision); add_pack(program)
        return tuple(result[key] for key in sorted(result))

    @staticmethod
    def _port(definition: SemanticDefinition, ref: str) -> ExactAuthorityPin:
        matches = tuple(item.port_pin for item in definition.formal_ports if item.port_pin.ref == ref)
        if len(matches) != 1:
            raise DeterministicCompositionError(
                f"construction program port must resolve to one exact formal port:{definition.definition_pin.ref}:{ref}:{len(matches)}"
            )
        return matches[0]

    def _root_definitions(
        self,
        *,
        program,
        construction_candidate,
        form_lattice,
        closure_candidates,
        authority_snapshot: AuthoritySnapshotV351,
    ) -> tuple[SemanticDefinition, ...]:
        selected: dict[tuple[str, str, str, int, str, str], SemanticDefinition] = {}
        step_count = 0
        for step in program.steps:
            step_count += 1
            if step_count > self.budget.maximum_program_steps:
                raise DeterministicCompositionError("construction program step budget exceeded")
            if step.operation in {
                ConstructionProgramOperation.INSTANTIATE_SCHEMA,
                ConstructionProgramOperation.WRAP_DISCOURSE_ACT,
            }:
                definition = self._definition_for_ref_revision(
                    authority_snapshot, step.schema_ref, int(step.schema_revision)
                )
                selected[definition.definition_pin.key] = definition
            elif step.operation == ConstructionProgramOperation.ACTIVATE_SCHEMA_CLASS_CANDIDATES:
                allowed_classes = set(step.schema_classes)
                candidates = []
                for closure in closure_candidates:
                    if getattr(closure, "schema_class", None) not in allowed_classes:
                        continue
                    try:
                        candidates.append(
                            self._definition_for_ref_revision(
                                authority_snapshot,
                                str(closure.schema_ref),
                                int(closure.schema_revision),
                            )
                        )
                    except DeterministicCompositionError:
                        continue
                for definition in candidates[: self.budget.maximum_schema_class_candidates]:
                    selected[definition.definition_pin.key] = definition
        if selected:
            return tuple(selected[key] for key in sorted(selected))

        # A construction may be structurally transparent and rely on a target-bearing sense.
        sense_by_ref = {item.candidate_ref: item for item in form_lattice.sense_candidates}
        refs = set(construction_candidate.trigger_refs)
        refs.update(ref for _slot, fillers in construction_candidate.slot_fillers for ref in fillers)
        for ref in sorted(refs):
            sense = sense_by_ref.get(ref)
            if sense is None:
                continue
            definition = self._definition_for_target(
                authority_snapshot, sense.target_ref, sense.target_revision
            )
            if definition is not None:
                selected[definition.definition_pin.key] = definition
        return tuple(selected[key] for key in sorted(selected))

    def _plans_for_construction(
        self,
        *,
        construction_candidate,
        program,
        registry,
        form_lattice,
        grounding_candidates,
        closure_candidates,
        authority_snapshot: AuthoritySnapshotV351,
        context_ref: str,
        projection_authority_pins: tuple[ExactAuthorityPin, ...],
    ) -> tuple[_RootPlan, ...]:
        mention_to_target, mentions = self._selected_grounding(grounding_candidates)
        construction = registry.require_construction(
            construction_candidate.construction_ref,
            construction_candidate.construction_revision,
        )
        root_definitions = self._root_definitions(
            program=program,
            construction_candidate=construction_candidate,
            form_lattice=form_lattice,
            closure_candidates=closure_candidates,
            authority_snapshot=authority_snapshot,
        )
        if not root_definitions:
            return ()

        slot_fillers = dict(construction_candidate.slot_fillers)
        plans: list[_RootPlan] = []
        for definition in root_definitions:
            arguments: dict[tuple[str, str, str, int, str, str], tuple[ExactAuthorityPin, CSIRRef]] = {}
            terms: dict[str, SemanticTerm] = {}

            # Construction slot semantic_port_ref is reviewed data and provides the
            # language-independent binding bridge into exact definition formal ports.
            for slot in construction.slots:
                if not slot.semantic_port_ref:
                    continue
                fillers = tuple(slot_fillers.get(slot.slot_ref, ()))
                if not fillers:
                    continue
                if len(fillers) != 1:
                    raise DeterministicCompositionError(
                        f"baseline exact argument binding currently requires singular slot filler:{slot.slot_ref}"
                    )
                target = self._grounded_target_for_candidate(
                    fillers[0], form_lattice, mention_to_target, mentions
                )
                if target is None:
                    continue
                term = self._term(target, context_ref=context_ref, evidence_refs=construction_candidate.evidence_refs)
                terms[term.term_ref] = term
                port = self._port(definition, slot.semantic_port_ref)
                arguments[port.key] = (port, term.node_ref)

            # Explicit generic BIND_PORT_FROM_SLOT steps override/inform slot metadata.
            for step in program.steps:
                if step.operation != ConstructionProgramOperation.BIND_PORT_FROM_SLOT:
                    continue
                fillers = tuple(slot_fillers.get(step.slot_ref, ()))
                if not fillers:
                    continue
                if len(fillers) != 1:
                    raise DeterministicCompositionError(
                        f"program port binding requires singular filler:{step.slot_ref}"
                    )
                target = self._grounded_target_for_candidate(
                    fillers[0], form_lattice, mention_to_target, mentions
                )
                if target is None:
                    continue
                term = self._term(target, context_ref=context_ref, evidence_refs=construction_candidate.evidence_refs)
                terms[term.term_ref] = term
                port = self._port(definition, step.port_ref)
                arguments[port.key] = (port, term.node_ref)

            plans.append(
                _RootPlan(
                    definition_pin=definition.definition_pin,
                    construction_ref=construction.construction_ref,
                    construction_revision=construction.revision,
                    arguments=tuple(arguments[key] for key in sorted(arguments)),
                    external_terms=tuple(terms[key] for key in sorted(terms)),
                    evidence_refs=tuple(sorted(set(construction_candidate.evidence_refs))),
                    source_refs=(construction_candidate.candidate_ref, program.program_ref),
                    prior_score=float(construction_candidate.confidence),
                    projection_authority_pins=projection_authority_pins,
                )
            )
        return tuple(plans)

    def _constraint_trace(
        self,
        *,
        graph: CSIRGraph,
        proof,
        authority_snapshot: AuthoritySnapshotV351,
        context_ref: str,
        evidence_refs: tuple[str, ...],
    ) -> HardConstraintTrace | None:
        if not proof.constraint_pins:
            return None
        if self.constraint_evaluator is None:
            raise DeterministicCompositionError(
                "exact definition requires hard-constraint evaluator but none is installed"
            )
        evaluations: list[HardConstraintEvaluation] = []
        for pin in proof.constraint_pins:
            result = self.constraint_evaluator.evaluate(
                constraint_pin=pin,
                graph=graph,
                authority_snapshot=authority_snapshot,
                context_ref=context_ref,
            )
            if isinstance(result, HardConstraintEvaluation):
                evaluation = result
            elif isinstance(result, Mapping):
                evaluation = HardConstraintEvaluation(
                    constraint_pin=pin,
                    satisfied=bool(result.get("satisfied")),
                    evidence_refs=tuple(result.get("evidence_refs", ()) or evidence_refs),
                    evaluator_pin=result.get("evaluator_pin"),
                )
            else:
                raise TypeError("constraint evaluator must return HardConstraintEvaluation or Mapping")
            if evaluation.constraint_pin.key != pin.key:
                raise DeterministicCompositionError("constraint evaluator returned another constraint identity")
            evaluations.append(evaluation)
        trace = HardConstraintTrace(
            authority_generation=authority_snapshot.generation,
            authority_fingerprint=authority_snapshot.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=authority_snapshot.snapshot_fingerprint,
            graph_structural_exact_fingerprint=semantic_structural_exact_fingerprint(graph),
            evaluations=tuple(evaluations),
        )
        trace.verify(
            graph,
            authority_snapshot=authority_snapshot,
            required_constraint_pins=proof.constraint_pins,
        )
        return trace

    def _constraint_trace_many(
        self,
        *,
        graph: CSIRGraph,
        proofs,
        authority_snapshot: AuthoritySnapshotV351,
        context_ref: str,
        evidence_refs: tuple[str, ...],
    ) -> HardConstraintTrace | None:
        pins = {}
        for proof in proofs:
            for pin in proof.constraint_pins:
                pins[pin.key] = pin
        required = tuple(pins[key] for key in sorted(pins))
        if not required:
            return None
        if self.constraint_evaluator is None:
            raise DeterministicCompositionError(
                "composed exact definitions require hard-constraint evaluator but none is installed"
            )
        evaluations = []
        for pin in required:
            result = self.constraint_evaluator.evaluate(
                constraint_pin=pin, graph=graph, authority_snapshot=authority_snapshot,
                context_ref=context_ref,
            )
            if isinstance(result, HardConstraintEvaluation):
                evaluation = result
            elif isinstance(result, Mapping):
                evaluation = HardConstraintEvaluation(
                    constraint_pin=pin, satisfied=bool(result.get("satisfied")),
                    evidence_refs=tuple(result.get("evidence_refs", ()) or evidence_refs),
                    evaluator_pin=result.get("evaluator_pin"),
                )
            else:
                raise TypeError("constraint evaluator must return HardConstraintEvaluation or Mapping")
            if evaluation.constraint_pin.key != pin.key:
                raise DeterministicCompositionError("constraint evaluator returned another constraint identity")
            evaluations.append(evaluation)
        trace = HardConstraintTrace(
            authority_generation=authority_snapshot.generation,
            authority_fingerprint=authority_snapshot.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=authority_snapshot.snapshot_fingerprint,
            graph_structural_exact_fingerprint=semantic_structural_exact_fingerprint(graph),
            evaluations=tuple(evaluations),
        )
        trace.verify(graph, authority_snapshot=authority_snapshot, required_constraint_pins=required)
        return trace

    def compile(
        self,
        *,
        evidence_lattice,
        grounding_candidates,
        referent_projections,
        state_space_projections,
        closure_candidates,
        authority_snapshot,
        semantic_authority_snapshot_v351: AuthoritySnapshotV351,
        read_generation,
        kernel_semantic_abi,
        context_ref: str,
        permission_ref: str,
    ) -> Mapping[str, Any]:
        del referent_projections, state_space_projections, permission_ref
        if kernel_semantic_abi.fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise DeterministicCompositionError("deterministic composer kernel ABI mismatch")
        if (
            read_generation.authority_generation,
            read_generation.authority_fingerprint,
        ) != (
            semantic_authority_snapshot_v351.generation,
            semantic_authority_snapshot_v351.authority_fingerprint,
        ):
            raise DeterministicCompositionError("deterministic composer read/semantic authority generation mismatch")
        form_lattice = getattr(evidence_lattice, "form_lattice", None)
        if form_lattice is None:
            return {"candidate_fragments": (), "composition_frontiers": (
                CompositionFrontier(
                    "frontier:composition:no-form-lattice",
                    "deterministic text composition requires form/sense/construction evidence",
                ),
            )}

        with self.store.snapshot() as snapshot:
            self.store.assert_snapshot(snapshot)
            if snapshot.read_generation.cognitive_fingerprint != read_generation.cognitive_fingerprint:
                raise DeterministicCompositionError("read generation changed during deterministic composition")
            registry = self.store.repositories.language.registry(snapshot=snapshot)
            projection_pins = self._projection_pins(
                form_lattice, registry, semantic_authority_snapshot_v351
            )

            plans: list[_RootPlan] = []
            vm_results = []
            frontiers: list[CompositionFrontier] = []
            branches = 0
            vm = DeterministicConstructionProgramVM(
                semantic_authority_snapshot_v351, maximum_branches=self.budget.maximum_branches
            )
            mention_to_target, mentions = self._selected_grounding(grounding_candidates)
            for construction_candidate in form_lattice.construction_candidates:
                programs = tuple(
                    item for item in registry.programs_for_construction(
                        construction_candidate.construction_ref,
                        construction_candidate.construction_revision,
                    )
                    if item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
                    and item.use_operation == UseOperation.COMPOSE
                    and item.use_decision == UseDecision.ALLOW
                )
                if not programs:
                    frontiers.append(
                        CompositionFrontier(
                            "frontier:composition:missing-program:" + construction_candidate.candidate_ref,
                            "active exact ConstructionProgramRecord",
                            source_refs=(construction_candidate.candidate_ref,),
                            evidence_refs=tuple(construction_candidate.evidence_refs),
                        )
                    )
                    continue

                filler_terms = {}
                filler_refs = {
                    ref for _slot, fillers in construction_candidate.slot_fillers for ref in fillers
                }
                for ref in sorted(filler_refs):
                    target = self._grounded_target_for_candidate(
                        ref, form_lattice, mention_to_target, mentions
                    )
                    if target is None:
                        continue
                    term = self._term(
                        target, context_ref=context_ref,
                        evidence_refs=construction_candidate.evidence_refs,
                    )
                    filler_terms[ref] = term
                terms = {term.term_ref: term for term in filler_terms.values()}
                initial_graph = CSIRGraph(terms=tuple(terms[key] for key in sorted(terms)))
                resolver = lambda ref, values=filler_terms: (
                    None if ref not in values else values[ref].node_ref
                )
                for program in programs:
                    generated = vm.execute(
                        program=program, construction_candidate=construction_candidate,
                        initial_graph=initial_graph, slot_resolver=resolver,
                        closure_candidates=closure_candidates,
                    )
                    branches += len(generated)
                    if branches > self.budget.maximum_branches:
                        frontiers.append(
                            CompositionFrontier(
                                "frontier:composition:branch-budget",
                                "bounded discrete composition search budget",
                                source_refs=(construction_candidate.candidate_ref,),
                                effects=("partial_response", "learning"),
                            )
                        )
                        break
                    for result in generated:
                        for frontier in result.frontiers:
                            frontiers.append(
                                CompositionFrontier(
                                    frontier.frontier_ref, frontier.missing_contract,
                                    source_refs=frontier.source_refs,
                                    evidence_refs=tuple(construction_candidate.evidence_refs),
                                )
                            )
                        vm_results.append((
                            result, tuple(construction_candidate.evidence_refs),
                            float(construction_candidate.confidence), projection_pins,
                        ))
                if branches > self.budget.maximum_branches:
                    break

            # Direct exact lexical denotation is a legitimate zero-construction case.
            # It is driven only by exact SenseCandidate targets, never raw words.
            if not vm_results:
                for sense in form_lattice.sense_candidates:
                    definition = self._definition_for_target(
                        semantic_authority_snapshot_v351, sense.target_ref, sense.target_revision,
                    )
                    if definition is None or any(port.minimum > 0 for port in definition.formal_ports):
                        continue
                    plans.append(
                        _RootPlan(
                            definition.definition_pin, "direct-exact-denotation", 1, (), (),
                            tuple(sense.evidence_refs), (sense.candidate_ref,),
                            float(sense.confidence), projection_pins,
                        )
                    )
                    if len(plans) >= self.budget.maximum_fragments:
                        break

        fragments: list[CSIRCandidateFragment] = []
        unresolved = tuple(
            sorted(
                {
                    f"frontier:composition:unresolved-span:{span.start}:{span.end}"
                    for span in form_lattice.unresolved_spans
                }
            )
        )
        for vm_result, evidence_refs, prior_score, language_projection_pins in vm_results[: self.budget.maximum_fragments]:
            graph = vm_result.graph
            if unresolved:
                graph = replace(
                    graph, unresolved_refs=tuple(sorted(set((*graph.unresolved_refs, *unresolved))))
                )
            try:
                trace = self._constraint_trace_many(
                    graph=graph, proofs=vm_result.closure_proofs,
                    authority_snapshot=semantic_authority_snapshot_v351,
                    context_ref=context_ref, evidence_refs=evidence_refs,
                )
            except (SemanticAuthorityError, DeterministicCompositionError) as exc:
                frontiers.append(
                    CompositionFrontier(
                        "frontier:composition:program-rejected:"
                        + runtime_fingerprint("program-rejected", (vm_result.source_refs, str(exc)), 20),
                        "exact construction program hard constraints",
                        source_refs=vm_result.source_refs, evidence_refs=evidence_refs,
                    )
                )
                continue
            projection = {pin.key: pin for pin in (*language_projection_pins, *vm_result.projection_authority_pins)}
            fragments.append(
                CSIRCandidateFragment(
                    fragment_ref="composition-fragment:" + runtime_fingerprint(
                        "composition-program-fragment", (vm_result.source_refs, semantic_fingerprint(graph)), 24
                    ),
                    graph=graph, evidence_refs=evidence_refs,
                    closure_proofs=vm_result.closure_proofs,
                    hard_constraint_traces=() if trace is None else (trace,),
                    projection_authority_pins=tuple(projection[key] for key in sorted(projection)),
                    requires_projection_authority=bool(graph.applications),
                    prior_score=prior_score,
                )
            )

        for plan in plans[: self.budget.maximum_fragments]:
            compiler = SemanticDefinitionCompiler(semantic_authority_snapshot_v351)
            external_graph = CSIRGraph(terms=plan.external_terms) if plan.external_terms else None
            try:
                compiled = compiler.compile(
                    plan.definition_pin,
                    external_graph=external_graph,
                    arguments=dict(plan.arguments),
                    canonicalization_budget=self.budget.canonicalization_budget,
                )
                graph = compiled.graph
                if unresolved:
                    graph = replace(
                        graph,
                        unresolved_refs=tuple(sorted(set((*graph.unresolved_refs, *unresolved)))),
                    )
                trace = self._constraint_trace(
                    graph=graph,
                    proof=compiled.closure_proof,
                    authority_snapshot=semantic_authority_snapshot_v351,
                    context_ref=context_ref,
                    evidence_refs=plan.evidence_refs,
                )
            except (SemanticAuthorityError, DeterministicCompositionError) as exc:
                frontiers.append(
                    CompositionFrontier(
                        "frontier:composition:plan-rejected:"
                        + runtime_fingerprint("composition-plan-rejected", (plan.source_refs, str(exc)), 20),
                        "exact definition closure / hard constraints / required grounding",
                        source_refs=plan.source_refs,
                        evidence_refs=plan.evidence_refs,
                    )
                )
                continue
            fragments.append(
                CSIRCandidateFragment(
                    fragment_ref="composition-fragment:"
                    + runtime_fingerprint(
                        "composition-fragment",
                        (plan.source_refs, semantic_fingerprint(graph)),
                        24,
                    ),
                    graph=graph,
                    evidence_refs=plan.evidence_refs,
                    closure_proofs=(compiled.closure_proof,),
                    hard_constraint_traces=() if trace is None else (trace,),
                    projection_authority_pins=plan.projection_authority_pins,
                    requires_projection_authority=bool(graph.applications),
                    prior_score=plan.prior_score,
                )
            )

        return {
            "candidate_fragments": tuple(fragments),
            "composition_frontiers": tuple(frontiers),
        }


class DeterministicMeaningDynamics:
    """One-pass exact baseline used before learned recurrent Phase-13 dynamics exists."""

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "deterministic_meaning_dynamics"

    def run(
        self,
        *,
        csir_candidates,
        authority_snapshot,
        semantic_authority_snapshot_v351: AuthoritySnapshotV351,
        dynamics_parameters,
        read_generation,
        budgets,
    ):
        del authority_snapshot, read_generation, budgets
        activations = []
        graphs = []
        for candidate in csir_candidates.candidates:
            support = float(candidate.prior_score)
            activations.append(
                CandidateActivation(
                    candidate_ref=candidate.candidate_ref,
                    semantic_fingerprint=candidate.semantic_fingerprint,
                    exact_fingerprint=candidate.exact_fingerprint,
                    support=support,
                    score_components=(("deterministic_prior", support),),
                    evidence_refs=candidate.evidence_refs,
                    frontier_refs=tuple(candidate.graph.unresolved_refs),
                )
            )
            graphs.append((candidate.candidate_ref, candidate.graph))
        open_variables = tuple(
            sorted(
                {variable.node_ref for candidate in csir_candidates.candidates for variable in candidate.graph.variables},
                key=lambda ref: (ref.kind.value, ref.ref),
            )
        )
        frontier_refs = tuple(
            sorted({ref for candidate in csir_candidates.candidates for ref in candidate.graph.unresolved_refs})
        )
        partial = None
        if len(graphs) == 1 and (open_variables or frontier_refs):
            partial = graphs[0][1]
        payload = DeterministicActivationPayload(
            payload_ref=artifact_ref(
                "deterministic-activation",
                tuple((item.candidate_ref, item.semantic_fingerprint) for item in activations),
            ),
            candidate_activations=tuple(activations),
            candidate_graphs=tuple(graphs),
            partial_graph=partial,
            open_variables=open_variables,
            frontier_refs=frontier_refs,
            authority_pins=tuple(item.parameter_pin for item in dynamics_parameters),
            metadata={"baseline": "deterministic_exact_composition", "learned_parameters_required": False},
        )
        graph = ActivationGraph(
            graph_ref=artifact_ref("activation-graph", payload.payload_ref),
            payload=payload,
            authority_generation=csir_candidates.authority_generation,
            authority_fingerprint=csir_candidates.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=semantic_authority_snapshot_v351.snapshot_fingerprint,
            dynamics_parameter_pins=tuple(
                item.parameter_pin
                for item in sorted(dynamics_parameters, key=lambda item: item.parameter_family)
            ),
            proof_refs=("proof:deterministic-exact-baseline",),
        )
        trace = ActivationTrace(
            trace_ref=artifact_ref("activation-trace", payload.payload_ref),
            iterations=1,
            convergence_delta=0.0,
            proof_refs=("proof:deterministic-no-learned-propagation",),
        )
        return graph, trace


class DeterministicAttractorStabilizer:
    """Canonical-class stabilizer for the deterministic Phase-10 baseline."""

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "deterministic_attractor_stabilizer"

    def __init__(self, *, ambiguity_margin: float = 0.05) -> None:
        if ambiguity_margin < 0:
            raise ValueError("ambiguity margin cannot be negative")
        self.ambiguity_margin = ambiguity_margin

    def stabilize(
        self,
        *,
        activation_graph: ActivationGraph,
        activation_trace: ActivationTrace,
        authority_snapshot,
        semantic_authority_snapshot_v351: AuthoritySnapshotV351,
        budgets,
    ) -> SemanticAttractorSet:
        del authority_snapshot, budgets
        payload = activation_graph.payload
        if not isinstance(payload, DeterministicActivationPayload):
            raise TypeError("deterministic stabilizer requires DeterministicActivationPayload")
        graph_by_ref = dict(payload.candidate_graphs)
        scores = [item.support for item in payload.candidate_activations]
        if scores:
            peak = max(scores)
            weights = [exp(score - peak) for score in scores]
            denominator = sum(weights)
        else:
            weights = []
            denominator = 1.0
        attractors = []
        for item, weight in zip(payload.candidate_activations, weights):
            graph = normalize(graph_by_ref[item.candidate_ref])
            attractors.append(
                SemanticAttractor(
                    attractor_ref=artifact_ref("semantic-attractor", item.semantic_fingerprint),
                    graph=graph,
                    semantic_fingerprint=semantic_fingerprint(graph),
                    support=weight / denominator,
                    energy=-item.support,
                    derivation_refs=(item.candidate_ref, *item.evidence_refs),
                )
            )
        attractors.sort(key=lambda item: (-item.support, item.semantic_fingerprint))
        ambiguous = (
            len(attractors) > 1
            and attractors[0].support - attractors[1].support <= self.ambiguity_margin
        )
        reason_refs = []
        if ambiguous:
            reason_refs.append("deterministic_close_alternatives")
        if payload.frontier_refs:
            reason_refs.append("partial_unresolved_evidence")
        convergence = ConvergenceAssessment(
            converged=not bool(payload.frontier_refs),
            semantic_normal_form_stable=True,
            activation_delta=activation_trace.convergence_delta,
            epsilon=0.0,
            reason_refs=tuple(reason_refs),
        )
        partial = payload.partial_graph
        if partial is None and attractors and (payload.open_variables or payload.frontier_refs):
            partial = attractors[0].graph
        return SemanticAttractorSet(
            attractor_set_ref=artifact_ref(
                "semantic-attractor-set",
                tuple(item.semantic_fingerprint for item in attractors),
                tuple(payload.frontier_refs),
            ),
            attractors=tuple(attractors),
            partial_meaning=partial,
            open_variables=payload.open_variables,
            convergence=convergence,
            authority_generation=activation_graph.authority_generation,
            authority_fingerprint=activation_graph.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=semantic_authority_snapshot_v351.snapshot_fingerprint,
            dynamics_parameter_pins=activation_graph.dynamics_parameter_pins,
            proof_refs=("proof:deterministic-canonical-class-stabilization",),
        )


__all__ = [
    "DeterministicAttractorStabilizer",
    "DeterministicCSIRComposer",
    "DeterministicCompositionError",
    "DeterministicMeaningDynamics",
]
