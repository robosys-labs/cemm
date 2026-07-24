"""Representation-neutral proof-carrying realization contracts.

The proof validates deterministic transform lineage and semantic coverage.  It does
not depend on UOL and can therefore carry forward unchanged when Response CSIR lands.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Any, Iterable

from ..learning.model import PinnedRecord
from ..schema.model import canonical_data, semantic_fingerprint
from ..semantic_capability import (
    CompiledSemanticCapabilityRegistry, SemanticCapabilityError,
)
from ..schema.model import UseOperation


class PreservationDecision(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class RealizationTransformStep:
    step_ref: str
    transform_kind: str
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    rule_pins: tuple[PinnedRecord, ...] = ()
    lexical_pins: tuple[PinnedRecord, ...] = ()
    morphology_pins: tuple[PinnedRecord, ...] = ()
    linearization_pins: tuple[PinnedRecord, ...] = ()
    coverage_refs: tuple[str, ...] = ()
    preserved_qualification_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.step_ref or not self.transform_kind:
            raise ValueError("realization transform step requires identity and kind")
        if not self.input_refs or not self.output_refs:
            raise ValueError("realization transform step requires linked inputs and outputs")
        for values, label in (
            (self.input_refs, "input refs"), (self.output_refs, "output refs"),
            (self.coverage_refs, "coverage refs"),
            (self.preserved_qualification_refs, "qualification refs"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate transform step {label}")
        pins = (*self.rule_pins, *self.lexical_pins, *self.morphology_pins, *self.linearization_pins)
        keys = tuple((pin.key, pin.record_fingerprint) for pin in pins)
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate exact authority pin inside realization transform step")


@dataclass(frozen=True, slots=True)
class RealizationProof:
    proof_ref: str
    semantic_input_ref: str
    semantic_input_fingerprint: str
    surface_candidate_ref: str
    surface_sha256: str
    authority_generation: int
    authority_fingerprint: str
    permission_ref: str
    audience_refs: tuple[str, ...]
    steps: tuple[RealizationTransformStep, ...]
    required_coverage_refs: tuple[str, ...]
    covered_semantic_refs: tuple[str, ...]
    required_qualification_refs: tuple[str, ...]
    preserved_qualification_refs: tuple[str, ...]
    qualification_fingerprint: str
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.proof_ref or not self.semantic_input_ref or not self.surface_candidate_ref:
            raise ValueError("realization proof requires stable semantic/surface identities")
        if self.authority_generation < 1 or not self.authority_fingerprint:
            raise ValueError("realization proof requires exact authority generation")
        if not self.steps:
            raise ValueError("realization proof requires deterministic transform steps")
        for values, label in (
            (self.required_coverage_refs, "required coverage"),
            (self.covered_semantic_refs, "covered semantics"),
            (self.required_qualification_refs, "required qualifications"),
            (self.preserved_qualification_refs, "preserved qualifications"),
            (self.proof_refs, "proof refs"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate realization proof {label}")


@dataclass(frozen=True, slots=True)
class SemanticPreservationAssessment:
    assessment_ref: str
    proof_ref: str
    decision: PreservationDecision
    checked_pin_refs: tuple[str, ...]
    missing_coverage_refs: tuple[str, ...]
    stale_pin_refs: tuple[str, ...]
    reason_refs: tuple[str, ...]
    semantic_input_fingerprint: str
    qualification_fingerprint: str

    @property
    def passed(self) -> bool:
        return self.decision == PreservationDecision.PASS


def _surface_sha256(surface: str) -> str:
    return hashlib.sha256(surface.encode("utf-8")).hexdigest()


def semantic_payload(value: Any) -> Any:
    graph = getattr(value, "graph", value)
    fingerprint = getattr(graph, "record_fingerprint", None) or getattr(graph, "fingerprint", None)
    if fingerprint:
        return fingerprint
    return semantic_fingerprint("semantic-payload", canonical_data(graph), 64)


def _stable_ref(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    for name in (
        "term_ref", "variable_ref", "application_ref", "binding_ref",
        "qualifier_ref", "relation_ref", "root_ref", "scope_relation_ref",
        "annotation_ref", "response_ref", "decision_ref", "graph_ref", "ref",
    ):
        found = getattr(value, name, None)
        if found:
            return str(found)
    return None


def qualification_document(value: Any) -> Any:
    """Canonical qualification surface for UOL-migration and future CSIR objects.

    Exact CSIR implementations may provide ``qualification_document`` directly.
    Otherwise we conservatively collect context/time/polarity/modality/source/
    permission qualifiers plus response scope metadata without assuming one graph
    representation.
    """
    explicit = getattr(value, "qualification_document", None)
    if callable(explicit):
        return canonical_data(explicit())
    if explicit is not None:
        return canonical_data(explicit)
    graph = getattr(value, "graph", value)
    qualifiers = getattr(graph, "qualifiers", ()) or ()
    applications = getattr(graph, "applications", {}) or {}
    return {
        "qualifiers": canonical_data(qualifiers),
        "applications": tuple(sorted(
            (
                str(ref),
                getattr(app, "context_ref", None),
                getattr(app, "time_ref", None),
                str(getattr(getattr(app, "polarity", None), "value", getattr(app, "polarity", ""))),
                str(getattr(getattr(app, "modality", None), "value", getattr(app, "modality", ""))),
                str(getattr(getattr(app, "use_operation", None), "value", getattr(app, "use_operation", ""))),
                getattr(app, "source_ref", None),
                getattr(app, "permission_ref", None),
            )
            for ref, app in applications.items()
        )),
        "relations": canonical_data(
            getattr(graph, "relations", ()) or getattr(graph, "scope_relations", ()) or ()
        ),
        "context_ref": getattr(value, "context_ref", None),
        "permission_ref": getattr(value, "permission_ref", None),
        "sensitivity": getattr(value, "sensitivity", None),
        "audience_refs": tuple(sorted(getattr(value, "audience_refs", ()) or ())),
    }


def required_qualification_refs(value: Any) -> tuple[str, ...]:
    doc = qualification_document(value)
    refs: set[str] = set()
    if isinstance(doc, dict):
        for key in ("context_ref", "permission_ref", "sensitivity"):
            val = doc.get(key)
            if val not in (None, ""):
                refs.add(f"qualification:{key}:{val}")
        for audience in doc.get("audience_refs", ()) or ():
            refs.add(f"qualification:audience:{audience}")
        for item in doc.get("qualifiers", ()) or ():
            refs.add("qualification:qualifier:" + semantic_fingerprint("qualification-item", item, 24))
        for relation in doc.get("relations", ()) or ():
            refs.add("qualification:relation:" + semantic_fingerprint("qualification-relation", relation, 24))
        for app in doc.get("applications", ()) or ():
            refs.add("qualification:application:" + semantic_fingerprint("qualification-application", app, 24))
    return tuple(sorted(refs))


def required_semantic_coverage(value: Any) -> tuple[str, ...]:
    """All exact semantic units that realization must account for.

    Future CSIR graphs may expose ``semantic_coverage_refs`` directly.  The generic
    path covers the mathematical CSIR families T,V,A,B,Q,R,Pi plus migration-era
    roots/scope relations without treating surface strings as semantic identity.
    """
    explicit = getattr(value, "semantic_coverage_refs", None)
    if callable(explicit):
        return tuple(sorted(set(map(str, explicit()))))
    if explicit is not None:
        return tuple(sorted(set(map(str, explicit))))
    graph = getattr(value, "graph", value)
    refs: set[str] = set()
    for field in (
        "terms", "variables", "applications", "bindings", "qualifiers",
        "relations", "proof_annotations", "annotations",
    ):
        collection = getattr(graph, field, None)
        if isinstance(collection, dict):
            refs.update(map(str, collection.keys()))
        elif collection:
            for item in collection:
                ref = _stable_ref(item)
                if ref:
                    refs.add(ref)
    for root in getattr(graph, "root_refs", ()) or ():
        ref = _stable_ref(root)
        if ref:
            refs.add(ref)
    for relation in getattr(graph, "scope_relations", ()) or ():
        ref = _stable_ref(relation)
        if ref:
            refs.add(ref)
    refs.discard("")
    return tuple(sorted(refs))


class RealizationProofBuilder:
    def __init__(self, store) -> None:
        self.store = store

    def build(
        self,
        *,
        semantic_input_ref: str,
        semantic_input: Any,
        surface_candidate_ref: str,
        surface: str,
        authority_generation: int,
        authority_fingerprint: str,
        permission_ref: str,
        audience_refs: tuple[str, ...],
        steps: Iterable[RealizationTransformStep],
        coverage_refs: Iterable[str],
        proof_refs: Iterable[str] = (),
    ) -> RealizationProof:
        required = required_semantic_coverage(semantic_input)
        covered = tuple(sorted(set(map(str, coverage_refs))))
        required_qualifications = required_qualification_refs(semantic_input)
        qfp = semantic_fingerprint("realization-qualifications", qualification_document(semantic_input), 64)
        steps = tuple(steps)
        if not steps:
            raise ValueError("proof-carrying realization requires at least one deterministic transform step")
        step_coverage = tuple(sorted({ref for step in steps for ref in step.coverage_refs}))
        if covered != step_coverage:
            raise ValueError("realization proof coverage must equal the union of transform-step coverage")
        missing_required = tuple(sorted(set(required).difference(covered)))
        if missing_required:
            raise ValueError(f"realization proof omits required semantic coverage:{missing_required}")
        preserved_qualifications = tuple(sorted({
            ref for step in steps for ref in step.preserved_qualification_refs
        }))
        missing_qualifications = tuple(
            sorted(set(required_qualifications).difference(preserved_qualifications))
        )
        if missing_qualifications:
            raise ValueError(
                f"realization proof omits required semantic qualifications:{missing_qualifications}"
            )
        return RealizationProof(
            proof_ref="realization-proof:" + semantic_fingerprint(
                "realization-proof",
                (semantic_input_ref, semantic_payload(semantic_input), surface_candidate_ref,
                 _surface_sha256(surface), authority_generation, authority_fingerprint,
                 tuple(step.step_ref for step in steps), required, covered,
                 required_qualifications, preserved_qualifications, qfp),
                24,
            ),
            semantic_input_ref=semantic_input_ref,
            semantic_input_fingerprint=str(semantic_payload(semantic_input)),
            surface_candidate_ref=surface_candidate_ref,
            surface_sha256=_surface_sha256(surface),
            authority_generation=authority_generation,
            authority_fingerprint=authority_fingerprint,
            permission_ref=permission_ref,
            audience_refs=tuple(sorted(set(audience_refs))),
            steps=steps,
            required_coverage_refs=required,
            covered_semantic_refs=covered,
            required_qualification_refs=required_qualifications,
            preserved_qualification_refs=preserved_qualifications,
            qualification_fingerprint=qfp,
            proof_refs=tuple(sorted(set(proof_refs))),
        )


class RealizationProofVerifier:
    def __init__(self, store, semantic_capabilities: CompiledSemanticCapabilityRegistry | None = None) -> None:
        self.store = store
        self.semantic_capabilities = semantic_capabilities or CompiledSemanticCapabilityRegistry(store)

    def verify(self, *, semantic_input: Any, surface: str, proof: RealizationProof) -> SemanticPreservationAssessment:
        reasons: list[str] = []
        stale: list[str] = []
        checked: list[str] = []
        current_authority = self.store.current_authority_snapshot()
        if (
            proof.authority_generation != current_authority.generation
            or proof.authority_fingerprint != current_authority.authority_fingerprint
        ):
            reasons.append("realization_proof_authority_generation_stale")
        semantic_ref = _stable_ref(semantic_input)
        if semantic_ref is not None and proof.semantic_input_ref != semantic_ref:
            reasons.append("semantic_input_identity_changed")
        if proof.semantic_input_fingerprint != str(semantic_payload(semantic_input)):
            reasons.append("semantic_input_fingerprint_changed")
        if proof.surface_sha256 != _surface_sha256(surface):
            reasons.append("surface_hash_changed")
        expected_qfp = semantic_fingerprint("realization-qualifications", qualification_document(semantic_input), 64)
        if proof.qualification_fingerprint != expected_qfp:
            reasons.append("semantic_qualification_drift")
        required = set(required_semantic_coverage(semantic_input))
        covered = set(proof.covered_semantic_refs)
        missing = tuple(sorted(required - covered))
        if missing:
            reasons.append("semantic_coverage_incomplete")
        step_coverage = {ref for step in proof.steps for ref in step.coverage_refs}
        if step_coverage != covered:
            reasons.append("semantic_coverage_not_exactly_backed_by_transform_steps")

        required_qualifications = set(required_qualification_refs(semantic_input))
        preserved_qualifications = set(proof.preserved_qualification_refs)
        step_qualifications = {
            ref for step in proof.steps for ref in step.preserved_qualification_refs
        }
        if set(proof.required_qualification_refs) != required_qualifications:
            reasons.append("required_qualification_set_changed")
        if not required_qualifications.issubset(preserved_qualifications):
            reasons.append("required_qualifications_not_preserved")
        if step_qualifications != preserved_qualifications:
            reasons.append("qualification_preservation_not_backed_by_transform_steps")

        for step in proof.steps:
            pins = (*step.rule_pins, *step.lexical_pins, *step.morphology_pins, *step.linearization_pins)
            if not pins:
                reasons.append(f"transform_step_missing_exact_authority:{step.step_ref}")
            for pin in pins:
                checked.append(pin.record_ref)
                stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
                if stored is None or stored.record_fingerprint != pin.record_fingerprint:
                    stale.append(pin.record_ref)
                    continue
                try:
                    self.semantic_capabilities.require(pin, UseOperation.REALIZE)
                except SemanticCapabilityError:
                    stale.append(pin.record_ref)

        if stale:
            reasons.append("realization_authority_pin_stale_or_ineligible")
        decision = PreservationDecision.FAIL if reasons else PreservationDecision.PASS
        return SemanticPreservationAssessment(
            assessment_ref="semantic-preservation:" + semantic_fingerprint(
                "semantic-preservation-assessment",
                (proof.proof_ref, decision.value, tuple(sorted(set(reasons))), missing, tuple(sorted(set(stale)))),
                24,
            ),
            proof_ref=proof.proof_ref,
            decision=decision,
            checked_pin_refs=tuple(sorted(set(checked))),
            missing_coverage_refs=missing,
            stale_pin_refs=tuple(sorted(set(stale))),
            reason_refs=tuple(sorted(set(reasons))),
            semantic_input_fingerprint=proof.semantic_input_fingerprint,
            qualification_fingerprint=proof.qualification_fingerprint,
        )


__all__ = [
    "PreservationDecision", "RealizationProof", "RealizationProofBuilder",
    "RealizationProofVerifier", "RealizationTransformStep",
    "SemanticPreservationAssessment", "qualification_document",
    "required_qualification_refs", "required_semantic_coverage", "semantic_payload",
]
