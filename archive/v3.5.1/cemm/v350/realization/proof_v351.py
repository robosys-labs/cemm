"""Exact, CSIR-native proof-carrying realization for CEMM v3.5.1 Phase 12."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Any, Iterable, Mapping

from ..csir.authority_v351 import AuthoritySnapshotV351, MissingExactDependency
from ..csir.canonical_v351 import exact_fingerprint, semantic_fingerprint
from ..csir.model import CSIRGraph, ExactAuthorityPin
from ..schema.model import semantic_fingerprint as runtime_fingerprint


class PreservationDecision(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class ExactRealizationTransformStep:
    step_ref: str
    transform_kind: str
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    rule_pins: tuple[ExactAuthorityPin, ...]
    lexical_pins: tuple[ExactAuthorityPin, ...]
    morphology_pins: tuple[ExactAuthorityPin, ...]
    linearization_pins: tuple[ExactAuthorityPin, ...]
    coverage_refs: tuple[str, ...]
    preserved_qualification_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.step_ref or not self.transform_kind or not self.input_refs or not self.output_refs:
            raise ValueError("exact realization transform step requires identity, kind, inputs and outputs")
        for pins, label in (
            (self.rule_pins, "rule"), (self.lexical_pins, "lexical"),
            (self.morphology_pins, "morphology"), (self.linearization_pins, "linearization"),
        ):
            if not pins:
                raise ValueError(f"deterministic realization step requires exact {label} pin")
            _unique(tuple(pin.key for pin in pins), f"realization {label} pins")
        for values, label in (
            (self.input_refs, "inputs"), (self.output_refs, "outputs"),
            (self.coverage_refs, "coverage"),
            (self.preserved_qualification_refs, "preserved qualifications"),
        ):
            _unique(values, f"realization step {label}")


@dataclass(frozen=True, slots=True)
class ExactRealizationProof:
    proof_ref: str
    semantic_input_ref: str
    semantic_fingerprint: str
    exact_fingerprint: str
    surface_candidate_ref: str
    surface_sha256: str
    authority_generation: int
    authority_fingerprint: str
    semantic_authority_snapshot_fingerprint: str
    permission_ref: str
    audience_refs: tuple[str, ...]
    language_tag: str
    steps: tuple[ExactRealizationTransformStep, ...]
    required_coverage_refs: tuple[str, ...]
    covered_semantic_refs: tuple[str, ...]
    required_qualification_refs: tuple[str, ...]
    preserved_qualification_refs: tuple[str, ...]
    qualification_fingerprint: str
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.proof_ref, "proof_ref"), (self.semantic_input_ref, "semantic input"),
            (self.surface_candidate_ref, "surface candidate"), (self.surface_sha256, "surface hash"),
            (self.authority_fingerprint, "authority fingerprint"),
            (self.semantic_authority_snapshot_fingerprint, "semantic authority snapshot fingerprint"),
            (self.permission_ref, "permission"), (self.language_tag, "language"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"exact realization {label} is required")
        if self.authority_generation < 1 or not self.steps:
            raise ValueError("exact realization proof requires authority generation and transform steps")
        for values, label in (
            (self.audience_refs, "audiences"), (self.required_coverage_refs, "required coverage"),
            (self.covered_semantic_refs, "covered semantics"),
            (self.required_qualification_refs, "required qualifications"),
            (self.preserved_qualification_refs, "preserved qualifications"),
            (self.proof_refs, "proof refs"),
        ):
            _unique(values, f"exact realization proof {label}")


@dataclass(frozen=True, slots=True)
class SemanticPreservationAssessmentV351:
    assessment_ref: str
    proof_ref: str
    decision: PreservationDecision
    checked_pin_refs: tuple[str, ...]
    missing_coverage_refs: tuple[str, ...]
    missing_qualification_refs: tuple[str, ...]
    stale_pin_refs: tuple[str, ...]
    reason_refs: tuple[str, ...]
    semantic_input_fingerprint: str
    qualification_fingerprint: str

    @property
    def passed(self) -> bool:
        return self.decision is PreservationDecision.PASS


def _surface_sha256(surface: str) -> str:
    return hashlib.sha256(surface.encode("utf-8")).hexdigest()


def semantic_graph(value: Any) -> CSIRGraph:
    graph = getattr(value, "graph", value)
    if not isinstance(graph, CSIRGraph):
        raise TypeError("Phase-12 realization accepts canonical CSIR only")
    return graph


def semantic_input_ref(value: Any) -> str:
    for name in ("decision_ref", "response_ref", "candidate_ref"):
        found = getattr(value, name, None)
        if found:
            return str(found)
    raise ValueError("semantic input requires stable response identity")


def required_semantic_coverage(value: Any) -> tuple[str, ...]:
    explicit = getattr(value, "semantic_coverage_refs", None)
    if callable(explicit):
        return tuple(sorted(set(map(str, explicit()))))
    graph = semantic_graph(value)
    refs: set[str] = set()
    refs.update(item.term_ref for item in graph.terms)
    refs.update(item.variable_ref for item in graph.variables)
    refs.update(item.application_ref for item in graph.applications)
    refs.update(item.binding_ref for item in graph.bindings)
    refs.update(item.qualifier_ref for item in graph.qualifiers)
    refs.update(item.embedding_ref for item in graph.scope_embeddings)
    refs.update(item.coordination_ref for item in graph.coordinations)
    # Proof links are lineage, not denotational surface content, and therefore are carried
    # through proof_refs rather than requiring lexical realization.
    refs.update(f"root:{item.kind.value}:{item.ref}" for item in graph.root_refs)
    return tuple(sorted(refs))


def qualification_document(value: Any) -> Mapping[str, Any]:
    explicit = getattr(value, "qualification_document", None)
    if callable(explicit):
        return dict(explicit())
    graph = semantic_graph(value)
    return {
        "context_ref": getattr(value, "context_ref", None),
        "permission_ref": getattr(value, "permission_ref", None),
        "audience_refs": tuple(sorted(getattr(value, "audience_refs", ()) or ())),
        "qualification_refs": tuple(sorted(getattr(value, "qualification_refs", ()) or ())),
        "qualifiers": tuple(
            (
                item.qualifier_ref, item.target.kind.value, item.target.ref, item.qualifier_kind.value,
                None if item.value_ref is None else (item.value_ref.kind.value, item.value_ref.ref),
                item.value_atom, None if item.value_pin is None else item.value_pin.key,
            )
            for item in graph.qualifiers
        ),
        "scope_embeddings": tuple(
            (
                item.embedding_ref, item.operator.kind.value, item.operator.ref,
                item.scoped.kind.value, item.scoped.ref, item.scope_kind_pin.key, item.order,
            )
            for item in graph.scope_embeddings
        ),
        "source_bindings": tuple(
            (
                getattr(item, "source_ref", ""), getattr(item, "semantic_ref", ""),
                tuple(sorted(getattr(item, "proof_refs", ()) or ())),
                tuple(sorted(getattr(item, "evidence_refs", ()) or ())),
                getattr(item, "semantic_fingerprint", ""), getattr(item, "exact_fingerprint", ""),
                getattr(item, "confidence", None),
            )
            for item in getattr(value, "source_bindings", ()) or ()
        ),
    }


def required_qualification_refs(value: Any) -> tuple[str, ...]:
    doc = qualification_document(value)
    refs: set[str] = set()
    for key in ("context_ref", "permission_ref"):
        val = doc.get(key)
        if val not in (None, ""):
            refs.add(f"qualification:{key}:{val}")
    refs.update(f"qualification:audience:{item}" for item in doc.get("audience_refs", ()) or ())
    refs.update(f"qualification:target:{item}" for item in doc.get("target_refs", ()) or ())
    refs.update(f"qualification:declared:{item}" for item in doc.get("qualification_refs", ()) or ())
    for key in ("qualifiers", "scope_embeddings", "source_bindings"):
        for item in doc.get(key, ()) or ():
            refs.add(
                f"qualification:{key}:" + runtime_fingerprint("realization-qualification", item, 24)
            )
    return tuple(sorted(refs))


class ExactRealizationProofBuilder:
    def build(
        self,
        *,
        semantic_input: Any,
        surface_candidate_ref: str,
        surface: str,
        authority_snapshot: AuthoritySnapshotV351,
        permission_ref: str,
        audience_refs: tuple[str, ...],
        language_tag: str,
        steps: Iterable[ExactRealizationTransformStep],
        coverage_refs: Iterable[str],
        proof_refs: Iterable[str] = (),
    ) -> ExactRealizationProof:
        graph = semantic_graph(semantic_input)
        required = required_semantic_coverage(semantic_input)
        covered = tuple(sorted(set(map(str, coverage_refs))))
        steps = tuple(steps)
        if not steps:
            raise ValueError("proof-carrying realization requires deterministic transform steps")
        step_coverage = tuple(sorted({ref for step in steps for ref in step.coverage_refs}))
        if step_coverage != covered:
            raise ValueError("realization coverage must equal exact union of transform-step coverage")
        required_set = set(required)
        covered_set = set(covered)
        missing = tuple(sorted(required_set.difference(covered_set)))
        unexpected = tuple(sorted(covered_set.difference(required_set)))
        if missing or unexpected:
            raise ValueError(
                f"realization proof coverage must exactly equal required semantics; missing={missing}; unexpected={unexpected}"
            )
        required_q = required_qualification_refs(semantic_input)
        preserved_q = tuple(sorted({
            ref for step in steps for ref in step.preserved_qualification_refs
        }))
        required_q_set = set(required_q)
        preserved_q_set = set(preserved_q)
        missing_q = tuple(sorted(required_q_set.difference(preserved_q_set)))
        unexpected_q = tuple(sorted(preserved_q_set.difference(required_q_set)))
        if missing_q or unexpected_q:
            raise ValueError(
                f"realization proof qualifications must exactly match; missing={missing_q}; unexpected={unexpected_q}"
            )
        qfp = runtime_fingerprint("realization-qualifications-v351", qualification_document(semantic_input), 64)
        proof_ref = "realization-proof-v351:" + runtime_fingerprint(
            "realization-proof-v351",
            (
                semantic_input_ref(semantic_input), semantic_fingerprint(graph), exact_fingerprint(graph),
                surface_candidate_ref, _surface_sha256(surface), authority_snapshot.generation,
                authority_snapshot.authority_fingerprint, authority_snapshot.snapshot_fingerprint,
                language_tag, tuple(step.step_ref for step in steps), required, covered,
                required_q, preserved_q, qfp,
            ),
            32,
        )
        return ExactRealizationProof(
            proof_ref=proof_ref,
            semantic_input_ref=semantic_input_ref(semantic_input),
            semantic_fingerprint=semantic_fingerprint(graph),
            exact_fingerprint=exact_fingerprint(graph),
            surface_candidate_ref=surface_candidate_ref,
            surface_sha256=_surface_sha256(surface),
            authority_generation=authority_snapshot.generation,
            authority_fingerprint=authority_snapshot.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=authority_snapshot.snapshot_fingerprint,
            permission_ref=permission_ref,
            audience_refs=tuple(sorted(set(audience_refs))),
            language_tag=language_tag,
            steps=steps,
            required_coverage_refs=required,
            covered_semantic_refs=covered,
            required_qualification_refs=required_q,
            preserved_qualification_refs=preserved_q,
            qualification_fingerprint=qfp,
            proof_refs=tuple(sorted(set(map(str, proof_refs)))),
        )


class ExactRealizationProofVerifier:
    """Replay cheap preservation under the exact Stage-0 semantic authority snapshot."""

    def verify(
        self,
        *,
        semantic_input: Any,
        surface: str,
        proof: ExactRealizationProof,
        authority_snapshot: AuthoritySnapshotV351,
    ) -> SemanticPreservationAssessmentV351:
        reasons: list[str] = []
        stale: list[str] = []
        checked: list[str] = []
        graph = semantic_graph(semantic_input)
        if (proof.authority_generation, proof.authority_fingerprint) != (
            authority_snapshot.generation, authority_snapshot.authority_fingerprint,
        ):
            reasons.append("realization_proof_authority_generation_mismatch")
        if proof.semantic_authority_snapshot_fingerprint != authority_snapshot.snapshot_fingerprint:
            reasons.append("realization_proof_semantic_snapshot_mismatch")
        if proof.semantic_input_ref != semantic_input_ref(semantic_input):
            reasons.append("semantic_input_identity_changed")
        if proof.semantic_fingerprint != semantic_fingerprint(graph):
            reasons.append("semantic_input_fingerprint_changed")
        if proof.exact_fingerprint != exact_fingerprint(graph):
            reasons.append("semantic_input_exact_fingerprint_changed")
        if proof.surface_sha256 != _surface_sha256(surface):
            reasons.append("surface_hash_changed")
        qfp = runtime_fingerprint("realization-qualifications-v351", qualification_document(semantic_input), 64)
        if proof.qualification_fingerprint != qfp:
            reasons.append("semantic_qualification_drift")
        required = set(required_semantic_coverage(semantic_input))
        covered = set(proof.covered_semantic_refs)
        missing = tuple(sorted(required.difference(covered)))
        unexpected = tuple(sorted(covered.difference(required)))
        if set(proof.required_coverage_refs) != required:
            reasons.append("required_semantic_coverage_set_changed")
        if missing:
            reasons.append("semantic_coverage_incomplete")
        if unexpected:
            reasons.append("semantic_coverage_contains_unexpected_refs")
        step_coverage = {ref for step in proof.steps for ref in step.coverage_refs}
        if step_coverage != covered:
            reasons.append("semantic_coverage_not_exactly_backed_by_transform_steps")
        required_q = set(required_qualification_refs(semantic_input))
        preserved_q = set(proof.preserved_qualification_refs)
        missing_q = tuple(sorted(required_q.difference(preserved_q)))
        unexpected_q = tuple(sorted(preserved_q.difference(required_q)))
        if set(proof.required_qualification_refs) != required_q:
            reasons.append("required_qualification_set_changed")
        if missing_q:
            reasons.append("required_qualifications_not_preserved")
        if unexpected_q:
            reasons.append("preserved_qualifications_contain_unexpected_refs")
        step_q = {ref for step in proof.steps for ref in step.preserved_qualification_refs}
        if step_q != preserved_q:
            reasons.append("qualification_preservation_not_backed_by_transform_steps")

        for step in proof.steps:
            for pin in (
                *step.rule_pins, *step.lexical_pins, *step.morphology_pins, *step.linearization_pins,
            ):
                checked.append(pin.ref)
                try:
                    authority_snapshot.require_known_pin(pin)
                except MissingExactDependency:
                    stale.append(pin.ref)
        if stale:
            reasons.append("realization_authority_pin_missing_from_pinned_generation")
        decision = PreservationDecision.FAIL if reasons else PreservationDecision.PASS
        return SemanticPreservationAssessmentV351(
            assessment_ref="semantic-preservation-v351:" + runtime_fingerprint(
                "semantic-preservation-v351",
                (
                    proof.proof_ref, decision.value, tuple(sorted(set(reasons))),
                    missing, unexpected, missing_q, unexpected_q, tuple(sorted(set(stale))),
                ),
                24,
            ),
            proof_ref=proof.proof_ref,
            decision=decision,
            checked_pin_refs=tuple(sorted(set(checked))),
            missing_coverage_refs=missing,
            missing_qualification_refs=missing_q,
            stale_pin_refs=tuple(sorted(set(stale))),
            reason_refs=tuple(sorted(set(reasons))),
            semantic_input_fingerprint=proof.semantic_fingerprint,
            qualification_fingerprint=proof.qualification_fingerprint,
        )


def _unique(values, label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


__all__ = [
    "ExactRealizationProof", "ExactRealizationProofBuilder", "ExactRealizationProofVerifier",
    "ExactRealizationTransformStep", "PreservationDecision", "SemanticPreservationAssessmentV351",
    "qualification_document", "required_qualification_refs", "required_semantic_coverage",
]
