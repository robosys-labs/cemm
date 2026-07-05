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
    "social": 6,
    "creative": 7,
    "unknown": 8,
}

_KIND_TO_OBLIGATION: dict[str, str] = {
    "safety": "abstain_policy",
    "question": "answer_concept",
    "correction": "repair",
    "repair": "repair",
    "teaching": "continue_teaching",
    "assertion": "store_patch",
    "command": "store_patch",
    "social": "social_reply",
    "creative": "social_reply",
    "unknown": "abstain_policy",
}

_RESPONSE_MODE: dict[str, str] = {
    "safety": "safety_refusal",
    "question": "evidence_answer",
    "correction": "repair",
    "repair": "repair",
    "teaching": "teaching_continuation",
    "assertion": "store_confirmation",
    "command": "store_confirmation",
    "social": "social_response",
    "creative": "creative_response",
    "unknown": "general_conversation",
}

_EVIDENCE_POLICY: dict[str, str] = {
    "safety": "none",
    "question": "required",
    "correction": "required",
    "repair": "required",
    "teaching": "speaker_asserted",
    "assertion": "speaker_asserted",
    "command": "speaker_asserted",
    "social": "none",
    "creative": "none",
    "unknown": "none",
}

_WRITE_POLICY: dict[str, str] = {
    "safety": "none",
    "question": "none",
    "correction": "patch_only",
    "repair": "none",
    "teaching": "patch_only",
    "assertion": "patch_only",
    "command": "patch_only",
    "social": "none",
    "creative": "none",
    "unknown": "none",
}


class SemanticObligationScheduler:
    def schedule(
        self,
        program: SemanticProgram,
        working_set: Any | None = None,
        kernel: Any | None = None,
        uol_graph: Any | None = None,
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
        obligation_kind = self._refine_obligation(kind, entry, program, kernel, uol_graph)

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
            response_mode=_RESPONSE_MODE.get(kind, "general_conversation"),
            evidence_policy=_EVIDENCE_POLICY.get(kind, "none"),
            write_policy=_WRITE_POLICY.get(kind, "none"),
            required_slots=required_slots,
            blocked_by=blocked_by,
            child_obligations=child_obligations,
            suppressed_obligations=suppressed,
            confidence=entry.confidence,
        )

    def _refine_obligation(
        self,
        kind: str,
        entry: Any,
        program: SemanticProgram,
        kernel: Any | None = None,
        uol_graph: Any | None = None,
    ) -> str:
        base = _KIND_TO_OBLIGATION.get(kind, "abstain_policy")

        if base == "answer_concept":
            if self._targets_self(entry, uol_graph):
                return "answer_self_model"
            if kernel is not None:
                conv = getattr(kernel, "conversation", None)
                if conv is not None:
                    active_teaching = getattr(conv, "active_teaching_target", "")
                    if active_teaching and kind == "teaching":
                        return "continue_teaching"

        if base == "social_reply":
            for inst in program.instructions:
                if inst.instruction_id == entry.instruction_id:
                    continue
                if _OBLIGATION_PRIORITY.get(inst.instruction_kind, 8) < _OBLIGATION_PRIORITY.get(kind, 8):
                    return _KIND_TO_OBLIGATION.get(inst.instruction_kind, "abstain_policy")

        return base

    def _targets_self(self, entry: Any, uol_graph: Any | None = None) -> bool:
        if uol_graph is not None:
            for aid in entry.atom_ids:
                atom = uol_graph.atoms.get(aid)
                if atom is not None and atom.kind == "self":
                    return True
        for slot_key in entry.output_slots:
            if "self" in slot_key or "identity" in slot_key:
                return True
        return False

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
