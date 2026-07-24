"""Deterministic codec for durable Phase-16 causal proof DAGs."""
from __future__ import annotations

from typing import Any, Mapping

from ..csir.model import ExactAuthorityPin
from ..state.codec_v351 import _pin
from ..state.model_v351 import ParticipantRoleBinding
from .model_v351 import CausalProofStepV351, CausalProofV351, ContextSemantics


def causal_proof_to_document(proof: CausalProofV351) -> dict[str, Any]:
    return {
        "model_version": "causal-proof-v351",
        "proof_ref": proof.proof_ref,
        "context_ref": proof.context_ref,
        "context_semantics": proof.context_semantics.value,
        "steps": tuple(
            {
                "step_ref": step.step_ref,
                "mechanism_pin": step.mechanism_pin.key,
                "source_variable_refs": step.source_variable_refs,
                "source_event_refs": step.source_event_refs,
                "target_variable_ref": step.target_variable_ref,
                "trigger_ref": step.trigger_ref,
                "branch_probability": step.branch_probability,
                "confidence": step.confidence,
                "warrant_refs": step.warrant_refs,
                "role_bindings": tuple(
                    {
                        "role_pin": item.role_pin.key,
                        "participant_ref": item.participant_ref,
                        "source_application_ref": item.source_application_ref,
                        "participant_type_pins": tuple(pin.key for pin in item.participant_type_pins),
                        "evidence_refs": item.evidence_refs,
                        "proof_refs": item.proof_refs,
                    }
                    for item in step.role_bindings
                ),
                "delta_ref": step.delta_ref,
                "prior_value_ref": step.prior_value_ref,
                "new_value_ref": step.new_value_ref,
                "secondary_event_ref": step.secondary_event_ref,
                "suppressed_delta_ref": step.suppressed_delta_ref,
                "parent_step_refs": step.parent_step_refs,
                "intervention_cut": step.intervention_cut,
            }
            for step in proof.steps
        ),
        "root_trigger_refs": proof.root_trigger_refs,
        "target_variable_refs": proof.target_variable_refs,
        "intervention_ref": proof.intervention_ref,
        "exogenous_assumption_refs": proof.exogenous_assumption_refs,
        "evidence_refs": proof.evidence_refs,
        "frontier_refs": proof.frontier_refs,
    }


def causal_proof_from_document(value: Mapping[str, Any]) -> CausalProofV351:
    data = dict(value)
    if str(data.get("model_version", "")) != "causal-proof-v351":
        raise ValueError("not a Phase-16 causal proof document")
    steps = tuple(
        CausalProofStepV351(
            step_ref=str(item["step_ref"]),
            mechanism_pin=_pin(item["mechanism_pin"]),
            source_variable_refs=tuple(map(str, item.get("source_variable_refs", ()))),
            source_event_refs=tuple(map(str, item.get("source_event_refs", ()))),
            target_variable_ref=str(item.get("target_variable_ref", "")),
            trigger_ref=str(item["trigger_ref"]),
            branch_probability=float(item["branch_probability"]),
            confidence=float(item["confidence"]),
            warrant_refs=tuple(map(str, item.get("warrant_refs", ()))),
            role_bindings=tuple(
                ParticipantRoleBinding(
                    role_pin=_pin(binding["role_pin"]),
                    participant_ref=str(binding["participant_ref"]),
                    source_application_ref=str(binding["source_application_ref"]),
                    participant_type_pins=tuple(_pin(pin) for pin in binding.get("participant_type_pins", ())),
                    evidence_refs=tuple(map(str, binding.get("evidence_refs", ()))),
                    proof_refs=tuple(map(str, binding.get("proof_refs", ()))),
                )
                for binding in item.get("role_bindings", ())
            ),
            delta_ref=str(item.get("delta_ref", "")),
            prior_value_ref=str(item.get("prior_value_ref", "")),
            new_value_ref=str(item.get("new_value_ref", "")),
            secondary_event_ref=str(item.get("secondary_event_ref", "")),
            suppressed_delta_ref=str(item.get("suppressed_delta_ref", "")),
            parent_step_refs=tuple(map(str, item.get("parent_step_refs", ()))),
            intervention_cut=bool(item.get("intervention_cut", False)),
        )
        for item in data.get("steps", ())
    )
    return CausalProofV351(
        proof_ref=str(data["proof_ref"]),
        context_ref=str(data["context_ref"]),
        context_semantics=ContextSemantics(str(data["context_semantics"])),
        steps=steps,
        root_trigger_refs=tuple(map(str, data.get("root_trigger_refs", ()))),
        target_variable_refs=tuple(map(str, data.get("target_variable_refs", ()))),
        intervention_ref=str(data.get("intervention_ref", "")),
        exogenous_assumption_refs=tuple(map(str, data.get("exogenous_assumption_refs", ()))),
        evidence_refs=tuple(map(str, data.get("evidence_refs", ()))),
        frontier_refs=tuple(map(str, data.get("frontier_refs", ()))),
    )


__all__ = ["causal_proof_from_document", "causal_proof_to_document"]
