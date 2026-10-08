"""Canonical Hybrid MVP composition root through R3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from .affordances import SemanticAffordanceIndex
from .authority import AuthorityLinker, DesignationIndex, DesignationFact
from .config import RuntimeConfig
from .canonical import stable_ref
from .contributions import ContributionExpander
from .coverage import CoverageVerifier
from .forms import FormResolver
from .gaps import MissingOwner
from .grounding import Grounder
from .persistence import open_stores
from .proposal import BootstrapProposer
from .proposal_context import ProposalContextBuilder
from .r3_effects import AdapterRegistry
from .r3_kernel import R3Kernel
from .runtime import HybridRuntime, RuntimeOrientationOwner
from .verifier import ExactProgramVerifier

__all__ = ["load_runtime"]


def load_runtime(
    root: str | Path,
    *,
    profile: Literal["development", "neural", "release"],
    device: str = "cpu",
    store_path: str | Path | None = None,
    proposal_artifact_dir: str | Path | None = None,
    realizer_artifact_dir: str | Path | None = None,
    adapters: AdapterRegistry | None = None,
    resource_refs: tuple[str, ...] = (),
) -> HybridRuntime:
    """Link authority and activate exactly one six-phase composition root."""
    if profile not in {"development", "neural", "release"}:
        raise ValueError(f"unknown profile: {profile}")
    if profile != "development":
        raise MissingOwner("program_abi_2_proposal_owner")

    project_root = Path(root)
    authority = AuthorityLinker().link_path(
        project_root / "data" / "authority" / "manifest.json"
    )
    config = RuntimeConfig.release()
    proposer = BootstrapProposer(config)

    # Complete the form and authority link BEFORE any persistent session can
    # be opened. A stable manifest generation label alone cannot guarantee
    # that meaning, grounding or proposer contracts are compatible.
    form_pack_path = project_root / "data" / "languages" / "en" / "forms.json"
    with form_pack_path.open(encoding="utf-8") as handle:
        form_pack = json.load(handle)
    resolver = FormResolver(form_pack, config)
    semantic_contract_ref = stable_ref(
        "semantic_execution_contract",
        {
            "authority_content_ref": authority.content_hash,
            "form_pack_sha256": resolver.form_pack_hash,
            "proposal_model_identity": proposer.model_identity,
        },
    )
    stores = open_stores(
        Path(store_path) if store_path is not None else project_root / "stores.db",
        authority_generation=authority.generation,
        model_identity=proposer.model_identity,
        semantic_contract_ref=semantic_contract_ref,
    )
    affordances = SemanticAffordanceIndex(authority, config)
    expander = ContributionExpander(affordances, config)

    class _DesignationStore:
        """Lookup approved aliases through the revision-owned world index."""

        def facts_for_surface(self, surface: str, language: str):
            row = stores.r3_reviewed_designation_for_surface(surface, language)
            if row is None:
                return ()
            if row["target_ref"] not in authority.atoms:
                raise ValueError("approved designation lost its reviewed target")
            return (DesignationFact.create(
                surface=row["surface"],
                target_ref=row["target_ref"],
                language=row["language"],
            ),)

        def build_index(self) -> DesignationIndex:
            # Compatibility for fixture clients; the runtime reads the durable
            # indexed method above and falls back to linked authority itself.
            return authority.designations

    grounder = Grounder(
        authority=authority,
        config=config,
        form_pack=form_pack,
        form_pack_hash=resolver.form_pack_hash,
        designation_store=_DesignationStore(),
    )
    context_builder = ProposalContextBuilder(
        authority, affordances, config, form_pack=form_pack
    )
    adapter_registry = adapters or AdapterRegistry()
    orienter = RuntimeOrientationOwner(
        authority=authority,
        stores=stores,
        config=config,
        form_resolver=resolver,
        grounder=grounder,
        contribution_expander=expander,
        context_builder=context_builder,
        resource_refs=resource_refs,
        adapter_refs=adapter_registry.refs,
    )
    verifier = ExactProgramVerifier(CoverageVerifier(config))
    r3 = R3Kernel(
        authority=authority,
        stores=stores,
        config=config,
        adapters=adapter_registry,
        resource_refs=resource_refs,
    )
    return HybridRuntime(
        config,
        authority,
        stores,
        {
            "orientation": orienter,
            "proposal": proposer,
            "verification": verifier,
            "r3": r3,
        },
        profile=profile,
    )
