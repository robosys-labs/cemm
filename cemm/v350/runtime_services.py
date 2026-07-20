"""Canonical non-semantic runtime service composition for CEMM v3.5.

Only mechanical capabilities live here. Semantic policy remains in reviewed data
or an explicitly configured/signed provider. Public runtime construction uses
these descriptors so the release manifest can fingerprint the exact service
implementation rather than accepting arbitrary injected objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import inspect
from pathlib import Path
from typing import Any, Mapping

from .composition.coordinator import MeaningComposer
from .grounding.coordinator import JointGrounder
from .grounding.model import DiscourseAnchor
from .knowledge_factors import ReferentKnowledgeFactorBinder
from .language.analyzer import FormLatticeAnalyzer
from .permissions import PermissionScopeEvaluator
from .schema.model import semantic_fingerprint
from .facets.projector import ReferentKnowledgeProjector
from .uol.model import UOLGraph


@dataclass(frozen=True, slots=True)
class RuntimeServiceDescriptor:
    service_kind: str
    implementation_ref: str
    implementation_revision: str
    class_path: str
    source_sha256: str
    config_fingerprint: str = ""

    def __post_init__(self) -> None:
        for value, label in (
            (self.service_kind, "service kind"),
            (self.implementation_ref, "implementation ref"),
            (self.implementation_revision, "implementation revision"),
            (self.class_path, "service class path"),
            (self.source_sha256, "service source sha256"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be non-empty")
        if len(self.source_sha256) != 64:
            raise ValueError("service source sha256 must be 64 hex characters")


class SystemClock:
    clock_ref = "clock:system-utc"
    clock_revision = "1"

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


class CanonicalSemanticAnalyzer:
    """Independent target-language analysis used only for semantic round-trip.

    The analyzer receives no expected Response UOL. It reconstructs meaning through
    the reviewed understanding path and returns recovered UOL for kernel-side
    equivalence comparison.
    """

    analyzer_ref = "semantic-analyzer:canonical-v350"
    analyzer_revision = "2"

    def __init__(self, store) -> None:
        self.store = store

    def recover_graph(
        self,
        surface: str,
        language_tag: str,
        *,
        context_ref: str,
        speaker_ref: str,
        addressee_refs: tuple[str, ...],
        permission_ref: str,
    ) -> tuple[UOLGraph, tuple[str, ...]]:
        if not surface:
            raise ValueError("round-trip analyzer cannot analyze empty surface")
        source_ref = "source:roundtrip:" + semantic_fingerprint(
            "roundtrip-source",
            (surface, language_tag, context_ref, speaker_ref, addressee_refs),
            24,
        )
        anchor_evidence = "evidence:roundtrip-context:" + semantic_fingerprint(
            "roundtrip-context",
            (context_ref, speaker_ref, addressee_refs, permission_ref),
            24,
        )
        anchors = [
            DiscourseAnchor(
                anchor_ref="anchor:roundtrip:speaker:" + semantic_fingerprint(
                    "roundtrip-speaker-anchor", (speaker_ref, context_ref), 16
                ),
                referent_ref=speaker_ref,
                context_ref=context_ref,
                salience=1.0,
                turn_index=0,
                role_refs=("speaker",),
                evidence_refs=(anchor_evidence,),
            )
        ]
        anchors.extend(
            DiscourseAnchor(
                anchor_ref="anchor:roundtrip:addressee:" + semantic_fingerprint(
                    "roundtrip-addressee-anchor", (ref, context_ref), 16
                ),
                referent_ref=ref,
                context_ref=context_ref,
                salience=0.95,
                turn_index=0,
                role_refs=("addressee",),
                evidence_refs=(anchor_evidence,),
            )
            for ref in addressee_refs
        )

        with self.store.snapshot() as snapshot:
            language_registry = self.store.repositories.language.registry(snapshot=snapshot)
            form_analyzer = FormLatticeAnalyzer(language_registry)
            lattice = form_analyzer.analyze(
                surface,
                source_ref=source_ref,
                language_hints=(language_tag,),
            )
            grounder = JointGrounder(self.store, form_analyzer)
            prepared = grounder.prepare_lattice(
                lattice,
                context_ref=context_ref,
                discourse_anchors=tuple(anchors),
                multimodal_tracks=(),
                system_outputs=(),
                constraints=(),
                snapshot=snapshot,
            )
            grounding = grounder.solve_prepared(prepared)
            projections = {}
            projector = ReferentKnowledgeProjector(self.store)
            for target_ref in sorted({item.target_ref for item in prepared.candidates}):
                if self.store.get_record(
                    self.store.repositories.referents.record_kind,
                    target_ref,
                    snapshot=snapshot,
                ) is not None:
                    projections[target_ref] = projector.project(
                        target_ref,
                        context_ref=context_ref,
                        at_time=None,
                        snapshot=snapshot,
                    )
            composer = MeaningComposer(self.store)
            factor_graph = composer.build_factor_graph(
                lattice,
                grounding,
                context_ref=context_ref,
                snapshot=snapshot,
            )
            factor_graph = ReferentKnowledgeFactorBinder(self.store).bind(
                factor_graph,
                lattice=lattice,
                projections=projections,
                snapshot=snapshot,
            )
            solved = composer.solve_factor_graph(factor_graph)
            result = composer.select_bundle(
                factor_graph,
                solved,
                lattice,
                grounding,
                context_ref=context_ref,
                snapshot=snapshot,
            )

        graph = result.bundle.uol_graph
        if graph is None:
            raise ValueError("round-trip analyzer produced no semantic graph")
        if graph.unresolved_refs or result.bundle.partial_understanding.unresolved_refs:
            raise ValueError("round-trip analyzer retained unresolved semantic meaning")
        proof_refs = tuple(
            sorted(
                set(
                    (
                        lattice.lattice_ref,
                        grounding.grounding_ref,
                        factor_graph.graph_ref,
                        *result.bundle.evidence_refs,
                        anchor_evidence,
                    )
                )
            )
        )
        if not proof_refs:
            raise ValueError("round-trip analysis requires proof/evidence lineage")
        return graph, proof_refs


class InProcessTextChannelAdapter:
    """Mechanical text-return boundary.

    Returning bytes to the API caller proves that content left the semantic runtime,
    but it does not prove recipient receipt or semantic acceptance.
    """

    adapter_ref = "channel-adapter:in-process-text"
    adapter_revision = 1

    def submit(
        self,
        *,
        surface: str,
        audience_refs: tuple[str, ...],
        idempotency_key: str | None,
        context: Mapping[str, Any],
    ):
        from .output.executor import ChannelObservation
        from .output.gate import surface_sha256

        evidence_ref = "evidence:channel-submit:" + semantic_fingerprint(
            "channel-submit",
            (
                surface_sha256(surface),
                audience_refs,
                idempotency_key,
                tuple(sorted((str(k), str(v)) for k, v in context.items())),
            ),
            24,
        )
        return ChannelObservation(
            accepted=True,
            delivered=False,
            delivery_known=False,
            content_left_system=True,
            evidence_refs=(evidence_ref,),
            observed_surface_sha256=surface_sha256(surface),
            request_evidence_refs=(evidence_ref,),
            metadata={"boundary": "in_process_return", "recipient_receipt_proven": False},
        )

    def recover(
        self,
        *,
        external_correlation_refs: tuple[str, ...],
        idempotency_key: str | None,
        context: Mapping[str, Any],
    ):
        raise ValueError("in-process text adapter has no reviewed recovery query")


class StructuralPolicySafetyEvaluator:
    evaluator_ref = "emission-evaluator:structural-policy-safety"
    evaluator_revision = "2"

    def evaluate(self, *, gate_ref: str, store, substrate: Mapping[str, object]):
        from .output.gate import GateEvaluation, pin
        from .storage.model import RecordKind

        response = substrate["response"]
        candidate = substrate["candidate"]
        checked = [
            pin(RecordKind.RESPONSE_UOL, response),
            pin(RecordKind.SURFACE_CANDIDATE, candidate),
        ]
        failures = []
        if response.unresolved_frontier_refs or response.graph.unresolved_refs:
            failures.append("response_retains_unresolved_meaning")
        for source_pin in response.source_pins:
            stored = store.get_record(
                source_pin.record_kind, source_pin.record_ref, source_pin.revision
            )
            if (
                stored is None
                or stored.record_fingerprint != source_pin.record_fingerprint
                or store.is_invalidated(
                    source_pin.record_kind, source_pin.record_ref, source_pin.revision
                )
            ):
                failures.append(f"stale_or_invalidated_source:{source_pin.record_ref}")
            else:
                checked.append(source_pin)
        return GateEvaluation(
            passed=not failures,
            checked_pins=tuple(checked),
            reason_refs=tuple(sorted(set(failures))),
            evaluator_ref=self.evaluator_ref,
            evaluator_revision=self.evaluator_revision,
        )


class QualificationPreservedEvaluator:
    evaluator_ref = "emission-evaluator:qualification-preserved"
    evaluator_revision = "2"

    def evaluate(self, *, gate_ref: str, store, substrate: Mapping[str, object]):
        from .output.gate import GateEvaluation, pin
        from .storage.model import RecordKind

        response = substrate["response"]
        roundtrip = substrate["roundtrip"]
        checked = [
            pin(RecordKind.RESPONSE_UOL, response),
            pin(RecordKind.SEMANTIC_ROUNDTRIP, roundtrip),
        ]
        failures = []
        if roundtrip.additions or roundtrip.losses or roundtrip.drift_refs:
            failures.append("roundtrip_reports_semantic_drift")
        for proof_ref in response.transformation_proof_refs:
            proof = store.get_record(RecordKind.RESPONSE_TRANSFORMATION_PROOF, proof_ref)
            if proof is None or store.is_invalidated(
                RecordKind.RESPONSE_TRANSFORMATION_PROOF,
                proof_ref,
                1 if proof is None else proof.revision,
            ):
                failures.append(f"missing_or_invalidated_response_proof:{proof_ref}")
                continue
            checked.append(
                pin(RecordKind.RESPONSE_TRANSFORMATION_PROOF, proof.payload)
            )
            rule = store.get_record(
                proof.payload.rule_pin.record_kind,
                proof.payload.rule_pin.record_ref,
                proof.payload.rule_pin.revision,
            )
            if rule is None or rule.record_fingerprint != proof.payload.rule_pin.record_fingerprint:
                failures.append(f"stale_transform_rule:{proof.payload.rule_pin.record_ref}")
                continue
            mandatory = tuple(getattr(rule.payload, "mandatory_qualification_refs", ()))
            if mandatory:
                # Planner must resolve mandatory qualifications before a response can
                # be committed. A residual requirement here is a hard emission block.
                failures.extend(
                    f"unresolved_mandatory_qualification:{ref}" for ref in mandatory
                )
        return GateEvaluation(
            passed=not failures,
            checked_pins=tuple(checked),
            reason_refs=tuple(sorted(set(failures))),
            evaluator_ref=self.evaluator_ref,
            evaluator_revision=self.evaluator_revision,
        )


def canonical_service_descriptors() -> tuple[RuntimeServiceDescriptor, ...]:
    classes = (
        ("clock", SystemClock.clock_ref, SystemClock.clock_revision, SystemClock),
        (
            "semantic_analyzer",
            CanonicalSemanticAnalyzer.analyzer_ref,
            CanonicalSemanticAnalyzer.analyzer_revision,
            CanonicalSemanticAnalyzer,
        ),
        (
            "channel_adapter",
            InProcessTextChannelAdapter.adapter_ref,
            str(InProcessTextChannelAdapter.adapter_revision),
            InProcessTextChannelAdapter,
        ),
        (
            "emission_gate_evaluator",
            StructuralPolicySafetyEvaluator.evaluator_ref,
            StructuralPolicySafetyEvaluator.evaluator_revision,
            StructuralPolicySafetyEvaluator,
        ),
        (
            "emission_gate_evaluator",
            QualificationPreservedEvaluator.evaluator_ref,
            QualificationPreservedEvaluator.evaluator_revision,
            QualificationPreservedEvaluator,
        ),
    )
    result = []
    for service_kind, ref, revision, cls in classes:
        source = inspect.getsourcefile(cls)
        if not source or not Path(source).is_file():
            raise RuntimeError(f"cannot fingerprint runtime service implementation: {cls}")
        result.append(
            RuntimeServiceDescriptor(
                service_kind=service_kind,
                implementation_ref=ref,
                implementation_revision=str(revision),
                class_path=f"{cls.__module__}:{cls.__name__}",
                source_sha256=_sha256(Path(source)),
            )
        )
    return tuple(result)


def build_canonical_runtime_services(store):
    """Construct the reviewed mechanical service set.

    No epistemic policy provider, operation adapter, or generic inference authority
    is invented here. Those remain absent until exact reviewed capability data is
    supplied and signed by the runtime manifest.
    """
    from .runtime import RuntimeServices

    return RuntimeServices(
        syntax_adapters=None,
        observation_analyzers={},
        operation_gate_evaluators={},
        operation_adapters={},
        semantic_analyzer=CanonicalSemanticAnalyzer(store),
        emission_gate_evaluators={
            "policy_safety": StructuralPolicySafetyEvaluator(),
            "qualification_preserved": QualificationPreservedEvaluator(),
        },
        channel_adapters={
            InProcessTextChannelAdapter.adapter_ref: InProcessTextChannelAdapter()
        },
        speaker_ref="referent:self",
        # Commitment kind is semantic policy/data, never invented by the mechanical service root.
        output_commitment_kind_ref=None,
        permission_evaluator=PermissionScopeEvaluator(),
        clock=SystemClock(),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
