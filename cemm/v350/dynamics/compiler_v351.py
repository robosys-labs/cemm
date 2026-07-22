"""Compile exact CSIR candidates into a sparse typed activation graph."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ..csir.model import CSIRNodeKind, QualifierKind
from ..runtime_abi import CSIRCandidateSet, artifact_ref
from ..schema.model import semantic_fingerprint
from .model_v351 import (
    ActivationNodeKind, CompetitionGroup, EdgePolarity, HardConstraintMask, HardMaskReason,
    MessageFamily, REQUIRED_MESSAGE_FAMILIES, SemanticActivationNode, TypedActivationPayload,
    TypedMessageEdge,
)
from .parameters_v351 import compile_parameter_set

@dataclass(frozen=True, slots=True)
class _SemanticCandidateClass:
    candidate_ref: str
    graph: Any
    semantic_fingerprint: str
    evidence_refs: tuple[str, ...]
    derivation_refs: tuple[str, ...]
    closure_proof_refs: tuple[str, ...]
    hard_constraint_trace_refs: tuple[str, ...]
    dynamics_parameter_pins: tuple[Any, ...]
    use_authorization_pins: tuple[Any, ...]
    projection_authority_pins: tuple[Any, ...]
    causal_mechanism_pins: tuple[Any, ...]
    policy_adapter_pins: tuple[Any, ...]
    prior_score: float


class TypedActivationGraphCompilerV351:
    """Pure cycle-local compiler. It never resolves floating semantic authority."""

    def compile(
        self,
        *,
        csir_candidates: CSIRCandidateSet,
        semantic_authority_snapshot_v351,
        dynamics_parameters,
        evidence_lattice=None,
        evidence_envelopes=(),
        grounding_candidates=None,
        referent_projections: Mapping[str, Any] | None = None,
        state_space_projections: Mapping[str, Any] | None = None,
    ) -> TypedActivationPayload:
        parameter_set = compile_parameter_set(
            dynamics_parameters,
            authority_snapshot=semantic_authority_snapshot_v351,
        )
        nodes: dict[str, SemanticActivationNode] = {}
        edges: dict[str, TypedMessageEdge] = {}
        masks: dict[str, HardConstraintMask] = {}
        candidate_node_refs: list[tuple[str, str]] = []
        candidate_graphs = []
        candidate_priors = []
        candidate_evidence = []
        candidate_derivations = []
        open_variables: set[str] = set()
        unresolved: set[str] = set(csir_candidates.unresolved_refs)
        family_counts = {family: 0 for family in REQUIRED_MESSAGE_FAMILIES}

        def add_node(item: SemanticActivationNode) -> None:
            previous = nodes.get(item.node_ref)
            if previous is not None and previous != item:
                raise ValueError(f"activation node identity collision:{item.node_ref}")
            nodes[item.node_ref] = item

        def add_edge(
            family: MessageFamily,
            source: str,
            target: str,
            *,
            strength: float = 1.0,
            polarity: EdgePolarity = EdgePolarity.EXCITATORY,
            evidence_refs: Iterable[str] = (),
            authority_pins=(),
            feature_refs: Iterable[str] = (),
        ) -> None:
            if source == target:
                return
            ref = "activation-edge:" + semantic_fingerprint(
                "typed-message-edge-v351",
                (family.value, source, target, polarity.value, tuple(sorted(set(evidence_refs))), tuple(pin.key for pin in authority_pins), tuple(sorted(set(feature_refs)))),
                24,
            )
            item = TypedMessageEdge(
                edge_ref=ref,
                family=family,
                source_node_ref=source,
                target_node_ref=target,
                polarity=polarity,
                strength=float(strength),
                evidence_refs=tuple(sorted(set(evidence_refs))),
                authority_pins=tuple(sorted(set(authority_pins), key=lambda pin: pin.key)),
                feature_refs=tuple(sorted(set(feature_refs))),
            )
            if ref not in edges:
                edges[ref] = item
                family_counts[family] += 1

        # Evidence nodes are explicit bottom-up sources. Shared evidence is one node, so
        # derivations cannot naively double-count the same evidence identity.
        semantic_classes = self._cluster_semantic_candidates(csir_candidates.candidates)
        all_evidence_refs = sorted({ref for candidate in semantic_classes for ref in candidate.evidence_refs})
        evidence_lineages = self._evidence_lineages(evidence_envelopes, all_evidence_refs)
        for evidence_ref in all_evidence_refs:
            node_ref = "activation-node:evidence:" + semantic_fingerprint("activation-evidence", evidence_ref, 20)
            add_node(SemanticActivationNode(
                node_ref=node_ref,
                node_kind=ActivationNodeKind.EVIDENCE,
                semantic_class_ref="evidence-only:not-semantic-identity",
                source_ref=evidence_ref,
                initial_activation=1.0,
                current_activation=1.0,
                evidence_refs=(evidence_ref,),
                lineage_refs=evidence_lineages[evidence_ref],
            ))

        for candidate in semantic_classes:
            class_node = "activation-node:class:" + candidate.semantic_fingerprint
            prior = self._bounded_prior(candidate.prior_score)
            add_node(SemanticActivationNode(
                node_ref=class_node,
                node_kind=ActivationNodeKind.SEMANTIC_CLASS,
                semantic_class_ref=candidate.semantic_fingerprint,
                source_ref=candidate.candidate_ref,
                initial_activation=prior,
                current_activation=prior,
                evidence_refs=tuple(sorted(candidate.evidence_refs)),
                lineage_refs=tuple(sorted(candidate.derivation_refs)),
                exact_authority_pins=tuple(sorted({
                    *candidate.dynamics_parameter_pins,
                    *candidate.use_authorization_pins,
                    *candidate.projection_authority_pins,
                    *candidate.causal_mechanism_pins,
                    *candidate.policy_adapter_pins,
                }, key=lambda pin: pin.key)),
                unresolved_refs=candidate.graph.unresolved_refs,
            ))
            candidate_node_refs.append((candidate.candidate_ref, class_node))
            candidate_graphs.append((candidate.candidate_ref, candidate.graph))
            candidate_priors.append((candidate.candidate_ref, float(candidate.prior_score)))
            candidate_evidence.append((
                candidate.candidate_ref,
                tuple(sorted(set(candidate.evidence_refs))),
            ))
            candidate_derivations.append((
                candidate.candidate_ref,
                tuple(sorted(set(candidate.derivation_refs))),
            ))
            unresolved.update(candidate.graph.unresolved_refs)
            open_variables.update(item.variable_ref for item in candidate.graph.variables)

            masks[class_node] = HardConstraintMask(
                mask_ref="hard-mask:" + semantic_fingerprint(
                    "hard-mask-pass-v351",
                    (candidate.candidate_ref, candidate.semantic_fingerprint, candidate.hard_constraint_trace_refs),
                    24,
                ),
                target_node_ref=class_node,
                allowed=True,
                reason=HardMaskReason.HARD_CONSTRAINT,
                proof_refs=tuple(sorted(set(candidate.hard_constraint_trace_refs))) or (
                    "proof:kernel-validated-csir-candidate:" + candidate.candidate_ref,
                ),
                authority_pins=tuple(sorted(candidate.dynamics_parameter_pins, key=lambda pin: pin.key)),
            )

            graph = candidate.graph
            local_to_node: dict[tuple[CSIRNodeKind, str], str] = {}

            for term in graph.terms:
                node_ref = self._structure_node_ref(candidate.candidate_ref, "term", term.term_ref)
                local_to_node[(CSIRNodeKind.TERM, term.term_ref)] = node_ref
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.TERM,
                    semantic_class_ref=candidate.semantic_fingerprint,
                    source_ref=term.term_ref,
                    initial_activation=prior,
                    current_activation=prior,
                    exact_authority_pins=tuple(sorted((*term.type_pins, *term.authority_pins), key=lambda pin: pin.key)),
                    feature_refs=tuple(sorted(f"{key}={value}" for key, value in term.features)),
                ))
                add_edge(MessageFamily.CONSTRUCTION, class_node, node_ref, evidence_refs=candidate.evidence_refs)
                add_edge(MessageFamily.CONSTRUCTION, node_ref, class_node, evidence_refs=candidate.evidence_refs)
                for pin in term.type_pins:
                    add_edge(MessageFamily.TYPE, class_node, node_ref, authority_pins=(pin,), feature_refs=(pin.ref,))
                if term.identity_ref:
                    add_edge(MessageFamily.IDENTITY, class_node, node_ref, feature_refs=(term.identity_ref,))

            for variable in graph.variables:
                node_ref = self._structure_node_ref(candidate.candidate_ref, "variable", variable.variable_ref)
                local_to_node[(CSIRNodeKind.VARIABLE, variable.variable_ref)] = node_ref
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.VARIABLE,
                    semantic_class_ref=candidate.semantic_fingerprint,
                    source_ref=variable.variable_ref,
                    initial_activation=prior,
                    current_activation=prior,
                    exact_authority_pins=tuple(sorted(variable.required_type_pins, key=lambda pin: pin.key)),
                    feature_refs=(f"scope:{variable.scope_ref}", f"purpose:{variable.open_purpose}"),
                    unresolved_refs=(variable.variable_ref,),
                ))
                add_edge(MessageFamily.CONSTRUCTION, class_node, node_ref, evidence_refs=candidate.evidence_refs)
                for pin in variable.required_type_pins:
                    add_edge(MessageFamily.TYPE, class_node, node_ref, authority_pins=(pin,), feature_refs=(pin.ref,))

            for application in graph.applications:
                node_ref = self._structure_node_ref(candidate.candidate_ref, "application", application.application_ref)
                local_to_node[(CSIRNodeKind.APPLICATION, application.application_ref)] = node_ref
                pins = (application.predicate_pin, *application.operational_profile_pins)
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.APPLICATION,
                    semantic_class_ref=candidate.semantic_fingerprint,
                    source_ref=application.application_ref,
                    initial_activation=prior,
                    current_activation=prior,
                    exact_authority_pins=tuple(sorted(pins, key=lambda pin: pin.key)),
                    feature_refs=(application.predicate_pin.ref,),
                ))
                add_edge(MessageFamily.CONSTRUCTION, class_node, node_ref, evidence_refs=candidate.evidence_refs, authority_pins=pins)
                add_edge(MessageFamily.CONSTRUCTION, node_ref, class_node, evidence_refs=candidate.evidence_refs, authority_pins=pins)

            for coordination in graph.coordinations:
                node_ref = self._structure_node_ref(candidate.candidate_ref, "coordination", coordination.coordination_ref)
                local_to_node[(CSIRNodeKind.COORDINATION, coordination.coordination_ref)] = node_ref
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.COORDINATION,
                    semantic_class_ref=candidate.semantic_fingerprint,
                    source_ref=coordination.coordination_ref,
                    initial_activation=prior,
                    current_activation=prior,
                    exact_authority_pins=(coordination.coordination_kind_pin,),
                ))
                add_edge(MessageFamily.CONSTRUCTION, class_node, node_ref, authority_pins=(coordination.coordination_kind_pin,))
                for member in coordination.members:
                    member_ref = local_to_node.get((member.kind, member.ref))
                    if member_ref:
                        add_edge(MessageFamily.CONSTRUCTION, node_ref, member_ref, authority_pins=(coordination.coordination_kind_pin,))

            # Bindings are factors, not semantic filler identities. They connect exact
            # application ports to grounded/variable fillers through PORT_ROLE messages.
            for binding in graph.bindings:
                node_ref = self._structure_node_ref(candidate.candidate_ref, "binding", binding.binding_ref)
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.BINDING,
                    semantic_class_ref=candidate.semantic_fingerprint,
                    source_ref=binding.binding_ref,
                    initial_activation=prior,
                    current_activation=prior,
                    exact_authority_pins=(binding.port_pin,),
                    feature_refs=(binding.port_pin.ref,),
                ))
                app_ref = local_to_node.get((CSIRNodeKind.APPLICATION, binding.application_ref))
                if app_ref:
                    add_edge(MessageFamily.PORT_ROLE, app_ref, node_ref, authority_pins=(binding.port_pin,))
                    add_edge(MessageFamily.PORT_ROLE, node_ref, app_ref, authority_pins=(binding.port_pin,))
                for filler in binding.fillers:
                    filler_ref = local_to_node.get((filler.kind, filler.ref))
                    if filler_ref:
                        add_edge(MessageFamily.PORT_ROLE, node_ref, filler_ref, authority_pins=(binding.port_pin,))
                        add_edge(MessageFamily.PORT_ROLE, filler_ref, node_ref, authority_pins=(binding.port_pin,))

            for qualifier in graph.qualifiers:
                node_ref = self._structure_node_ref(candidate.candidate_ref, "qualifier", qualifier.qualifier_ref)
                pins = () if qualifier.value_pin is None else (qualifier.value_pin,)
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.QUALIFIER,
                    semantic_class_ref=candidate.semantic_fingerprint,
                    source_ref=qualifier.qualifier_ref,
                    initial_activation=prior,
                    current_activation=prior,
                    exact_authority_pins=pins,
                    feature_refs=(qualifier.qualifier_kind.value,),
                ))
                target_ref = local_to_node.get((qualifier.target.kind, qualifier.target.ref))
                family = self._qualifier_family(qualifier.qualifier_kind)
                if target_ref:
                    add_edge(family, node_ref, target_ref, authority_pins=pins, feature_refs=(qualifier.qualifier_kind.value,))
                    add_edge(family, target_ref, node_ref, authority_pins=pins, feature_refs=(qualifier.qualifier_kind.value,))
                if qualifier.value_ref is not None:
                    value_ref = local_to_node.get((qualifier.value_ref.kind, qualifier.value_ref.ref))
                    if value_ref:
                        add_edge(family, node_ref, value_ref, authority_pins=pins, feature_refs=(qualifier.qualifier_kind.value,))

            for embedding in graph.scope_embeddings:
                node_ref = self._structure_node_ref(candidate.candidate_ref, "scope", embedding.embedding_ref)
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.SCOPE,
                    semantic_class_ref=candidate.semantic_fingerprint,
                    source_ref=embedding.embedding_ref,
                    initial_activation=prior,
                    current_activation=prior,
                    exact_authority_pins=(embedding.scope_kind_pin,),
                    feature_refs=(f"order:{embedding.order}",),
                ))
                operator_ref = local_to_node.get((embedding.operator.kind, embedding.operator.ref))
                scoped_ref = local_to_node.get((embedding.scoped.kind, embedding.scoped.ref))
                if operator_ref:
                    add_edge(MessageFamily.SCOPE, operator_ref, node_ref, authority_pins=(embedding.scope_kind_pin,))
                if scoped_ref:
                    add_edge(MessageFamily.SCOPE, node_ref, scoped_ref, authority_pins=(embedding.scope_kind_pin,))

            # Bottom-up lexical evidence is candidate-level unless a more precise
            # evidence-to-node alignment is explicitly available. This prevents a raw
            # word string from becoming semantic control flow.
            candidate_clusters = {}
            for evidence_ref in candidate.evidence_refs:
                cluster = evidence_lineages.get(evidence_ref, ("lineage:unknown",))
                candidate_clusters.setdefault(cluster, []).append(evidence_ref)
            cluster_cap = parameter_set.value("lineage_cluster_cap")
            if not 0.0 < cluster_cap <= 1.0:
                raise ValueError("lineage_cluster_cap must be in (0,1]")
            for cluster in sorted(candidate_clusters):
                refs = tuple(sorted(candidate_clusters[cluster]))
                # CEMM_CORE_MATHS §9: shared-lineage evidence is clustered and discounted,
                # not naively summed as independent support. The reviewed deterministic
                # baseline caps each exact lineage cluster's total lexical contribution.
                weight = cluster_cap / max(1, len(refs))
                for evidence_ref in refs:
                    evidence_node = "activation-node:evidence:" + semantic_fingerprint("activation-evidence", evidence_ref, 20)
                    if evidence_node in nodes:
                        add_edge(
                            MessageFamily.LEXICAL, evidence_node, class_node, strength=weight,
                            evidence_refs=(evidence_ref,), feature_refs=cluster,
                        )

            # Causal messages exist only when exact mechanism authority explicitly
            # matches an application predicate. Temporal adjacency/coactivation is never
            # converted into causal authority.
            predicate_keys = {app.predicate_pin.key for app in graph.applications}
            for mechanism in semantic_authority_snapshot_v351.causal_mechanisms:
                if mechanism.trigger_definition_pin.key not in predicate_keys:
                    continue
                for application in graph.applications:
                    if application.predicate_pin.key != mechanism.trigger_definition_pin.key:
                        continue
                    app_ref = local_to_node.get((CSIRNodeKind.APPLICATION, application.application_ref))
                    if app_ref:
                        add_edge(
                            MessageFamily.CAUSAL_EXPECTATION,
                            app_ref,
                            class_node,
                            authority_pins=(mechanism.mechanism_pin, mechanism.trigger_definition_pin),
                            feature_refs=tuple(pin.ref for pin in mechanism.transition_template_pins),
                        )

            self._add_state_projection_edges(
                candidate, class_node, nodes, add_node, add_edge,
                referent_projections or {}, state_space_projections or {},
            )
            self._add_grounding_edges(candidate, class_node, nodes, add_node, add_edge, grounding_candidates)
            self._add_multimodal_edges(candidate, class_node, nodes, add_node, add_edge, evidence_lattice)

        competition_groups = ()
        if len(candidate_node_refs) > 1:
            competition_groups = (CompetitionGroup(
                group_ref="competition-group:" + semantic_fingerprint(
                    "candidate-set-competition-v351",
                    (csir_candidates.candidate_set_ref, tuple(ref for ref, _ in candidate_node_refs)),
                    24,
                ),
                member_node_refs=tuple(node_ref for _, node_ref in candidate_node_refs),
                basis_refs=(csir_candidates.candidate_set_ref,),
            ),)

        payload_ref = artifact_ref(
            "typed-activation-payload",
            csir_candidates.candidate_set_ref,
            parameter_set.parameter_set_ref,
            tuple(item.semantic_fingerprint for item in semantic_classes),
        )
        return TypedActivationPayload(
            payload_ref=payload_ref,
            nodes=tuple(nodes[key] for key in sorted(nodes)),
            edges=tuple(edges[key] for key in sorted(edges)),
            masks=tuple(masks[key] for key in sorted(masks)),
            competition_groups=competition_groups,
            parameter_set=parameter_set,
            candidate_node_refs=tuple(candidate_node_refs),
            candidate_graphs=tuple(candidate_graphs),
            candidate_prior_scores=tuple(candidate_priors),
            candidate_evidence_refs=tuple(candidate_evidence),
            candidate_derivation_refs=tuple(candidate_derivations),
            open_variable_refs=tuple(sorted(open_variables)),
            unresolved_refs=tuple(sorted(unresolved)),
            family_edge_counts=tuple((family, family_counts[family]) for family in REQUIRED_MESSAGE_FAMILIES),
            proof_refs=tuple(sorted(set((
                *csir_candidates.closure_proof_refs,
                *csir_candidates.hard_constraint_trace_refs,
                "proof:typed-activation-compiler-v351",
                "proof:semantic-class-clustering-before-posterior-v351",
            )))),
        )

    @staticmethod
    def _cluster_semantic_candidates(candidates) -> tuple[_SemanticCandidateClass, ...]:
        """Collapse derivations into semantic classes before dynamic competition.

        CEMM_CORE_MATHS requires posterior mass over semantic classes, not over parse or
        proof derivations.  Repeated derivations therefore contribute lineage/evidence but
        never receive independent competition slots that would double-count the same meaning.
        The class prior uses the strongest derivational prior rather than summation.
        """
        grouped: dict[str, list] = {}
        for candidate in candidates:
            grouped.setdefault(candidate.semantic_fingerprint, []).append(candidate)
        result = []
        for semantic_ref in sorted(grouped):
            group = tuple(sorted(grouped[semantic_ref], key=lambda item: (item.exact_fingerprint, item.candidate_ref)))
            representative = group[0]
            def pins(name):
                values = {pin.key: pin for item in group for pin in getattr(item, name)}
                return tuple(values[key] for key in sorted(values))
            result.append(_SemanticCandidateClass(
                candidate_ref="semantic-class:" + semantic_ref,
                graph=representative.graph,
                semantic_fingerprint=semantic_ref,
                evidence_refs=tuple(sorted({ref for item in group for ref in item.evidence_refs})),
                derivation_refs=tuple(item.candidate_ref for item in group),
                closure_proof_refs=tuple(sorted({ref for item in group for ref in item.closure_proof_refs})),
                hard_constraint_trace_refs=tuple(sorted({ref for item in group for ref in item.hard_constraint_trace_refs})),
                dynamics_parameter_pins=pins("dynamics_parameter_pins"),
                use_authorization_pins=pins("use_authorization_pins"),
                projection_authority_pins=pins("projection_authority_pins"),
                causal_mechanism_pins=pins("causal_mechanism_pins"),
                policy_adapter_pins=pins("policy_adapter_pins"),
                prior_score=max(float(item.prior_score) for item in group),
            ))
        return tuple(result)

    @staticmethod
    def _bounded_prior(value: float) -> float:
        # prior_score is evidence ranking, not authority. Mapping only initializes
        # dynamic mass and cannot unmask an incompatible candidate.
        if value <= -20.0:
            return 0.0
        if value >= 20.0:
            return 1.0
        import math
        return 1.0 / (1.0 + math.exp(-float(value)))

    @staticmethod
    def _evidence_lineages(evidence_envelopes, evidence_refs):
        """Resolve exact evidence lineage clusters conservatively.

        Missing lineage metadata is *not* treated as independent evidence. All such signals
        share one unknown-lineage cluster so absence of provenance cannot inflate support.
        """
        by_ref = {}
        for envelope in tuple(evidence_envelopes or ()):
            ref = str(getattr(envelope, "evidence_ref", "") or "")
            if not ref:
                continue
            lineages = tuple(sorted(set(str(item) for item in tuple(getattr(envelope, "lineage_refs", ()) or ()) if str(item))))
            source_ref = str(getattr(envelope, "source_ref", "") or "")
            if not lineages and source_ref:
                lineages = ("source-lineage:" + source_ref,)
            by_ref[ref] = lineages or ("lineage:unknown",)
        return {ref: by_ref.get(ref, ("lineage:unknown",)) for ref in evidence_refs}

    @staticmethod
    def _structure_node_ref(candidate_ref: str, kind: str, local_ref: str) -> str:
        return "activation-node:" + semantic_fingerprint(
            "activation-structure-node-v351", (candidate_ref, kind, local_ref), 28
        )

    @staticmethod
    def _qualifier_family(kind: QualifierKind) -> MessageFamily:
        if kind == QualifierKind.CONTEXT or kind == QualifierKind.PERMISSION or kind == QualifierKind.SOURCE:
            return MessageFamily.CONTEXT
        if kind == QualifierKind.TIME:
            return MessageFamily.TIME_ASPECT
        if kind == QualifierKind.MODALITY or kind == QualifierKind.POLARITY:
            return MessageFamily.SCOPE
        if kind == QualifierKind.EVIDENCE:
            return MessageFamily.LEXICAL
        return MessageFamily.CONTEXT

    @staticmethod
    def _add_state_projection_edges(candidate, class_node, nodes, add_node, add_edge, referent_projections, state_space_projections):
        identities = {term.identity_ref for term in candidate.graph.terms if term.identity_ref}
        for referent_ref in sorted(identities.intersection(referent_projections)):
            state_items = tuple(state_space_projections.get(referent_ref, ()) or ())
            for index, item in enumerate(state_items):
                source_ref = str(getattr(item, "dimension_ref", None) or getattr(item, "schema_ref", None) or f"{referent_ref}:{index}")
                node_ref = "activation-node:state:" + semantic_fingerprint(
                    "activation-state-projection-v351", (candidate.candidate_ref, referent_ref, source_ref), 24
                )
                if node_ref not in nodes:
                    add_node(SemanticActivationNode(
                        node_ref=node_ref,
                        node_kind=ActivationNodeKind.STATE_PROJECTION,
                        semantic_class_ref=candidate.semantic_fingerprint,
                        source_ref=source_ref,
                        initial_activation=0.5,
                        current_activation=0.5,
                        evidence_refs=tuple(getattr(item, "evidence_refs", ()) or ()),
                        feature_refs=(referent_ref,),
                    ))
                add_edge(
                    MessageFamily.STATE, node_ref, class_node,
                    evidence_refs=tuple(getattr(item, "evidence_refs", ()) or ()),
                    feature_refs=(referent_ref, source_ref),
                )

    @staticmethod
    def _add_grounding_edges(candidate, class_node, nodes, add_node, add_edge, grounding_candidates):
        if grounding_candidates is None:
            return
        preparation = getattr(grounding_candidates, "preparation", None)
        values = tuple(getattr(preparation, "candidates", ()) or ())
        candidate_identities = {term.identity_ref for term in candidate.graph.terms if term.identity_ref}
        for item in values:
            target_ref = str(getattr(item, "target_ref", "") or "")
            if not target_ref or target_ref not in candidate_identities:
                continue
            node_ref = "activation-node:referent:" + semantic_fingerprint(
                "activation-grounding-referent-v351", (candidate.candidate_ref, target_ref), 24
            )
            evidence = tuple(getattr(item, "evidence_refs", ()) or ())
            if node_ref not in nodes:
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.REFERENT,
                    semantic_class_ref=candidate.semantic_fingerprint,
                    source_ref=target_ref,
                    initial_activation=0.5,
                    current_activation=0.5,
                    evidence_refs=evidence,
                    feature_refs=tuple(sorted(set(getattr(item, "type_refs", ()) or ()))),
                ))
            add_edge(MessageFamily.IDENTITY, node_ref, class_node, evidence_refs=evidence, feature_refs=(target_ref,))
            factor_values = tuple(getattr(item, "factors", ()) or ())
            if any("discourse" in str(getattr(factor, "kind", "")).casefold() for factor in factor_values):
                add_edge(MessageFamily.DISCOURSE, node_ref, class_node, evidence_refs=evidence, feature_refs=(target_ref,))

    @staticmethod
    def _add_multimodal_edges(candidate, class_node, nodes, add_node, add_edge, evidence_lattice):
        if evidence_lattice is None:
            return
        for item in tuple(getattr(evidence_lattice, "structured_observations", ()) or ()):
            source_ref = str(getattr(item, "track_ref", None) or getattr(item, "observation_ref", None) or repr(item))
            node_ref = "activation-node:multimodal:" + semantic_fingerprint(
                "activation-multimodal-v351", source_ref, 24
            )
            evidence = tuple(getattr(item, "evidence_refs", ()) or ())
            if node_ref not in nodes:
                add_node(SemanticActivationNode(
                    node_ref=node_ref,
                    node_kind=ActivationNodeKind.MULTIMODAL_TRACK,
                    semantic_class_ref="multimodal-evidence:not-semantic-identity",
                    source_ref=source_ref,
                    initial_activation=1.0,
                    current_activation=1.0,
                    evidence_refs=evidence,
                    lineage_refs=evidence or (source_ref,),
                ))
            # Only align when the observation itself explicitly names semantic/referent
            # targets that occur in the candidate. No proximity-based semantic identity.
            target_refs = set(tuple(getattr(item, "target_refs", ()) or ()))
            identities = {term.identity_ref for term in candidate.graph.terms if term.identity_ref}
            if target_refs.intersection(identities):
                add_edge(MessageFamily.MULTIMODAL, node_ref, class_node, evidence_refs=evidence, feature_refs=tuple(sorted(target_refs.intersection(identities))))


__all__ = ["TypedActivationGraphCompilerV351"]
