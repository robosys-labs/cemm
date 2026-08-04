"""Canonical Hybrid MVP composition root."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from .affordances import SemanticAffordanceIndex
from .authority import AuthorityLinker, DesignationIndex
from .config import RuntimeConfig
from .contributions import ContributionExpander
from .coverage import CoverageVerifier
from .forms import FormResolver
from .gaps import MissingOwner
from .grounding import Grounder
from .persistence import open_stores
from .proposal import BootstrapProposer
from .proposal_context import ProposalContextBuilder
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
) -> HybridRuntime:
    """Link authority and activate exactly one admitted runtime profile."""
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
    stores = open_stores(
        Path(store_path) if store_path is not None else project_root / "stores.db",
        authority_generation=authority.generation,
        model_identity=proposer.model_identity,
    )

    form_pack_path = project_root / "data" / "languages" / "en" / "forms.json"
    with form_pack_path.open(encoding="utf-8") as handle:
        form_pack = json.load(handle)
    resolver = FormResolver(form_pack, config)
    affordances = SemanticAffordanceIndex(authority, config)
    expander = ContributionExpander(affordances, config)

    class _DesignationStore:
        def build_index(self) -> DesignationIndex:
            return authority.designations

    grounder = Grounder(
        authority=authority,
        config=config,
        form_pack=form_pack,
        form_pack_hash=resolver.form_pack_hash,
        designation_store=_DesignationStore(),
    )
    context_builder = ProposalContextBuilder(authority, affordances, config, form_pack=form_pack)
    orienter = RuntimeOrientationOwner(
        authority=authority,
        stores=stores,
        config=config,
        form_resolver=resolver,
        grounder=grounder,
        contribution_expander=expander,
        context_builder=context_builder,
    )
    verifier = ExactProgramVerifier(CoverageVerifier(config))
    return HybridRuntime(
        config,
        authority,
        stores,
        {
            "orientation": orienter,
            "proposal": proposer,
            "verification": verifier,
        },
        profile=profile,
    )