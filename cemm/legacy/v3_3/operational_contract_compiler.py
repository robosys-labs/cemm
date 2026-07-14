"""OperationalContractCompiler — single authority for contract compilation.

Delegates to specialized builders for Query, Write, Reaction, State,
and Learning contracts. No duplicated contract creation.

Every contract carries frame/gap/episode provenance so that authorization
can be traced back to the exact interpretation branch that produced it.
"""

from __future__ import annotations

import uuid
import time
from typing import Any

from ...types.obligation_contract import (
    ObligationContract,
    QueryContract,
    WriteContract,
    ReactionContract,
    SafetyContract,
    StateContract,
    ResponseContract,
)
from ...types.operational_meaning import (
    OperationalMeaningFrame,
    OperationalEffect,
    MeaningArbitrationResult,
    is_writable_frame,
)
from ...types.obligation_graph import ObligationGraph
from ...types.semantic_gap import SemanticGap
from ...types.learning_episode import LearningEpisode
from ...types.knowledge_strength import PromotionState

from .obligation_contract_builder import ObligationContractBuilder
from .query_contract_builder import QueryContractBuilder
from .write_contract_builder import WriteContractBuilder
from .reaction_contract_builder import ReactionContractBuilder
from .state_contract_builder import StateContractBuilder
from .learning_contract_builder import LearningContractBuilder


class OperationalContractCompiler:
    """Single authority for contract compilation.

    Produces exactly one ObligationContract per turn by delegating
    to specialized builders. No other component may create contracts.
    """

    def __init__(self) -> None:
        self._obligation_builder = ObligationContractBuilder()
        self._query_builder = QueryContractBuilder()
        self._write_builder = WriteContractBuilder()
        self._reaction_builder = ReactionContractBuilder()
        self._state_builder = StateContractBuilder()
        self._learning_builder = LearningContractBuilder()

    def compile(
        self,
        frames: list[OperationalMeaningFrame],
        arbitration: MeaningArbitrationResult,
        effects: list[OperationalEffect] | None = None,
        safety_frame: Any | None = None,
        state_transmutations: list[Any] | None = None,
        obligation_graph: ObligationGraph | None = None,
        gaps: list[SemanticGap] | None = None,
        episodes: list[LearningEpisode] | None = None,
        durable_store: Any | None = None,
        graph: Any | None = None,
        percept: Any | None = None,
    ) -> ObligationContract:
        """Compile one ObligationContract from all available inputs.

        Delegates to each sub-builder in order and attaches provenance.
        """
        if not frames:
            return self._empty_contract()

        # 1. Build base obligation contract from frames
        contract = self._obligation_builder.build(
            frames, arbitration,
            effects=effects,
            safety_frame=safety_frame,
        )

        # 2. Delegate to specialized builders
        selected_frame = self._primary_frame(frames, arbitration)
        if selected_frame is not None:
            qc = self._query_builder.build(selected_frame, durable_store)
            if qc is not None:
                contract.query_contract = qc
                contract.query_policy = "query"

            wc = self._write_builder.build(selected_frame, graph)
            if wc is not None:
                contract.write_contract = wc
                contract.write_policy = "patch_only" if wc.is_writable else "none"

            rc = self._reaction_builder.build(selected_frame, effects)
            if rc is not None:
                contract.reaction_contract = rc
                contract.reaction_policy = rc.reaction_kind

        sc = self._state_builder.build(state_transmutations or [])
        if sc is not None:
            contract.state_contract = sc
            contract.state_policy = (
                "observed_delta" if sc.modality == "observed" else "reported_delta"
            )

        # 3. Build ResponseContract with output act metadata
        rc_contract = ResponseContract(
            primary_obligation_id=contract.primary_meaning_frame_id,
            expected_output_acts=self._expected_acts(contract),
            evidence_policy=(
                getattr(contract.query_contract, "evidence_policy", "none")
                if contract.query_contract is not None else "none"
            ),
            source_frame_id=contract.primary_meaning_frame_id,
            confidence=contract.confidence,
        )
        contract.response_contract = rc_contract

        # 4. Attach provenance from frames, gaps, and episodes
        contract.source_frame_ids = [f.frame_id for f in frames]
        if gaps:
            contract.source_gap_ids = [g.gap_id for g in gaps]
        if episodes:
            contract.source_episode_ids = [e.episode_id for e in episodes]

        branch_ids: set[str] = set()
        group_ids: set[str] = set()
        for f in frames:
            if getattr(f, "branch_id", ""):
                branch_ids.add(f.branch_id)
            if getattr(f, "group_id", ""):
                group_ids.add(f.group_id)
        contract.source_branch_ids = list(branch_ids)
        contract.source_group_ids = list(group_ids)

        # 5. Build LearningContract for active episodes
        if episodes:
            for episode in episodes:
                lc = self._learning_builder.build(episode)
                if lc is not None:
                    contract.diagnostics.setdefault("learning_contracts", []).append(
                        lc.to_dict() if hasattr(lc, "to_dict") else {"contract_id": lc.contract_id}
                    )

        return contract

    def _primary_frame(
        self,
        frames: list[OperationalMeaningFrame],
        arbitration: MeaningArbitrationResult,
    ) -> OperationalMeaningFrame | None:
        if not frames:
            return None
        primary_id = (
            arbitration.selected_frame_ids[0]
            if arbitration.selected_frame_ids
            else frames[0].frame_id
        )
        return next((f for f in frames if f.frame_id == primary_id), frames[0])

    @staticmethod
    def _expected_acts(contract: ObligationContract) -> list[str]:
        acts: list[str] = []
        if contract.response_mode == "answer":
            acts.append("inform")
        elif contract.response_mode == "confirm_write":
            acts.append("confirm")
        elif contract.response_mode == "clarify":
            acts.append("question")
        elif contract.response_mode == "refuse":
            acts.append("refusal")
        elif contract.response_mode == "social":
            acts.append("acknowledge")
        elif contract.response_mode == "exit":
            acts.append("farewell")
        if contract.state_contract is not None:
            acts.append("state_delta")
        return acts

    @staticmethod
    def _empty_contract() -> ObligationContract:
        return ObligationContract(
            contract_id=f"oc_{uuid.uuid4().hex[:12]}",
            primary_meaning_frame_id="",
            obligation_kind="abstain",
            response_mode="abstain",
            confidence=0.3,
            diagnostics={"reason": "no_meaning_frames"},
        )

    @property
    def obligation_builder(self) -> ObligationContractBuilder:
        return self._obligation_builder

    @property
    def query_builder(self) -> QueryContractBuilder:
        return self._query_builder

    @property
    def write_builder(self) -> WriteContractBuilder:
        return self._write_builder

    @property
    def reaction_builder(self) -> ReactionContractBuilder:
        return self._reaction_builder

    @property
    def state_builder(self) -> StateContractBuilder:
        return self._state_builder

    @property
    def learning_builder(self) -> LearningContractBuilder:
        return self._learning_builder
