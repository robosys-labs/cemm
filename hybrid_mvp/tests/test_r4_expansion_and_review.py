"""R4 all-surface expansion and external review authority tests."""
from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.authority import AtomRecord, DesignationIndex
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContractCompiler,
    ReviewedScenario,
)
from cemm_authoritative_hybrid.r4_expansion import CaseExpander, ExpandedCase
from cemm_authoritative_hybrid.r4_review import (
    CorpusReviewManifest,
    ExternalReviewRequired,
    ReviewManifestVerifier,
)

__cemm_test_inventory__ = {
    "tests/test_r4_expansion_and_review.py::test_expander_uses_every_reviewed_surface_and_environment": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-expander-uses-every-reviewed-surface-and-environment",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Complete",
        "owner_ref": "surface-review",
        "source_ast_sha256": "680dd423e3d81a0a44a01d675c3721a6bb9e36b7f3106333502c3b1734308387"
    },
    "tests/test_r4_expansion_and_review.py::test_review_manifest_requires_external_signature": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-review-manifest-requires-external-signature",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Complete",
        "owner_ref": "surface-review",
        "source_ast_sha256": "95460f840bbec1bb4d26e4469919532c88a76f0f0a452e791200260ea9bc9d64"
    },
    "tests/test_r4_expansion_and_review.py::test_review_verifier_uses_injected_external_trust_root": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-review-verifier-uses-injected-external-trust-root",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Complete",
        "owner_ref": "surface-review",
        "source_ast_sha256": "84e12333b1e2b1b8e5b8b220e707930de9e3d2dfd2fc3bf2488a3b00d612ce03"
    }
}



class _Authority:
    generation = "authority:test"
    atoms = {
        ref: AtomRecord(ref=ref, kind=kind)
        for ref, kind in {
            "rel:mother_in_law": "relation_type",
        }.items()
    }
    event_signatures = {}
    value_dimensions = {}
    designations = DesignationIndex(
        by_surface={("mother-in-law", "en"): ("rel:mother_in_law",)},
        by_target={("rel:mother_in_law", "en"): ("mother-in-law",)},
    )
    capabilities = {}
    permissions = ()
    adapters = ()
    operator_roles = {}
    rules = {}


def _scenario():
    return ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:multi",
            "review_status": "reviewed",
            "competency_category": "designation_definition",
            "semantic_assertions": [
                {
                    "kind": "designates",
                    "surface": "mother-in-law",
                    "target": "rel:mother_in_law",
                }
            ],
            "surface_examples": [
                "mother-in-law",
                "mother in law",
                "spouse's mother",
            ],
            "expected_gap_kind": None,
            "metadata": {},
        }
    )


def _compiler():
    return ExpectedCycleContractCompiler(_Authority(), abi_registry_ref="abi:test")


def _pin():
    return RevisionPin("authority:test", 0, 0, 0, 0, "model:test")


def test_expander_uses_every_reviewed_surface_and_environment() -> None:
    expanded = CaseExpander(_compiler()).expand(
        _scenario(), revision_pin=_pin(), environments=({}, {"permission_refs": []})
    )
    assert len(expanded) == 6
    assert {row.surface for row in expanded} == set(_scenario().surface_examples)
    assert all(ExpandedCase.from_dict(row.as_dict()) == row for row in expanded)


_SHA = "sha256:" + "0" * 64


def test_review_manifest_requires_external_signature() -> None:
    with pytest.raises(ExternalReviewRequired):
        CorpusReviewManifest.create(
            scenario_source_sha256=_SHA,
            assertion_registry_sha256=_SHA,
            expected_contract_set_sha256=_SHA,
            derivation_contract_set_sha256=_SHA,
            expanded_case_set_sha256=_SHA,
            structural_sufficiency_sha256=_SHA,
            episode_set_sha256=_SHA,
            mutation_set_sha256=_SHA,
            mutation_observation_set_sha256=_SHA,
            partition_manifest_sha256s=(_SHA,),
            training_allowlist_sha256=_SHA,
            authority_generation="authority:test",
            abi_registry_ref="abi:test",
            source_revision="source:test",
            reviewer_ref="reviewer:test",
            reviewer_policy_ref="policy:test",
            decision="approve",
            nonce="n",
            issued_at="2026-08-05T00:00:00Z",
            signature_algorithm="none",
            signature="x" * 16,
        )


class _MatchingVerifier:
    def verify_signature(
        self, reviewer_ref: str, payload, algorithm: str, signature: str
    ) -> bool:
        return (
            reviewer_ref == "reviewer:test"
            and algorithm == "test-signature-v1"
            and signature == "signed-payload-xx"
        )


def test_review_verifier_uses_injected_external_trust_root() -> None:
    manifest = CorpusReviewManifest.create(
        scenario_source_sha256=_SHA,
        assertion_registry_sha256=_SHA,
        expected_contract_set_sha256=_SHA,
        derivation_contract_set_sha256=_SHA,
        expanded_case_set_sha256=_SHA,
        structural_sufficiency_sha256=_SHA,
        episode_set_sha256=_SHA,
        mutation_set_sha256=_SHA,
        mutation_observation_set_sha256=_SHA,
        partition_manifest_sha256s=(_SHA,),
        training_allowlist_sha256=_SHA,
        authority_generation="authority:test",
        abi_registry_ref="abi:test",
        source_revision="source:test",
        reviewer_ref="reviewer:test",
        reviewer_policy_ref="policy:test",
        decision="approve",
        nonce="n",
        issued_at="2026-08-05T00:00:00Z",
        signature_algorithm="test-signature-v1",
        signature="signed-payload-xx",
    )
    assert ReviewManifestVerifier(
        _MatchingVerifier()
    ).verify(manifest) == manifest
