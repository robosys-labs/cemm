"""SemanticObligationScheduler — schedule ObligationFrame from SemanticProgram.

Takes a SemanticProgram, SemanticWorkingSet, and ContextKernel and produces
an ObligationFrame that determines the authoritative action for the turn.

The scheduler enforces semantic obligation ranking: a social wrapper can
never suppress a stronger content obligation. The response_mode is only
an output strategy — obligation_kind is the authority.
"""

from __future__ import annotations

from typing import Any

from ..types.obligation_frame import ObligationFrame
from ..types.semantic_program import SemanticProgram


_OBLIGATION_PRIORITY: dict[str, int] = {
    "safety": 0,
    "question": 1,
    "correction": 2,
    "repair": 2,
    "teaching": 3,
    "assertion": 4,
    "command": 5,
    "self_reflect": 5,
    "exit": 6,
    "social": 7,
    "creative": 8,
    "unknown": 9,
}

_KIND_TO_OBLIGATION: dict[str, str] = {
    "safety": "abstain_policy",
    "question": "answer_concept",
    "correction": "repair",
    "repair": "repair",
    "teaching": "continue_teaching",
    "assertion": "store_patch",
    "command": "store_patch",
    "exit": "exit",
    "social": "social_reply",
    "creative": "social_reply",
    "unknown": "abstain_policy",
    "self_reflect": "answer_self_model",
}

_RESPONSE_MODE: dict[str, str] = {
    "safety": "safety_refusal",
    "question": "evidence_answer",
    "correction": "repair",
    "repair": "repair",
    "teaching": "teaching_continuation",
    "assertion": "store_confirmation",
    "command": "store_confirmation",
    "exit": "session_exit",
    "social": "social_response",
    "creative": "creative_response",
    "unknown": "general_conversation",
    "self_reflect": "self_identity",
    "answer_self_identity": "self_identity",
    "answer_self_capability": "evidence_answer",
    "answer_self_knowledge": "evidence_answer",
    "answer_self_model": "self_identity",
    "acknowledge_emotional_context": "emotional_response",
}

_EVIDENCE_POLICY: dict[str, str] = {
    "safety": "none",
    "question": "required",
    "correction": "required",
    "repair": "required",
    "teaching": "speaker_asserted",
    "assertion": "speaker_asserted",
    "command": "speaker_asserted",
    "exit": "none",
    "social": "none",
    "creative": "none",
    "unknown": "none",
    "self_reflect": "required",
}

_WRITE_POLICY: dict[str, str] = {
    "safety": "none",
    "question": "none",
    "correction": "patch_only",
    "repair": "none",
    "teaching": "patch_only",
    "assertion": "patch_only",
    "command": "patch_only",
    "exit": "none",
    "social": "none",
    "creative": "none",
    "unknown": "none",
    "self_reflect": "none",
}


