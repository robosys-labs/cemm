"""Schema activation, joint referent/port solving and UOL bundle selection."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, Mapping

from .context import ContextSnapshot
from .language import primary_language, spans_in_clause
from .lifecycle import LifecycleEnvironment, SchemaLifecycleCoordinator
from .model import (
    CommunicativeForce,
    ContextMode,
    FormLattice,
    FormSpanCandidate,
    GapKind,
    GapRecord,
    GroundingCandidate,
    MeaningBundle,
    MeaningHypothesis,
    Polarity,
    PortBinding,
    OperationalPort,
    SchemaUseOperation,
    SchemaUseProfile,
    Predication,
    PredicateSchema,
    PropositionPayload,
    Referent,
    ReferentKind,
    SelectionAssessment,
    UOLGraph,
    semantic_hash,
)
from .schema import SemanticSchemaStore
from .storage import SemanticStore


@dataclass(frozen=True, slots=True)
class SchemaActivation:
    activation_id: str
    schema: PredicateSchema
    trigger_span_ref: str
    clause_ref: str
    score: float
    evidence_refs: tuple[str, ...]
    fixed_bindings: Mapping[str, str]
    metadata: Mapping[str, Any]
    use_profile: SchemaUseProfile
    operational_ports: tuple[OperationalPort, ...]


@dataclass(frozen=True, slots=True)
class UnderstandingResult:
    activations: tuple[SchemaActivation, ...]
    hypotheses: tuple[MeaningHypothesis, ...]
    bundle: MeaningBundle | None
    gaps: tuple[GapRecord, ...]
    incomplete: bool = False


class SchemaActivator:
    def __init__(self, schema_store: SemanticSchemaStore, lifecycle: SchemaLifecycleCoordinator):
        self._schemas = schema_store
        self._lifecycle = lifecycle

    def activate(
        self,
        lattice: FormLattice,
        *,
        context_ref: str,
        analyzer_fingerprint: str = "",
        max_per_clause: int = 16,
    ) -> tuple[SchemaActivation, ...]:
        activations: list[SchemaActivation] = []
        clauses = [span for span in lattice.spans if span.span_id in lattice.clause_span_refs]
        environment = LifecycleEnvironment(
            store_revision=self._lifecycle._store.revision,
            foundation_fingerprint=self._schemas.fingerprint,
            analyzer_fingerprint=analyzer_fingerprint,
        )
        for clause in clauses:
            candidates: dict[tuple[str, str], SchemaActivation] = {}
            for span in spans_in_clause(lattice, clause.span_id):
                refs = [ref for ref in span.semantic_refs if ref.startswith("predicate:")]
                hint = span.features.get("semantic_hint") if span.features else None
                if hint and str(hint).startswith("predicate:"):
                    refs.append(str(hint))
                for ref in refs:
                    schema = self._schemas.maybe_predicate(ref)
                    if schema is None:
                        continue
                    profile = self._lifecycle.profile(
                        schema.schema_ref, context_ref=context_ref,
                        operation=SchemaUseOperation.COMPOSE, environment=environment,
                    )
                    if not profile.permits(SchemaUseOperation.COMPOSE):
                        continue
                    ports = self._lifecycle.project_ports(
                        schema.schema_ref, context_ref=context_ref,
                        operation=SchemaUseOperation.COMPOSE, environment=environment,
                    )
                    key = (schema.schema_ref, span.span_id)
                    status_factor = 1.0 if schema.status.value == "active" else 0.82
                    activation = SchemaActivation(
                        activation_id=semantic_hash("activation", (
                            lattice.lattice_id, clause.span_id, span.span_id, ref,
                            profile.dependency_fingerprint,
                        )),
                        schema=schema,
                        trigger_span_ref=span.span_id,
                        clause_ref=clause.span_id,
                        score=span.confidence * status_factor,
                        evidence_refs=tuple(dict.fromkeys(span.evidence_refs + profile.evidence_refs)),
                        fixed_bindings={
                            str(k): str(v)
                            for k, v in (span.features.get("fixed_bindings", {}) or {}).items()
                        },
                        metadata={
                            "span_start": span.start,
                            "span_end": span.end,
                            "language_tag": span.language_tag,
                            "features": dict(span.features),
                            "schema_use_profile_ref": profile.profile_id,
                        },
                        use_profile=profile,
                        operational_ports=ports,
                    )
                    current = candidates.get(key)
                    if current is None or activation.score > current.score:
                        candidates[key] = activation
            activations.extend(sorted(
                candidates.values(), key=lambda item: (item.score, item.activation_id), reverse=True
            )[:max_per_clause])
        return tuple(activations)


class JointMeaningAssembler:
    def __init__(self, schema_store: SemanticSchemaStore, store: SemanticStore, max_hypotheses: int = 64):
        self._schemas = schema_store
        self._store = store
        self.max_hypotheses = max_hypotheses

    def assemble(
        self,
        lattice: FormLattice,
        activations: Iterable[SchemaActivation],
        grounding_candidates: Mapping[str, tuple[GroundingCandidate, ...]],
        context: ContextSnapshot,
    ) -> tuple[tuple[MeaningHypothesis, ...], tuple[GapRecord, ...]]:
        activations = tuple(activations)
        force = self._force(lattice)
        polarity = self._polarity(lattice)
        all_hypotheses: list[MeaningHypothesis] = []
        gaps: list[GapRecord] = []
        for activation in activations:
            trigger = next(span for span in lattice.spans if span.span_id == activation.trigger_span_ref)
            clause = next(span for span in lattice.spans if span.span_id == activation.clause_ref)
            pool = self._candidate_pool(
                lattice, activation, trigger, clause, grounding_candidates, context, activations
            )
            hypotheses, activation_gaps = self._bind_activation(
                lattice, activation, trigger, force, polarity, pool, context
            )
            all_hypotheses.extend(hypotheses)
            gaps.extend(activation_gaps)
        if not activations:
            gaps.extend(self._gaps_without_activation(lattice))
        ranked = sorted(all_hypotheses, key=lambda item: item.score, reverse=True)
        return tuple(ranked[: self.max_hypotheses]), tuple(_dedupe_gaps(gaps))

    def _candidate_pool(
        self,
        lattice: FormLattice,
        activation: SchemaActivation,
        trigger: FormSpanCandidate,
        clause: FormSpanCandidate,
        grounding_candidates: Mapping[str, tuple[GroundingCandidate, ...]],
        context: ContextSnapshot,
        all_activations: tuple[SchemaActivation, ...],
    ) -> tuple[tuple[FormSpanCandidate | None, GroundingCandidate], ...]:
        candidate_items: list[tuple[FormSpanCandidate | None, GroundingCandidate]] = []
        trigger_center = (trigger.start + trigger.end) / 2
        neighbor_centers = sorted(
            (
                ((float(item.metadata["span_start"]) + float(item.metadata["span_end"])) / 2, item)
                for item in all_activations
                if item.clause_ref == activation.clause_ref and item.activation_id != activation.activation_id
            ),
            key=lambda pair: pair[0],
        )
        left_boundary = clause.start
        right_boundary = clause.end
        for center, _ in neighbor_centers:
            if center < trigger_center:
                left_boundary = max(left_boundary, int(center))
            elif center > trigger_center:
                right_boundary = min(right_boundary, int(center))
                break
        span_by_id = {span.span_id: span for span in lattice.spans}
        for span_ref, candidates in grounding_candidates.items():
            span = span_by_id.get(span_ref)
            if span is None or not (left_boundary <= span.start and span.end <= right_boundary):
                continue
            for candidate in candidates:
                candidate_items.append((span, candidate))
        for port_id, referent_ref in activation.fixed_bindings.items():
            referent = next(
                (
                    candidate.referent
                    for candidates in grounding_candidates.values()
                    for candidate in candidates
                    if candidate.referent.referent_id == referent_ref
                ),
                None,
            )
            if referent is None:
                referent = self._store.get_referent(referent_ref)
            if referent is None:
                # Create a schema-topic reference only as an explicit fixed
                # semantic anchor. It will be validated against the store later.
                referent = Referent(
                    referent_id=referent_ref,
                    kind=ReferentKind.SCHEMA,
                    type_refs=("kind:schema",),
                    context_ref=context.context_ref,
                    scope_ref="global",
                )
            candidate_items.append((None, GroundingCandidate(
                candidate_id=semantic_hash("ground", (activation.activation_id, port_id, referent_ref)),
                mention_span_ref=activation.trigger_span_ref,
                referent=referent,
                score=1.0,
                score_parts={"fixed_binding": 1.0},
                evidence_refs=activation.evidence_refs,
                provisional=False,
            )))
        composite = self._composite_text_candidate(
            lattice, activation, trigger, clause, left_boundary, right_boundary, context
        )
        if composite is not None:
            candidate_items.append(composite)
        return tuple(candidate_items)

    @staticmethod
    def _composite_text_candidate(
        lattice: FormLattice,
        activation: SchemaActivation,
        trigger: FormSpanCandidate,
        clause: FormSpanCandidate,
        left_boundary: int,
        right_boundary: int,
        context: ContextSnapshot,
    ) -> tuple[FormSpanCandidate, GroundingCandidate] | None:
        unresolved = [
            span for span in lattice.spans
            if span.candidate_kind in {"unresolved", "text", "name_candidate"}
            and max(trigger.end, left_boundary) <= span.start
            and span.end <= right_boundary
        ]
        if not unresolved:
            return None
        unresolved.sort(key=lambda item: item.start)
        # Preserve only the first contiguous group after the predicate. This is
        # evidence aggregation, not a language-specific name/value parser.
        group = [unresolved[0]]
        for span in unresolved[1:]:
            gap = lattice.raw_text[group[-1].end:span.start]
            if any(char in gap for char in ".!?;:"):
                break
            group.append(span)
        start = group[0].start
        end = group[-1].end
        surface = lattice.raw_text[start:end].strip(" ,")
        if not surface:
            return None
        span_id = semantic_hash("span:composite", (lattice.lattice_id, start, end))
        span = FormSpanCandidate(
            span_id=span_id,
            start=start,
            end=end,
            surface=surface,
            normalized=" ".join(surface.casefold().split()),
            candidate_kind="text",
            language_tag=primary_language(lattice),
            confidence=0.72,
            evidence_refs=tuple(ref for item in group for ref in item.evidence_refs),
            features={"composed_from": tuple(item.span_id for item in group)},
        )
        referent = Referent(
            referent_id=semantic_hash("referent:text", (surface, context.context_ref)),
            kind=ReferentKind.TEXT,
            type_refs=("kind:text",),
            payload={"text": surface},
            scope_ref=context.context_ref,
            context_ref=context.context_ref,
            metadata={"source_span_ref": span_id},
        )
        candidate = GroundingCandidate(
            candidate_id=semantic_hash("ground", (span_id, referent.referent_id)),
            mention_span_ref=span_id,
            referent=referent,
            score=0.72,
            score_parts={"composite_mention": 0.72},
            evidence_refs=span.evidence_refs,
            provisional=True,
        )
        return span, candidate

    def _bind_activation(
        self,
        lattice: FormLattice,
        activation: SchemaActivation,
        trigger: FormSpanCandidate,
        force: CommunicativeForce,
        polarity: Polarity,
        pool: tuple[tuple[FormSpanCandidate | None, GroundingCandidate], ...],
        context: ContextSnapshot,
    ) -> tuple[list[MeaningHypothesis], list[GapRecord]]:
        schema = activation.schema
        ports = tuple(item.port_schema for item in activation.operational_ports)
        candidate_lists: list[tuple[Any, ...]] = []
        for port in ports:
            fixed_ref = activation.fixed_bindings.get(port.port_id)
            compatible = []
            for span, candidate in pool:
                if fixed_ref and candidate.referent.referent_id != fixed_ref:
                    continue
                if not port.accepts(candidate.referent):
                    continue
                score = self._port_score(port, trigger, span, candidate, schema)
                if score <= 0:
                    continue
                compatible.append((candidate, span, score))
            compatible.sort(key=lambda value: value[2], reverse=True)
            options: list[Any] = compatible[:8]
            if force == CommunicativeForce.ASK and port.query_open:
                options.append((None, None, 0.62))
            if not port.required:
                options.append(("omit", None, 0.0))
            candidate_lists.append(tuple(options))

        hypotheses: list[MeaningHypothesis] = []
        gaps: list[GapRecord] = []
        if any(not options for options in candidate_lists):
            for port, options in zip(ports, candidate_lists):
                if not options and port.required:
                    gaps.append(GapRecord(
                        gap_id=semantic_hash("gap", (activation.activation_id, port.port_id)),
                        kind=GapKind.PORT,
                        target_ref=f"{schema.schema_ref}.{port.port_id}",
                        reason="required_port_has_no_compatible_referent",
                        expected_type_refs=tuple(sorted(port.accepted_type_refs)),
                        evidence_refs=activation.evidence_refs,
                        learnable=False,
                        repair_options=("resolve_reference", "clarify_port_filler"),
                    ))
            return hypotheses, gaps

        combinations = product(*candidate_lists)
        for combination_index, combination in enumerate(combinations):
            if combination_index >= 64:
                break
            used_refs: set[str] = set()
            bindings: list[PortBinding] = []
            referents: dict[str, Referent] = {}
            evidence_refs: list[str] = list(activation.evidence_refs)
            assumptions: list[str] = []
            total = activation.score
            hard_failure = False
            open_count = 0
            for port, selected in zip(ports, combination):
                candidate, span, score = selected
                if candidate == "omit":
                    continue
                if candidate is None:
                    variable_ref = semantic_hash("variable", (activation.activation_id, port.port_id))
                    bindings.append(PortBinding(
                        port_id=port.port_id,
                        open_variable_ref=variable_ref,
                        confidence=score,
                        evidence_refs=activation.evidence_refs,
                    ))
                    open_count += 1
                    total += score
                    continue
                ref = candidate.referent.referent_id
                if ref in used_refs and not port.multiple:
                    # Reusing the same filler across semantically distinct ports
                    # is allowed only when explicitly configured.
                    if not bool(port.metadata.get("allow_coreference", False)):
                        hard_failure = True
                        break
                used_refs.add(ref)
                referents[ref] = candidate.referent
                bindings.append(PortBinding(
                    port_id=port.port_id,
                    referent_refs=(ref,),
                    confidence=min(1.0, score),
                    evidence_refs=candidate.evidence_refs,
                    assumptions=("provisional_referent",) if candidate.provisional else (),
                ))
                total += score
                evidence_refs.extend(candidate.evidence_refs)
                if candidate.provisional:
                    assumptions.append(f"provisional:{ref}")
            if hard_failure:
                continue
            bound_ports = {binding.port_id for binding in bindings}
            missing_required = [
                port.port_id for port in ports if port.required and port.port_id not in bound_ports
            ]
            if missing_required:
                continue
            if force == CommunicativeForce.ASK and open_count == 0:
                # A question hypothesis must contain an explicit semantic variable.
                continue
            predication = Predication(
                predication_id=semantic_hash("predication", {
                    "schema": schema.schema_ref,
                    "bindings": bindings,
                    "context": context.context_ref,
                }),
                predicate_schema_ref=schema.schema_ref,
                bindings=tuple(bindings),
                context_ref=context.context_ref,
                source_evidence_refs=tuple(dict.fromkeys(evidence_refs)),
                assumptions=tuple(assumptions),
                confidence=min(1.0, total / (len(ports) + 1)),
            )
            proposition_payload = PropositionPayload(
                predication_refs=(predication.predication_id,),
                context_ref=context.context_ref,
                polarity=polarity,
                communicative_force=force,
                attribution_ref="referent:user",
            )
            proposition = Referent(
                referent_id=semantic_hash("referent:proposition", proposition_payload),
                kind=ReferentKind.PROPOSITION,
                type_refs=("kind:proposition",),
                payload={
                    "predication_refs": proposition_payload.predication_refs,
                    "context_ref": proposition_payload.context_ref,
                    "polarity": proposition_payload.polarity.value,
                    "modality_refs": proposition_payload.modality_refs,
                    "attribution_ref": proposition_payload.attribution_ref,
                    "valid_time_ref": proposition_payload.valid_time_ref,
                    "communicative_force": proposition_payload.communicative_force.value,
                },
                scope_ref=context.context_ref,
                context_ref=context.context_ref,
                metadata={"activation_ref": activation.activation_id},
            )
            referents[proposition.referent_id] = proposition
            required_port_ids = {port.port_id for port in ports if port.required}
            covered_required = len(required_port_ids.intersection(bound_ports))
            coverage = min(1.0, covered_required / max(1, len(required_port_ids)))
            graph = UOLGraph(
                graph_id=semantic_hash("uol", (activation.activation_id, predication.predication_id)),
                referents=referents,
                predications={predication.predication_id: predication},
                proposition_refs=(proposition.referent_id,),
                unresolved_refs=tuple(
                    binding.open_variable_ref for binding in bindings if binding.open_variable_ref
                ),
                assumptions=tuple(assumptions),
                evidence_refs=tuple(dict.fromkeys(evidence_refs)),
            )
            optional_port_ids = {port.port_id for port in ports if not port.required}
            explicit_optional_bindings = sum(
                1 for binding in bindings
                if binding.port_id in optional_port_ids and binding.referent_refs
            )
            score_parts = {
                "activation": activation.score,
                "port_fit": sum(binding.confidence for binding in bindings) / max(1, len(bindings)),
                "coverage": coverage,
                # Optional ports are optional for structural completeness, not
                # semantically disposable.  When an utterance explicitly
                # supplies a compatible filler (for example the unit in
                # ``34 years``), preserving it must outrank an otherwise equal
                # omission hypothesis.  This is a generic information-retention
                # preference, not a language or predicate special case.
                "explicit_information": 0.04 * explicit_optional_bindings,
                "assumption_penalty": -0.05 * len(assumptions),
            }
            score = sum(score_parts.values())
            hypotheses.append(MeaningHypothesis(
                hypothesis_id=semantic_hash("hypothesis", (activation.activation_id, predication.predication_id)),
                graph=graph,
                proposition_refs=(proposition.referent_id,),
                communicative_force=force,
                score=score,
                score_parts=score_parts,
                coverage=coverage,
                unresolved_refs=graph.unresolved_refs,
                incompatibility_keys=(f"activation:{activation.activation_id}",),
            ))
        if not hypotheses:
            gaps.append(GapRecord(
                gap_id=semantic_hash("gap", (activation.activation_id, "no_hypothesis")),
                kind=GapKind.PORT,
                target_ref=activation.schema.schema_ref,
                reason="no_complete_port_binding_hypothesis",
                evidence_refs=activation.evidence_refs,
                learnable=False,
                repair_options=("try_alternative_referent", "clarify_meaning"),
            ))
        return hypotheses, gaps

    @staticmethod
    def _port_score(
        port: Any,
        trigger: FormSpanCandidate,
        span: FormSpanCandidate | None,
        candidate: GroundingCandidate,
        schema: PredicateSchema,
    ) -> float:
        score = candidate.score
        if span is None:
            return score + 0.5
        role_hint = str(span.features.get("role_hint", ""))
        possessive = bool(span.features.get("possessive", False))
        if role_hint and role_hint in {port.port_id, port.role_family}:
            score += 0.45
        if possessive and port.role_family in {"holder", "possessor", "subject"}:
            score += 0.35
        position = str(port.metadata.get("position", "either"))
        if position == "left" and span.end <= trigger.start:
            score += 0.2
        elif position == "right" and span.start >= trigger.end:
            score += 0.2
        elif position == "left" and span.start >= trigger.end:
            score -= 0.25
        elif position == "right" and span.end <= trigger.start:
            score -= 0.25
        preferred_kinds = {str(value) for value in port.metadata.get("preferred_kinds", ())}
        if candidate.referent.kind.value in preferred_kinds:
            score += 0.15
        return score

    @staticmethod
    def _force(lattice: FormLattice) -> CommunicativeForce:
        relation_kinds = {item.relation_kind for item in lattice.structural_relations}
        span_kinds = {span.candidate_kind for span in lattice.spans}
        semantic_refs = {ref for span in lattice.spans for ref in span.semantic_refs}
        if "correction" in relation_kinds or "force:correct" in semantic_refs:
            return CommunicativeForce.CORRECT
        if "directive" in relation_kinds or "force:direct" in semantic_refs:
            return CommunicativeForce.DIRECT
        if "question" in relation_kinds or "question_operator" in span_kinds or "force:ask" in semantic_refs:
            return CommunicativeForce.ASK
        return CommunicativeForce.ASSERT

    @staticmethod
    def _polarity(lattice: FormLattice) -> Polarity:
        relation_kinds = {item.relation_kind for item in lattice.structural_relations}
        return Polarity.NEGATIVE if "negation" in relation_kinds else Polarity.POSITIVE

    @staticmethod
    def _gaps_without_activation(lattice: FormLattice) -> list[GapRecord]:
        unresolved = tuple(lattice.unresolved_span_refs)
        if unresolved:
            return [GapRecord(
                gap_id=semantic_hash("gap", (lattice.lattice_id, "lexical")),
                kind=GapKind.LEXICAL,
                target_ref=unresolved[0],
                reason="no_active_predicate_schema_from_form_evidence",
                evidence_refs=tuple(ref for span in lattice.spans for ref in span.evidence_refs),
                learnable=False,
                repair_options=("ask_specific_meaning", "request_paraphrase"),
            )]
        return [GapRecord(
            gap_id=semantic_hash("gap", (lattice.lattice_id, "analysis")),
            kind=GapKind.ANALYSIS,
            target_ref=lattice.lattice_id,
            reason="no_semantic_activation",
            learnable=False,
            repair_options=("request_paraphrase",),
        )]


class MeaningBundleSelector:
    """Bounded maximum-score compatible-set selection with alternatives."""

    def __init__(self, exact_limit: int = 24, beam_width: int = 128):
        self.exact_limit = exact_limit
        self.beam_width = beam_width

    def select(self, hypotheses: Iterable[MeaningHypothesis]) -> MeaningBundle | None:
        ranked = sorted(hypotheses, key=lambda item: (item.score, item.hypothesis_id), reverse=True)
        if not ranked:
            return None
        if len(ranked) <= self.exact_limit:
            selected = self._branch_and_bound(ranked)
        else:
            selected = self._beam_select(ranked)
        if not selected:
            return None
        referents: dict[str, Referent] = {}
        predications: dict[str, Predication] = {}
        proposition_refs: list[str] = []
        evidence_refs: list[str] = []
        assumptions: list[str] = []
        unresolved: list[str] = []
        discourse_relations = []
        for hypothesis in selected:
            referents.update(hypothesis.graph.referents)
            predications.update(hypothesis.graph.predications)
            proposition_refs.extend(hypothesis.proposition_refs)
            evidence_refs.extend(hypothesis.graph.evidence_refs)
            assumptions.extend(hypothesis.graph.assumptions)
            unresolved.extend(hypothesis.graph.unresolved_refs)
            discourse_relations.extend(hypothesis.graph.discourse_relations)
        graph = UOLGraph(
            graph_id=semantic_hash("uol:bundle", tuple(item.hypothesis_id for item in selected)),
            referents=referents,
            predications=predications,
            proposition_refs=tuple(dict.fromkeys(proposition_refs)),
            discourse_relations=tuple(dict.fromkeys(discourse_relations)),
            unresolved_refs=tuple(dict.fromkeys(unresolved)),
            assumptions=tuple(dict.fromkeys(assumptions)),
            evidence_refs=tuple(dict.fromkeys(evidence_refs)),
        )
        selected_refs = tuple(item.hypothesis_id for item in selected)
        rejected = tuple(item.hypothesis_id for item in ranked if item.hypothesis_id not in selected_refs)
        coverage = sum(item.coverage for item in selected) / len(selected)
        compatibility = self._compatibility_score(selected)
        unresolved_problem = any(
            item.unresolved_refs and item.communicative_force != CommunicativeForce.ASK
            for item in selected
        )
        assessment = SelectionAssessment(
            selected_hypothesis_refs=selected_refs,
            rejected_hypothesis_refs=rejected,
            total_score=sum(item.score for item in selected),
            compatibility_score=compatibility,
            coverage=coverage,
            # Open query ports are deliberate semantic variables, not failed
            # reference resolution.  Only unresolved content in non-query
            # hypotheses makes the selected bundle incomplete.
            incomplete=coverage < 0.8 or unresolved_problem,
            reason="bounded_maximum_weight_compatible_set",
        )
        return MeaningBundle(
            bundle_id=semantic_hash("bundle", (selected_refs, assessment.total_score)),
            graph=graph,
            hypothesis_refs=selected_refs,
            proposition_refs=graph.proposition_refs,
            assessment=assessment,
            alternatives=rejected,
        )

    def _branch_and_bound(self, ranked: list[MeaningHypothesis]) -> list[MeaningHypothesis]:
        positive_suffix = [0.0] * (len(ranked) + 1)
        for index in range(len(ranked) - 1, -1, -1):
            positive_suffix[index] = positive_suffix[index + 1] + max(0.0, ranked[index].score)
        best_score = float("-inf")
        best: list[MeaningHypothesis] = []

        def visit(index: int, selected: list[MeaningHypothesis], score: float) -> None:
            nonlocal best_score, best
            if score + positive_suffix[index] < best_score:
                return
            if index >= len(ranked):
                tie = tuple(item.hypothesis_id for item in selected)
                best_tie = tuple(item.hypothesis_id for item in best)
                if score > best_score or (score == best_score and tie < best_tie):
                    best_score = score
                    best = list(selected)
                return
            candidate = ranked[index]
            if not self._conflicts(candidate, selected):
                selected.append(candidate)
                visit(index + 1, selected, score + candidate.score)
                selected.pop()
            visit(index + 1, selected, score)

        visit(0, [], 0.0)
        return best

    def _beam_select(self, ranked: list[MeaningHypothesis]) -> list[MeaningHypothesis]:
        beams: list[tuple[float, tuple[MeaningHypothesis, ...]]] = [(0.0, ())]
        for candidate in ranked:
            expanded = list(beams)
            for score, selected in beams:
                if not self._conflicts(candidate, selected):
                    expanded.append((score + candidate.score, selected + (candidate,)))
            expanded.sort(key=lambda item: (item[0], tuple(x.hypothesis_id for x in item[1])), reverse=True)
            beams = expanded[: self.beam_width]
        return list(beams[0][1]) if beams else []

    @classmethod
    def _conflicts(cls, candidate: MeaningHypothesis, selected: Iterable[MeaningHypothesis]) -> bool:
        candidate_keys = set(candidate.incompatibility_keys)
        candidate_props = set(candidate.proposition_refs)
        for current in selected:
            if candidate_keys.intersection(current.incompatibility_keys):
                return True
            if candidate_props.intersection(current.proposition_refs):
                return True
            if cls._semantic_contradiction(candidate, current):
                return True
        return False

    @staticmethod
    def _semantic_contradiction(left: MeaningHypothesis, right: MeaningHypothesis) -> bool:
        def signatures(item: MeaningHypothesis) -> dict[tuple[Any, ...], str]:
            result = {}
            for prop_ref in item.proposition_refs:
                prop = item.graph.referents.get(prop_ref)
                payload = prop.payload or {} if prop else {}
                polarity = str(payload.get("polarity", "positive"))
                for pred_ref in payload.get("predication_refs", ()):
                    pred = item.graph.predications.get(str(pred_ref))
                    if pred is None:
                        continue
                    signature = (pred.predicate_schema_ref, tuple(sorted(
                        (binding.port_id, tuple(binding.referent_refs))
                        for binding in pred.bindings if binding.referent_refs
                    )))
                    result[signature] = polarity
            return result
        left_sig, right_sig = signatures(left), signatures(right)
        return any(key in right_sig and right_sig[key] != polarity for key, polarity in left_sig.items())

    @classmethod
    def _compatibility_score(cls, selected: Iterable[MeaningHypothesis]) -> float:
        selected = tuple(selected)
        if len(selected) < 2:
            return 1.0
        pairs = 0
        compatible = 0
        for index, left in enumerate(selected):
            for right in selected[index + 1:]:
                pairs += 1
                compatible += int(not cls._conflicts(left, (right,)))
        return compatible / max(1, pairs)


class GapClassifier:
    def classify(
        self,
        lattice: FormLattice,
        bundle: MeaningBundle | None,
        prior_gaps: Iterable[GapRecord],
        *,
        explicit_teaching: bool = False,
    ) -> tuple[GapRecord, ...]:
        result = list(prior_gaps)
        if bundle is not None and bundle.assessment.incomplete:
            result.append(GapRecord(
                gap_id=semantic_hash("gap", (bundle.bundle_id, "incomplete")),
                kind=GapKind.AMBIGUITY,
                target_ref=bundle.bundle_id,
                reason="selected_bundle_has_partial_coverage",
                evidence_refs=bundle.graph.evidence_refs,
                learnable=False,
                repair_options=("clarify_ambiguous_part",),
            ))
        if explicit_teaching:
            result = [
                GapRecord(
                    gap_id=item.gap_id,
                    kind=item.kind,
                    target_ref=item.target_ref,
                    reason=item.reason,
                    expected_type_refs=item.expected_type_refs,
                    evidence_refs=item.evidence_refs,
                    learnable=item.kind in {GapKind.LEXICAL, GapKind.SCHEMA},
                    repair_options=item.repair_options,
                    confidence=item.confidence,
                )
                for item in result
            ]
        return tuple(_dedupe_gaps(result))


class UnderstandingCoordinator:
    def __init__(
        self, schema_store: SemanticSchemaStore, store: SemanticStore,
        lifecycle: SchemaLifecycleCoordinator | None = None,
    ):
        self.lifecycle = lifecycle or SchemaLifecycleCoordinator(schema_store, store)
        self.activator = SchemaActivator(schema_store, self.lifecycle)
        self.assembler = JointMeaningAssembler(schema_store, store)
        self.selector = MeaningBundleSelector()
        self.gaps = GapClassifier()

    def understand(
        self,
        lattice: FormLattice,
        candidates: Mapping[str, tuple[GroundingCandidate, ...]],
        context: ContextSnapshot,
        *,
        analyzer_fingerprint: str = "",
    ) -> UnderstandingResult:
        activations = self.activator.activate(
            lattice, context_ref=context.context_ref, analyzer_fingerprint=analyzer_fingerprint
        )
        hypotheses, raw_gaps = self.assembler.assemble(lattice, activations, candidates, context)
        bundle = self.selector.select(hypotheses)
        explicit_teaching = any(
            "force:teach" in span.semantic_refs or span.candidate_kind == "teaching_marker"
            for span in lattice.spans
        )
        gaps = self.gaps.classify(
            lattice, bundle, raw_gaps, explicit_teaching=explicit_teaching
        )
        return UnderstandingResult(
            activations=activations,
            hypotheses=hypotheses,
            bundle=bundle,
            gaps=gaps,
            incomplete=bundle is None or bundle.assessment.incomplete,
        )


def _dedupe_gaps(items: Iterable[GapRecord]) -> list[GapRecord]:
    result: dict[tuple[str, str], GapRecord] = {}
    for item in items:
        key = (item.kind.value, item.target_ref)
        existing = result.get(key)
        if existing is None or item.confidence > existing.confidence:
            result[key] = item
    return sorted(result.values(), key=lambda item: (item.kind.value, item.target_ref))
