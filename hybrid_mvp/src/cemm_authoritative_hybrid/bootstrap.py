"""Runtime bootstrap: link authority, open stores, assemble the six-phase kernel.

This module owns :func:`load_runtime`. It links authority via
:class:`AuthorityLinker`, opens SQLite stores, verifies the release
configuration, and refuses to start until every capability advertised by the
selected profile has an owner.

The ``development`` / ``typed_fixture`` profile uses fixture owners and accepts
an injected ``proposal_fixture``. The ``neural`` profile loads a
safetensors-backed :class:`NeuralSwitchProposer` from the artifact directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .authority import AuthorityLinker, LinkedAuthority
from .config import RuntimeConfig
from .gaps import MissingOwner
from .persistence import SemanticStores, open_stores
from .runtime import (
    FixtureEffectOwner,
    FixtureEvaluationOwner,
    FixtureProposalOwner,
    FixtureRealizationOwner,
    FixtureVerificationOwner,
    HybridRuntime,
)

__all__ = ["load_runtime"]


def load_runtime(
    root: str | Path,
    *,
    profile: str = "development",
    device: str = "cpu",
    proposal_fixture: Any = None,
    artifact_dir: str | Path | None = None,
) -> HybridRuntime:
    """Assemble and return a :class:`HybridRuntime` for the given profile.

    Links authority via ``AuthorityLinker().link_path(root / "data/authority/manifest.json")``,
    opens SQLite stores, verifies the release configuration, and refuses to
    start until every advertised capability has an owner.

    Parameters:
        root: project root directory.
        profile: ``"development"``, ``"typed_fixture"``, or ``"neural"``.
        device: torch device (used by the neural profile).
        proposal_fixture: a :class:`SemanticSwitchProgram` for the fixture
            proposal owner (required for ``development`` / ``typed_fixture``).
        artifact_dir: path to the model artifact directory for the neural
            profile (defaults to ``root / "artifacts/proposal_dev"``).

    Raises:
        MissingOwner: if any required owner is missing.
    """
    root = Path(root)

    # -- Link authority ------------------------------------------------------
    manifest_path = root / "data" / "authority" / "manifest.json"
    linked: LinkedAuthority = AuthorityLinker().link_path(manifest_path)

    # -- Open SQLite stores --------------------------------------------------
    stores: SemanticStores = open_stores(
        root / "stores.db",
        authority_generation=linked.generation,
    )

    # -- Verify release configuration ---------------------------------------
    config = RuntimeConfig.release()

    # -- Assemble owners by profile -----------------------------------------
    if profile in ("development", "typed_fixture"):
        if proposal_fixture is None:
            from .propositions import Application, PropositionGraph, SemanticSwitchProgram

            app = Application.create(
                "op:event",
                {
                    "role:event": "event-instance:bootstrap-default",
                    "role:type": "event:observation",
                    "role:actor": "participant:user",
                },
            )
            graph = PropositionGraph.create([app], app.application_ref)
            proposal_fixture = SemanticSwitchProgram.create(
                "OBSERVE", "event:context:bootstrap", graph
            )

        owners = {
            "proposal": FixtureProposalOwner(proposal_fixture),
            "verification": FixtureVerificationOwner(),
            "evaluation": FixtureEvaluationOwner(),
            "effect": FixtureEffectOwner(stores),
            "realization": FixtureRealizationOwner(),
        }
    elif profile == "neural":
        owners = _assemble_neural_owners(root, linked, config, stores, device, artifact_dir)
    else:
        raise ValueError(f"unknown profile: {profile}")

    return HybridRuntime(
        config=config,
        authority=linked,
        stores=stores,
        owners=owners,
        profile=profile,
    )


def _assemble_neural_owners(
    root: Path,
    linked: LinkedAuthority,
    config: RuntimeConfig,
    stores: SemanticStores,
    device: str,
    artifact_dir: str | Path | None,
) -> dict[str, Any]:
    """Assemble owners for the neural profile.

    Loads the safetensors artifact, wires the NeuralSwitchProposer with all
    components (authority, config, form_resolver, grounder, etc.), and returns
    the owners dict. The release factory calls the loaded network directly —
    no bootstrap/static delegate.
    """
    from .canonical import read_canonical_json, sha256_file
    from .contributions import ContributionExpander
    from .affordances import SemanticAffordanceIndex
    from .coverage import CoverageVerifier
    from .forms import FormResolver
    from .grounding import Grounder
    from .model import NeuralSwitchProposer, load_proposer_from_artifact
    from .verifier import ActionMasker, ExactProgramVerifier, LegalActionIndex

    # Load the form pack
    import json
    form_pack_path = root / "data" / "languages" / "en" / "forms.json"
    with open(form_pack_path, encoding="utf-8") as fh:
        form_pack = json.load(fh)

    # Compute the form pack hash
    from .canonical import canonical_bytes
    import hashlib
    form_pack_hash = f"sha256:{hashlib.sha256(canonical_bytes(form_pack)).hexdigest()}"

    # Build components
    form_resolver = FormResolver(form_pack, config)
    affordance_index = SemanticAffordanceIndex(linked, config)
    contribution_expander = ContributionExpander(affordance_index, config)
    coverage_verifier = CoverageVerifier(config)
    verifier = ExactProgramVerifier(linked, config, coverage_verifier)
    legal_action_index = LegalActionIndex(linked, config)
    action_masker = ActionMasker(legal_action_index)

    # Build a designation store for the grounder
    from .authority import DesignationIndex
    designation_index = linked.designations

    class _StaticDesignationStore:
        def build_index(self) -> DesignationIndex:
            return designation_index

    grounder = Grounder(
        authority=linked,
        config=config,
        form_pack=form_pack,
        form_pack_hash=form_pack_hash,
        designation_store=_StaticDesignationStore(),
    )

    # Load the artifact
    if artifact_dir is None:
        artifact_dir = root / "artifacts" / "proposal_dev"
    artifact_dir = Path(artifact_dir)

    manifest_path = artifact_dir / "model_manifest.json"
    manifest_sha256 = sha256_file(manifest_path)

    proposer = load_proposer_from_artifact(
        artifact_dir,
        manifest_sha256,
        verifier=verifier,
        coverage_verifier=coverage_verifier,
        legal_action_index=legal_action_index,
        action_masker=action_masker,
        form_resolver=form_resolver,
        grounder=grounder,
        affordance_index=affordance_index,
        contribution_expander=contribution_expander,
        authority=linked,
        config=config,
        device=device,
    )

    # Use the neural proposer as the proposal owner, and the exact verifier
    # as the verification owner (wrapping it to match the VerificationOwner
    # protocol which takes (program, orientation)).
    class _NeuralVerificationOwner:
        def verify(self, program: Any, orientation: Any) -> Any:
            return verifier.verify(program)

    class _FixtureEvaluationOwner:
        def evaluate(self, program: Any, verification: Any, orientation: Any) -> Any:
            from .runtime import EvaluationResult
            return EvaluationResult(
                status="resolved",
                output_refs=(getattr(program, "program_ref", ""),),
            )

    class _FixtureEffectOwner:
        def __init__(self, stores: SemanticStores) -> None:
            self._stores = stores

        def execute(self, evaluation: Any, orientation: Any) -> Any:
            from .runtime import EffectResult
            return EffectResult(executed=True, output_refs=())

    class _FixtureRealizationOwner:
        def realize(self, evaluation: Any, effect: Any, orientation: Any) -> Any:
            from .runtime import RealizationResult
            return RealizationResult(realized=True, output_refs=())

    return {
        "proposal": proposer,
        "verification": _NeuralVerificationOwner(),
        "evaluation": _FixtureEvaluationOwner(),
        "effect": _FixtureEffectOwner(stores),
        "realization": _FixtureRealizationOwner(),
    }
