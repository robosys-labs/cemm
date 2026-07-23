from __future__ import annotations

import pytest

from cemm.v350.csir.model import ExactAuthorityPin
from cemm.v350.language.minimum_swahili_v351 import CONSTRUCTIONS, SHARED_SEMANTIC_SLOTS
from cemm.v350.language.model import ConstructionProgramOperation
from cemm.v350.observation.fusion_v351 import DependenceAwareEvidenceFusionV351, EvidenceContributionV351
from cemm.v350.observation.model_v351 import (
    CalibratedFeatureV351, ExactReferentBindingV351, ModalityKind, RawObservationV351,
)
from cemm.v350.observation.operation_outcome_v351 import OperationReentryGuardV351


def pin(ref: str) -> ExactAuthorityPin:
    return ExactAuthorityPin("test", "tests", ref, 1, "a" * 64)


def test_raw_observation_preserves_zero_confidence():
    item = RawObservationV351(
        observation_ref="obs:zero", modality=ModalityKind.VISION,
        source_ref="camera:test", payload={}, context_ref="actual", permission_ref="public",
        confidence=0.0, evidence_refs=("evidence:zero",), lineage_refs=("lineage:zero",),
    )
    assert item.confidence == 0.0


def test_calibrated_feature_requires_exact_calibration_and_evidence():
    item = CalibratedFeatureV351(
        feature_ref="feature:x", feature_name="provider_x", value=4.2, confidence=0.0,
        calibration_pin=pin("calibration:x"), evidence_refs=("e:x",), dependence_ref="dep:x",
    )
    assert item.confidence == 0.0
    with pytest.raises(ValueError):
        CalibratedFeatureV351(
            feature_ref="feature:y", feature_name="provider_y", value=1, confidence=1.0,
            calibration_pin=pin("calibration:y"), evidence_refs=(),
        )


def test_correlated_evidence_uses_weakest_magnitude_not_sum():
    fusion = DependenceAwareEvidenceFusionV351()
    result = fusion.fuse((
        EvidenceContributionV351("a", 0.9, ("e:a",), dependence_ref="same"),
        EvidenceContributionV351("b", 0.3, ("e:b",), dependence_ref="same"),
    ))
    assert result.cluster_scores == (("same", 0.3),)


def test_conflicting_correlated_transforms_cancel_cluster():
    fusion = DependenceAwareEvidenceFusionV351()
    result = fusion.fuse((
        EvidenceContributionV351("a", 0.9, ("e:a",), dependence_ref="same"),
        EvidenceContributionV351("b", -0.2, ("e:b",), dependence_ref="same"),
    ))
    assert result.cluster_scores == (("same", 0.0),)
    assert result.fused_score == 0.0


def test_direct_referent_binding_requires_exact_authority_and_evidence():
    binding = ExactReferentBindingV351("referent:r", pin("binding:r"), ("e:r",))
    assert binding.referent_ref == "referent:r"
    with pytest.raises(ValueError):
        ExactReferentBindingV351("referent:r", pin("binding:r"), ())


def test_operation_reentry_guard_is_cumulative_and_bounded():
    guard = OperationReentryGuardV351(3, "f" * 64, hop_count=2, seen_observation_refs=("o1", "o2"))
    assert guard.hop_count == 2
    with pytest.raises(ValueError):
        OperationReentryGuardV351(3, "f" * 64, hop_count=3)


def test_swahili_source_uses_shared_semantic_slots_and_generic_vm():
    assert "participant_role:speaker" in SHARED_SEMANTIC_SLOTS
    assert "projection:manner_or_state" in SHARED_SEMANTIC_SLOTS
    assert CONSTRUCTIONS
    for construction in CONSTRUCTIONS:
        for step in construction.program:
            assert isinstance(step.operation, ConstructionProgramOperation)


def test_operation_fragments_without_projection_authority_remain_frontier():
    from types import SimpleNamespace
    from cemm.v350.observation.operation_outcome_v351 import CanonicalOperationOutcomeAssimilatorV351
    from cemm.v350.runtime_abi import RuntimeInput

    cycle = SimpleNamespace(
        cycle_ref="cycle:test",
        context_ref="conversation",
        permission_ref="conversation",
        input_payload=RuntimeInput("", speaker_ref="speaker:test", participant_evidence_refs=("e:speaker",)),
        artifacts={
            "operation_observations": ({
                "operation_ref": "operation:test",
                "observation_ref": "operation-observation:test",
                "actual_outcome": "ok",
                "semantic_fragments": (object(),),
                "evidence_refs": ("e:operation",),
            },),
        },
    )
    capability = SimpleNamespace(authority_generation=1, authority_fingerprint="f" * 64)
    outcome = CanonicalOperationOutcomeAssimilatorV351().assimilate(
        cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None,
    )
    assert outcome.reentry_request is None
    assert outcome.frontier_refs == (
        "frontier:operation-reentry:semantic-projection-authority-missing:operation-observation:test",
    )
