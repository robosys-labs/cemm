"""Exact immutable Phase-13 recurrent parameter authority.

The canonical runtime may install the reviewed Phase-13 baseline artifact set into an
otherwise parameter-empty semantic-authority snapshot at Stage 0.  Stage 6 itself never
falls back to code constants: it consumes only the exact artifacts pinned into that cycle
snapshot.  Learned replacements remain immutable candidate artifacts until Phase-14
calibration, competence, review and post-pass publication produce a new authority generation.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable

from ..csir.authority_v351 import AuthoritySnapshotV351, DynamicsParameterArtifact
from ..csir.model import ExactAuthorityPin
from ..schema.model import semantic_fingerprint
from .model_v351 import DynamicsParameterSet, MessageFamily, REQUIRED_MESSAGE_FAMILIES


CORE_PARAMETER_FAMILY = "dynamics:recurrent:v351:core"
MESSAGE_PARAMETER_PREFIX = "dynamics:recurrent:v351:message:"

# Explicit reviewed baseline values for the first recurrent deployment. Their exact content
# becomes authority only when Stage 0 pins the resulting artifacts into the immutable cycle
# AuthoritySnapshotV351. Later trained values never overwrite these objects in place.
MINIMUM_CORE_VALUES = (
    ("bias", -0.35),
    ("prior_gain", 1.0),
    ("bottom_up_gain", 0.85),
    ("top_down_gain", 0.70),
    ("context_gain", 0.65),
    ("inhibition_strength", 1.10),
    ("lineage_cluster_cap", 1.0),
    ("damping", 0.45),
    ("convergence_epsilon", 0.0005),
    ("activation_floor", 0.000001),
    ("retention_threshold", 0.12),
    ("ambiguity_margin", 0.08),
    ("oscillation_round_digits", 8.0),
    ("max_attractors", 8.0),
)

MINIMUM_MESSAGE_GAINS = {
    MessageFamily.LEXICAL: 0.95,
    MessageFamily.CONSTRUCTION: 1.00,
    MessageFamily.PORT_ROLE: 1.15,
    MessageFamily.TYPE: 1.10,
    MessageFamily.IDENTITY: 1.00,
    MessageFamily.SCOPE: 1.10,
    MessageFamily.TIME_ASPECT: 0.90,
    MessageFamily.CONTEXT: 1.10,
    MessageFamily.STATE: 0.95,
    MessageFamily.CAUSAL_EXPECTATION: 0.80,
    MessageFamily.DISCOURSE: 0.85,
    MessageFamily.MULTIMODAL: 0.90,
}


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _pin(family: str, revision: int, values) -> ExactAuthorityPin:
    return ExactAuthorityPin(
        kind="dynamics_parameter",
        namespace="cemm.v351",
        ref=family,
        revision=revision,
        content_hash=_hash((family, revision, tuple(values))),
        scope_ref="global",
    )


def compile_reviewed_phase13_parameter_artifacts(*, revision: int = 1) -> tuple[DynamicsParameterArtifact, ...]:
    """Build the exact reviewed recurrent baseline installed by the canonical runtime.

    The returned objects are immutable authority artifacts. Merely calling this function does
    not mutate a store; authority arises only when the artifacts are pinned into the exact
    Stage-0 ``AuthoritySnapshotV351`` for a cycle.
    """
    core = DynamicsParameterArtifact(
        parameter_pin=_pin(CORE_PARAMETER_FAMILY, revision, MINIMUM_CORE_VALUES),
        parameter_family=CORE_PARAMETER_FAMILY,
        values=tuple(MINIMUM_CORE_VALUES),
        calibration_evidence_refs=("calibration:phase13-reviewed-recurrent-baseline:v1",),
    )
    messages = tuple(
        DynamicsParameterArtifact(
            parameter_pin=_pin(
                MESSAGE_PARAMETER_PREFIX + family.value,
                revision,
                (("gain", MINIMUM_MESSAGE_GAINS[family]),),
            ),
            parameter_family=MESSAGE_PARAMETER_PREFIX + family.value,
            values=(("gain", MINIMUM_MESSAGE_GAINS[family]),),
            calibration_evidence_refs=("calibration:phase13-reviewed-recurrent-baseline:v1",),
        )
        for family in REQUIRED_MESSAGE_FAMILIES
    )
    return (core, *messages)


def compile_minimum_phase13_parameter_artifacts(*, revision: int = 1) -> tuple[DynamicsParameterArtifact, ...]:
    """Compatibility alias for the reviewed baseline; no solver-side fallback is implied."""
    return compile_reviewed_phase13_parameter_artifacts(revision=revision)


def compile_parameter_set(
    artifacts: Iterable[DynamicsParameterArtifact],
    *,
    authority_snapshot: AuthoritySnapshotV351,
) -> DynamicsParameterSet:
    """Compile only exact artifacts present in the cycle-pinned authority snapshot."""
    artifacts = tuple(artifacts)
    by_family = {item.parameter_family: item for item in artifacts}
    if len(by_family) != len(artifacts):
        raise ValueError("duplicate dynamics parameter families in authority snapshot")
    snapshot_by_family = {item.parameter_family: item for item in authority_snapshot.dynamics_parameters}
    if by_family.keys() != snapshot_by_family.keys():
        raise ValueError("Stage-6 dynamics artifacts differ from exact AuthoritySnapshotV351 inventory")
    for family, item in by_family.items():
        expected = snapshot_by_family[family]
        if item != expected or item.parameter_pin.key != expected.parameter_pin.key:
            raise ValueError(f"dynamics parameter artifact differs from cycle-pinned authority:{family}")

    if CORE_PARAMETER_FAMILY not in by_family:
        raise ValueError("missing exact recurrent core parameter artifact")
    missing_message = [
        family for family in REQUIRED_MESSAGE_FAMILIES
        if MESSAGE_PARAMETER_PREFIX + family.value not in by_family
    ]
    if missing_message:
        raise ValueError(
            "missing exact typed-message parameter families:"
            + ",".join(item.value for item in missing_message)
        )

    core_values = tuple(by_family[CORE_PARAMETER_FAMILY].values)
    family_gains = []
    for family in REQUIRED_MESSAGE_FAMILIES:
        artifact = by_family[MESSAGE_PARAMETER_PREFIX + family.value]
        values = dict(artifact.values)
        if set(values) != {"gain"}:
            raise ValueError(f"typed message artifact must contain only explicit gain:{family.value}")
        family_gains.append((family, float(values["gain"])))

    required_core = {
        "bias", "prior_gain", "bottom_up_gain", "top_down_gain", "context_gain",
        "inhibition_strength", "lineage_cluster_cap", "damping", "convergence_epsilon", "activation_floor",
        "retention_threshold", "ambiguity_margin", "oscillation_round_digits", "max_attractors",
    }
    actual_core = set(dict(core_values))
    missing = required_core.difference(actual_core)
    extra = actual_core.difference(required_core)
    if missing or extra:
        raise ValueError(f"recurrent core parameter schema mismatch:missing={sorted(missing)}:extra={sorted(extra)}")

    pins = tuple(item.parameter_pin for item in sorted(artifacts, key=lambda item: item.parameter_family))
    calibration = tuple(sorted({ref for item in artifacts for ref in item.calibration_evidence_refs}))
    ref = "dynamics-parameter-set:" + semantic_fingerprint(
        "dynamics-parameter-set-v351",
        (
            authority_snapshot.generation,
            authority_snapshot.authority_fingerprint,
            tuple(pin.key for pin in pins),
            core_values,
            tuple((family.value, gain) for family, gain in family_gains),
        ),
        32,
    )
    return DynamicsParameterSet(
        parameter_set_ref=ref,
        parameter_pins=pins,
        values=core_values,
        family_gains=tuple(family_gains),
        calibration_evidence_refs=calibration,
    )


__all__ = [
    "CORE_PARAMETER_FAMILY", "MESSAGE_PARAMETER_PREFIX", "MINIMUM_CORE_VALUES",
    "MINIMUM_MESSAGE_GAINS", "compile_minimum_phase13_parameter_artifacts",
    "compile_reviewed_phase13_parameter_artifacts", "compile_parameter_set",
]
