"""Tests for training partition isolation and release artifact pinning (M4 Task 3).

These tests verify that:
- A release trainer cannot open validation or test partitions
  (:class:`PartitionAccessError` is raised).
- Release artifacts pin ALL semantic inputs (authority, action encoding,
  dataset, dependency lock, Python ABI, source revision, ABI registry).
- The model uses dynamic semantic slots, not ref spelling.
- Combined trainable capacity is bounded (<= 50,000,000).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.partitions import (
    PartitionAccessError,
    load_partition_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
PARTITIONS_DIR = ROOT / "data" / "partitions"
PROPOSAL_RELEASE = ROOT / "artifacts" / "proposal_release"
REALIZER_RELEASE = ROOT / "artifacts" / "realizer_release"


# ---------------------------------------------------------------------------
# Manifests fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def manifests() -> SimpleNamespace:
    """Collect all semantic-input manifests for pinning assertions."""
    from cemm_authoritative_hybrid.authority import AuthorityLinker
    from cemm_authoritative_hybrid.canonical import sha256_file
    from cemm_authoritative_hybrid.artifacts import (
        current_model_lock_hash,
        current_python_abi,
    )
    from cemm_authoritative_hybrid.config import ABIRegistry
    from cemm_authoritative_hybrid.training import _compute_action_encoding_hash
    from cemm_authoritative_hybrid.verifier import LegalActionIndex
    from cemm_authoritative_hybrid.config import RuntimeConfig

    # Authority compatibility hash.
    linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")

    # Action encoding hash (proposal).
    legal_action_index = LegalActionIndex(linked, RuntimeConfig.release())
    action_encoding_hash = _compute_action_encoding_hash(legal_action_index)

    # Partition manifest.
    pm = load_partition_manifest(PARTITIONS_DIR / "manifest.json")

    # Dependency lock + python abi.
    dep_lock = current_model_lock_hash()
    py_abi = current_python_abi()

    # ABI registry.
    abis = ABIRegistry()

    return SimpleNamespace(
        authority=SimpleNamespace(compatibility_sha256=linked.model_compatibility_hash),
        actions=SimpleNamespace(sha256=action_encoding_hash),
        train=SimpleNamespace(sha256=pm.train_sha256),
        validation=SimpleNamespace(sha256=pm.validation_sha256),
        test=SimpleNamespace(sha256=pm.test_sha256),
        dependencies=SimpleNamespace(model_sha256=dep_lock),
        environment=SimpleNamespace(python_abi=py_abi),
        abis={
            "contribution": abis.contribution,
            "switch_program": abis.switch_program,
            "coverage": abis.coverage,
            "phase_receipt": abis.phase_receipt,
            "gap_receipt": abis.gap_receipt,
            "learning_plan": abis.learning_plan,
            "response_meaning": abis.response_meaning,
            "realization_receipt": abis.realization_receipt,
        },
    )


@pytest.fixture
def sealed_paths() -> SimpleNamespace:
    """Paths to the sealed validation and test partitions."""
    return SimpleNamespace(
        validation=PARTITIONS_DIR / "validation.jsonl",
        test=PARTITIONS_DIR / "test.jsonl",
    )


# ---------------------------------------------------------------------------
# Trainer isolation
# ---------------------------------------------------------------------------


def _build_proposal_trainer():
    """Build a release proposal trainer wired with the real authority."""
    from cemm_authoritative_hybrid.authority import AuthorityLinker
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.contributions import ContributionExpander
    from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
    from cemm_authoritative_hybrid.coverage import CoverageVerifier
    from cemm_authoritative_hybrid.forms import FormResolver
    from cemm_authoritative_hybrid.grounding import Grounder
    from cemm_authoritative_hybrid.verifier import (
        ActionMasker,
        ExactProgramVerifier,
        LegalActionIndex,
    )
    from cemm_authoritative_hybrid.training import ReleaseProposalTrainer

    linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    rc = RuntimeConfig.release()

    with open(ROOT / "data" / "languages" / "en" / "forms.json", encoding="utf-8") as fh:
        form_pack = json.load(fh)

    from cemm_authoritative_hybrid.canonical import canonical_bytes
    import hashlib
    form_pack_hash = f"sha256:{hashlib.sha256(canonical_bytes(form_pack)).hexdigest()}"

    form_resolver = FormResolver(form_pack, rc)
    affordance_index = SemanticAffordanceIndex(linked, rc)
    coverage_verifier = CoverageVerifier(rc)
    verifier = ExactProgramVerifier(linked, rc, coverage_verifier)
    legal_action_index = LegalActionIndex(linked, rc)

    from cemm_authoritative_hybrid.authority import DesignationIndex

    class _StaticDesignationStore:
        def build_index(self) -> DesignationIndex:
            return linked.designations

    grounder = Grounder(
        authority=linked,
        config=rc,
        form_pack=form_pack,
        form_pack_hash=form_pack_hash,
        designation_store=_StaticDesignationStore(),
    )

    return ReleaseProposalTrainer(
        authority=linked,
        config=rc,
        form_resolver=form_resolver,
        grounder=grounder,
        affordance_index=affordance_index,
        verifier=verifier,
        coverage_verifier=coverage_verifier,
        legal_action_index=legal_action_index,
    )


@pytest.fixture
def trainer():
    """A release proposal trainer."""
    return _build_proposal_trainer()


def test_trainer_cannot_open_validation_or_test(trainer, sealed_paths):
    """A release trainer must raise PartitionAccessError on test data."""
    with pytest.raises(PartitionAccessError):
        trainer.fit(sealed_paths.test)


def test_trainer_cannot_open_validation(trainer, sealed_paths):
    """A release trainer must raise PartitionAccessError on validation data."""
    with pytest.raises(PartitionAccessError):
        trainer.fit(sealed_paths.validation)


def test_trainer_can_open_train(trainer):
    """A release trainer must be able to open the train partition."""
    # fit() returns a report; we only need to confirm it does not raise.
    report = trainer.fit(PARTITIONS_DIR / "train.jsonl")
    assert report is not None


# ---------------------------------------------------------------------------
# Release artifact pinning
# ---------------------------------------------------------------------------


def _load_release_metadata(root: Path):
    """Load the model metadata from a release artifact directory."""
    from cemm_authoritative_hybrid.artifacts import _metadata_from_dict
    from cemm_authoritative_hybrid.canonical import read_canonical_json

    return _metadata_from_dict(read_canonical_json(root / "model_metadata.json"))


@pytest.fixture
def release_metadata() -> SimpleNamespace:
    """Load metadata for both release artifacts."""
    return SimpleNamespace(
        proposal=_load_release_metadata(PROPOSAL_RELEASE),
        realizer=_load_release_metadata(REALIZER_RELEASE),
    )


@pytest.fixture
def release_models() -> list:
    """Load both release models and return their trainable parameter counts."""
    from cemm_authoritative_hybrid.canonical import sha256_file
    from cemm_authoritative_hybrid.model import (
        load_proposer_from_artifact,
        load_realizer_from_artifact,
    )
    from cemm_authoritative_hybrid.authority import AuthorityLinker
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.contributions import ContributionExpander
    from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
    from cemm_authoritative_hybrid.coverage import CoverageVerifier
    from cemm_authoritative_hybrid.forms import FormResolver
    from cemm_authoritative_hybrid.grounding import Grounder
    from cemm_authoritative_hybrid.verifier import (
        ActionMasker,
        ExactProgramVerifier,
        LegalActionIndex,
    )
    from cemm_authoritative_hybrid.realization import RealizationVerifier

    linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    rc = RuntimeConfig.release()

    with open(ROOT / "data" / "languages" / "en" / "forms.json", encoding="utf-8") as fh:
        form_pack = json.load(fh)

    from cemm_authoritative_hybrid.canonical import canonical_bytes
    import hashlib
    form_pack_hash = f"sha256:{hashlib.sha256(canonical_bytes(form_pack)).hexdigest()}"

    form_resolver = FormResolver(form_pack, rc)
    affordance_index = SemanticAffordanceIndex(linked, rc)
    contribution_expander = ContributionExpander(affordance_index, rc)
    coverage_verifier = CoverageVerifier(rc)
    verifier = ExactProgramVerifier(linked, rc, coverage_verifier)
    legal_action_index = LegalActionIndex(linked, rc)
    action_masker = ActionMasker(legal_action_index)

    from cemm_authoritative_hybrid.authority import DesignationIndex

    class _StaticDesignationStore:
        def build_index(self) -> DesignationIndex:
            return linked.designations

    grounder = Grounder(
        authority=linked,
        config=rc,
        form_pack=form_pack,
        form_pack_hash=form_pack_hash,
        designation_store=_StaticDesignationStore(),
    )

    proposer = load_proposer_from_artifact(
        PROPOSAL_RELEASE,
        sha256_file(PROPOSAL_RELEASE / "model_manifest.json"),
        verifier=verifier,
        coverage_verifier=coverage_verifier,
        legal_action_index=legal_action_index,
        action_masker=action_masker,
        form_resolver=form_resolver,
        grounder=grounder,
        affordance_index=affordance_index,
        contribution_expander=contribution_expander,
        authority=linked,
        config=rc,
    )
    realizer = load_realizer_from_artifact(
        REALIZER_RELEASE,
        sha256_file(REALIZER_RELEASE / "model_manifest.json"),
        verifier=RealizationVerifier(),
    )
    return [proposer, realizer]


def test_release_artifact_pins_all_semantic_inputs(release_metadata, manifests):
    """The proposal release artifact pins every semantic input."""
    md = release_metadata.proposal
    assert md.authority_compatibility_hash == manifests.authority.compatibility_sha256
    assert md.action_encoding_hash == manifests.actions.sha256
    assert md.dataset_hash == manifests.train.sha256
    assert md.model_dependency_lock_sha256 == manifests.dependencies.model_sha256
    assert md.python_abi == manifests.environment.python_abi
    assert md.source_revision
    assert md.abi_registry == manifests.abis


def test_realizer_release_artifact_pins_all_semantic_inputs(release_metadata, manifests):
    """The realizer release artifact pins every semantic input."""
    md = release_metadata.realizer
    assert md.authority_compatibility_hash == manifests.authority.compatibility_sha256
    assert md.model_dependency_lock_sha256 == manifests.dependencies.model_sha256
    assert md.python_abi == manifests.environment.python_abi
    assert md.source_revision
    assert md.abi_registry == manifests.abis


def test_model_uses_dynamic_semantic_slots_not_ref_spelling(release_metadata):
    """The release model uses dynamic pointer slots, not ref spelling."""
    md = release_metadata.proposal
    assert md.config.get("target_encoding") == "dynamic_pointer_slots"
    assert tuple(md.config.get("internal_ref_vocabulary", ())) == ()


def test_combined_trainable_capacity_is_bounded(release_models):
    """The combined trainable capacity of both models is <= 50,000,000."""
    total = sum(model.trainable_parameter_count for model in release_models)
    assert total <= 50_000_000