class SemanticObligationScheduler:
    def schedule(
        self,
        program: SemanticProgram,
        working_set: Any | None = None,
        kernel: Any | None = None,
        uol_graph: Any | None = None,
        affordance_predictions: list[Any] | None = None,
    ) -> ObligationFrame:
        entry = program.entry_instruction
        if entry is None:
            return ObligationFrame(
                primary_instruction_id="",
                obligation_kind="abstain_policy",
                response_mode="general_conversation",
                confidence=0.3,
            )

        kind = entry.instruction_kind
        obligation_kind = self._refine_obligation(
            kind, entry, program, kernel, uol_graph,
            affordance_predictions=affordance_predictions,
        )

        # H-007: If social reply was refined to a content obligation, switch
        # entry to the higher-priority instruction so query uses its data
        if kind == "social_reply" and obligation_kind != "social_reply":
            for inst in program.instructions:
                if inst.instruction_id == entry.instruction_id:
                    continue
                if _KIND_TO_OBLIGATION.get(inst.instruction_kind, "") == obligation_kind:
                    entry = inst
                    kind = inst.instruction_kind
                    break

        suppressed: list[dict[str, Any]] = []
        for inst in program.instructions:
            if inst.instruction_id == entry.instruction_id:
                continue
            inst_rank = _OBLIGATION_PRIORITY.get(inst.instruction_kind, 8)
            entry_rank = _OBLIGATION_PRIORITY.get(kind, 8)
            if inst_rank > entry_rank:
                suppressed.append({
                    "instruction_id": inst.instruction_id,
                    "instruction_kind": inst.instruction_kind,
                    "reason": "lower_semantic_force",
                })

        child_obligations = [
            inst.instruction_id
            for inst in program.instructions
            if inst.discourse_parent_id == entry.group_id
            and inst.instruction_id != entry.instruction_id
        ]

        required_slots = list(entry.output_slots.keys())
        blocked_by = self._check_blockers(entry, working_set)

        return ObligationFrame(
            primary_instruction_id=entry.instruction_id,
            obligation_kind=obligation_kind,
            response_mode=_RESPONSE_MODE.get(obligation_kind, _RESPONSE_MODE.get(kind, "general_conversation")),
            evidence_policy=_EVIDENCE_POLICY.get(kind, "none"),
            write_policy=_WRITE_POLICY.get(kind, "none"),
            required_slots=required_slots,
            blocked_by=blocked_by,
            child_obligations=child_obligations,
            suppressed_obligations=suppressed,
            confidence=entry.confidence,
            context={"affordance_predictions": affordance_predictions or []},
        )

    def _refine_obligation(
        self,
        kind: str,
        entry: Any,
        program: SemanticProgram,
        kernel: Any | None = None,
        uol_graph: Any | None = None,
        affordance_predictions: list[Any] | None = None,
    ) -> str:
        base = _KIND_TO_OBLIGATION.get(kind, "abstain_policy")

        if base == "answer_concept":
            if self._targets_self(entry, uol_graph):
                refined = self._refine_self_query(entry, uol_graph)
                if refined:
                    return refined
                return "answer_self_model"
            if self._targets_user_profile(entry, uol_graph):
                return "answer_user_profile"
            if kernel is not None:
                conv = getattr(kernel, "conversation", None)
                if conv is not None:
                    active_teaching = getattr(conv, "active_teaching_target", "")
                    if active_teaching and kind == "teaching":
                        return "continue_teaching"

        if base == "answer_self_model":
            refined = self._refine_self_query(entry, uol_graph)
            if refined:
                return refined

        if base == "social_reply":
            for inst in program.instructions:
                if inst.instruction_id == entry.instruction_id:
                    continue
                if _OBLIGATION_PRIORITY.get(inst.instruction_kind, 8) < _OBLIGATION_PRIORITY.get(kind, 8):
                    return _KIND_TO_OBLIGATION.get(inst.instruction_kind, "abstain_policy")

        if base == "store_patch" and affordance_predictions:
            has_evaluation_shift = any(
                getattr(p, "effect_type", "") == "evaluation_shift"
                for p in affordance_predictions
            )
            if has_evaluation_shift:
                return "acknowledge_emotional_context"

        return base

    def _targets_user_profile(self, entry: Any, uol_graph: Any | None = None) -> bool:
        if uol_graph is None:
            return False
        for atom in uol_graph.atoms.values():
            if atom.kind == "intent" and atom.key == "user_profile_query":
                return True
        has_user_entity = False
        has_user_ref = False
        for aid in entry.atom_ids:
            atom = uol_graph.atoms.get(aid)
            if atom is None:
                continue
            if atom.kind == "entity" and atom.key == "user":
                has_user_entity = True
            role = atom.features.get("role", "")
            if role in ("possessor", "speaker", "topic", "subject", "self_target") and atom.kind == "entity":
                has_user_ref = True
        if has_user_entity and has_user_ref:
            surface_lower = entry.surface.lower()
            profile_keywords = (
                "name", "age", "old", "email", "hobby", "location",
                "address", "phone", "birthday", "occupation", "job",
                "favorite", "favourite", "preference", "like",
            )
            if any(kw in surface_lower for kw in profile_keywords):
                return True
        # Fallback: if user entity is present and surface contains "my" + profile keyword
        if has_user_entity:
            surface_lower = entry.surface.lower()
            if " my " in f" {surface_lower} " or surface_lower.startswith("my "):
                profile_keywords = (
                    "name", "age", "old", "email", "hobby", "location",
                    "address", "phone", "birthday", "occupation", "job",
                    "favorite", "favourite", "preference",
                )
                if any(kw in surface_lower for kw in profile_keywords):
                    return True
        return False

    _SELF_QUERY_INTENT_KEYS: frozenset = frozenset({
        "self_identity_query",
        "self_capability_query",
        "self_knowledge_query",
    })

    def _targets_self(self, entry: Any, uol_graph: Any | None = None) -> bool:
        if uol_graph is not None:
            for atom in uol_graph.atoms.values():
                if atom.kind == "intent" and atom.key in self._SELF_QUERY_INTENT_KEYS:
                    return True
        for slot_key in entry.output_slots:
            if "self" in slot_key or "identity" in slot_key:
                return True
        return False

    _SELF_QUERY_INTENT_TO_OBLIGATION: dict[str, str] = {
        "self_identity_query": "answer_self_identity",
        "self_capability_query": "answer_self_capability",
        "self_knowledge_query": "answer_self_knowledge",
    }

    def _refine_self_query(self, entry: Any, uol_graph: Any | None = None) -> str:
        """Check UOL graph for specific self-query intent atoms to refine obligation."""
        if uol_graph is None:
            return ""
        for atom in uol_graph.atoms.values():
            if atom.kind != "intent":
                continue
            obligation = self._SELF_QUERY_INTENT_TO_OBLIGATION.get(atom.key)
            if obligation:
                return obligation
        return ""

    def _check_blockers(self, entry: Any, working_set: Any | None = None) -> list[str]:
        blockers: list[str] = []
        if working_set is None:
            return blockers
        for port in getattr(working_set, "unresolved_ports", []):
            port_id = port if isinstance(port, str) else getattr(port, "port_key", str(port))
            if port_id in entry.output_slots:
                blockers.append(f"unresolved_port:{port_id}")
        risk_flags = getattr(working_set, "risk_flags", [])
        if risk_flags:
            blockers.append("safety_risk")
        return blockers
