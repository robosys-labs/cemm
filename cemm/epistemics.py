"""Explicit claim occurrence and epistemic admission policy for CEMM v1."""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from cemm.cognition import (
    DiscourseAct,
    FORCE_CLAIM,
    FORCE_CORRECTION,
    FORCE_RETRACTION,
)
from cemm.model import stable


class AdmissionClass(str, Enum):
    ATTRIBUTED_ONLY = "ATTRIBUTED_ONLY"
    SESSION_PARTICIPANT_FACT = "SESSION_PARTICIPANT_FACT"
    SCOPED_USER_ASSERTED_FACT = "SCOPED_USER_ASSERTED_FACT"
    CORROBORATION_REQUIRED = "CORROBORATION_REQUIRED"
    HIGH_RISK_NO_AUTO_ADMISSION = "HIGH_RISK_NO_AUTO_ADMISSION"
    HYPOTHETICAL_ONLY = "HYPOTHETICAL_ONLY"


@dataclass(frozen=True)
class EpistemicPlacement:
    placement_ref: str
    admission_class: AdmissionClass
    admitted: bool
    reason: str
    context_ref: str | None
    target_refs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "placement_ref": self.placement_ref,
            "admission_class": self.admission_class.value,
            "admitted": self.admitted,
            "reason": self.reason,
            "context_ref": self.context_ref,
            "target_refs": list(self.target_refs),
        }


class EpistemicPolicy:
    """Data-driven admission classifier; it never promotes semantic authority."""

    _NON_ACTUAL = {"hypothetical", "quoted", "fictional", "counterfactual", "desired", "planned"}

    def __init__(self, store):
        self.s = store

    @staticmethod
    def _refs(apps: Iterable[dict[str, Any]]) -> tuple[str, ...]:
        refs = {
            value
            for app in apps
            for value in app.get("args", {}).values()
            if isinstance(value, str) and not value.startswith("?")
        }
        return tuple(sorted(refs))

    def _metadata_policy(self, refs: Iterable[str]) -> AdmissionClass | None:
        explicit: list[AdmissionClass] = []
        for ref in refs:
            atom = self.s.atom(ref)
            if not atom:
                continue
            metadata = json.loads(atom["metadata"])
            raw = metadata.get("admission_class")
            if raw:
                try:
                    explicit.append(AdmissionClass(str(raw)))
                except ValueError:
                    pass
            if metadata.get("high_risk_no_auto_admission"):
                explicit.append(AdmissionClass.HIGH_RISK_NO_AUTO_ADMISSION)
            elif metadata.get("corroboration_required"):
                explicit.append(AdmissionClass.CORROBORATION_REQUIRED)
            elif metadata.get("attributed_only"):
                explicit.append(AdmissionClass.ATTRIBUTED_ONLY)
        priority = (
            AdmissionClass.HIGH_RISK_NO_AUTO_ADMISSION,
            AdmissionClass.CORROBORATION_REQUIRED,
            AdmissionClass.ATTRIBUTED_ONLY,
        )
        return next((x for x in priority if x in explicit), explicit[0] if explicit else None)

    def place(self, act: DiscourseAct) -> EpistemicPlacement:
        refs = self._refs(act.content)
        if act.modality in self._NON_ACTUAL:
            klass = AdmissionClass.HYPOTHETICAL_ONLY
            reason = f"non_actual_context:{act.modality}"
        elif act.force not in {FORCE_CLAIM, FORCE_CORRECTION, FORCE_RETRACTION}:
            klass = AdmissionClass.ATTRIBUTED_ONLY
            reason = f"non_claim_force:{act.force}"
        else:
            explicit = self._metadata_policy(refs)
            if explicit:
                klass = explicit
                reason = "semantic_metadata_policy"
            else:
                speaker_bound = any(
                    app.get("args", {}).get(role) == act.speaker_ref
                    for app in act.content
                    for role in ("role:subject", "role:instance", "role:actor")
                )
                if speaker_bound:
                    klass = AdmissionClass.SESSION_PARTICIPANT_FACT
                    reason = "speaker_scoped_participant_claim"
                else:
                    klass = AdmissionClass.SCOPED_USER_ASSERTED_FACT
                    reason = "scoped_user_assertion"
        admitted = klass in {
            AdmissionClass.SESSION_PARTICIPANT_FACT,
            AdmissionClass.SCOPED_USER_ASSERTED_FACT,
        } and act.force == FORCE_CLAIM
        payload = (act.act_ref, klass.value, admitted, reason, act.context_ref, refs)
        return EpistemicPlacement(stable("epistemic-placement", payload), klass, admitted, reason, act.context_ref, refs)
