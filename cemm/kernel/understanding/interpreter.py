"""InterpretationResolver (v3.4) — sole authority for interpretation selection.

Selects compatible branches using grounded structure, schemas, context,
common ground, evidence, and coherence. Rejected branches remain traceable
and cannot produce effects.

Import boundary: model + understanding submodules only. No engine imports.

Architectural guardrails (UNDERSTANDING_PIPELINE.md §11, AUTHORITY_MATRIX):
- May select an opaque/provisional interpretation when sufficient for the
  current goal (quotation, memory, attributed report, correction, learning).
- May NOT use an inadmissible/opaque meaning for:
    actual-world inheritance
    strong classification
    causal/effect claims
    state mutation
    unqualified definition answers
    unqualified self-understanding claims
    selectional rejection
- Rejected branches emit no effects, writes, or durable schema changes.

Authority: interpretation_selection
Must not decide it: operational compiler, response planner
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .candidate_graph import (
    CandidateGraph,
    CandidatePredication,
    CandidateProposition,
    CandidateCommunicativeForce,
    CandidateContext,
)


@dataclass(frozen=True, slots=True)
class SelectedInterpretation:
    """A selected interpretation from the candidate graph.

    Contains the selected predication, proposition, context, and
    communicative force, plus the confidence and rejection reasons
    for non-selected alternatives.
    """
    id: str
    predication_ref: str = ""
    proposition_ref: str = ""
    context_ref: str = ""
    communicative_force: str = ""
    confidence: float = 0.0
    selected_evidence_refs: tuple[str, ...] = ()
    rejected_alternative_refs: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    is_opaque: bool = False
    is_provisional: bool = False


@dataclass(frozen=True, slots=True)
class InterpretationResult:
    """Result of interpretation resolution over a candidate graph."""
    selected: tuple[SelectedInterpretation, ...] = ()
    rejected: tuple[SelectedInterpretation, ...] = ()
    primary: SelectedInterpretation | None = None
    has_selection: bool = False

    @property
    def selected_count(self) -> int:
        return len(self.selected)


class InterpretationResolver:
    """Sole authority for interpretation branch selection (v3.4).

    Selects compatible branches using grounded structure, schemas,
    context, common ground, evidence, and coherence.

    Rejected branches remain traceable and cannot produce effects.

    Does NOT:
    - Use inadmissible meanings for actual-world claims
    - Produce effects, writes, or durable changes
    - Select response wording
    """

    def resolve(
        self,
        candidate_graph: CandidateGraph,
        grounding_assessments: list[Any] | None = None,
        epistemic_assessments: list[Any] | None = None,
    ) -> InterpretationResult:
        """Resolve the candidate graph into selected interpretations.

        Selects compatible candidates, preserving alternatives.
        Only truly contradictory candidates are resolved by preference.
        """
        selected: list[SelectedInterpretation] = []
        rejected: list[SelectedInterpretation] = []

        # Build a confidence map from epistemic assessments
        prop_confidence: dict[str, float] = {}
        if epistemic_assessments:
            for ea in epistemic_assessments:
                prop_ref = getattr(ea, "proposition_ref", "")
                admissibility = getattr(ea, "admissibility", "blocked")
                if admissibility in ("admitted", "attributed_only"):
                    prop_confidence[prop_ref] = getattr(ea, "confidence", 0.0)

        # Group propositions by communicative force target
        forces = candidate_graph.candidate_communicative_forces
        propositions = candidate_graph.candidate_propositions
        contexts = candidate_graph.candidate_contexts
        predications = candidate_graph.candidate_predications

        # If no candidates, return empty
        if not propositions and not predications:
            return InterpretationResult()

        # Select best proposition per communicative force target
        used_prop_ids: set[str] = set()

        for force in forces:
            target_ref = force.target_proposition_ref
            matching_props = [
                cp for cp in propositions
                if cp.proposition.id == target_ref
                or (not target_ref)
            ]

            if not matching_props:
                continue

            # Sort by confidence (epistemic-adjusted), then by candidate confidence
            def sort_key(cp: CandidateProposition) -> float:
                epistemic_boost = prop_confidence.get(cp.proposition.id, 0.0)
                return cp.confidence + epistemic_boost

            matching_props.sort(key=sort_key, reverse=True)

            best = matching_props[0]
            used_prop_ids.add(best.proposition.id)

            # Find matching context
            ctx_ref = best.proposition.context_ref
            ctx = None
            for cc in contexts:
                if cc.context_frame.id == ctx_ref:
                    ctx = cc
                    break

            # Check if opaque/provisional
            is_opaque = best.proposition.context_ref == "" or ctx is None
            is_provisional = False
            if epistemic_assessments:
                for ea in epistemic_assessments:
                    if getattr(ea, "proposition_ref", "") == best.proposition.id:
                        adm = getattr(ea, "admissibility", "blocked")
                        if adm == "attributed_only":
                            is_provisional = True
                        break

            # Find predication ref
            pred_ref = ""
            for cp in predications:
                if best.proposition.id and cp.source_token_indices:
                    pred_ref = cp.predication.id
                    break

            interp = SelectedInterpretation(
                id=f"interp:{uuid4().hex[:12]}",
                predication_ref=pred_ref,
                proposition_ref=best.proposition.id,
                context_ref=ctx_ref,
                communicative_force=force.force,
                confidence=best.confidence,
                selected_evidence_refs=best.source_evidence_refs,
                is_opaque=is_opaque,
                is_provisional=is_provisional,
            )
            selected.append(interp)

            # Reject non-selected alternatives
            for alt in matching_props[1:]:
                rejected.append(SelectedInterpretation(
                    id=f"interp_rej:{uuid4().hex[:12]}",
                    proposition_ref=alt.proposition.id,
                    confidence=alt.confidence,
                    rejection_reasons=("lower_confidence",),
                ))

        # Handle propositions without communicative force
        for cp in propositions:
            if cp.proposition.id in used_prop_ids:
                continue
            epistemic_boost = prop_confidence.get(cp.proposition.id, 0.0)

            # Check epistemic admissibility for provisional/opaque status
            is_provisional = False
            if epistemic_assessments:
                for ea in epistemic_assessments:
                    if getattr(ea, "proposition_ref", "") == cp.proposition.id:
                        adm = getattr(ea, "admissibility", "blocked")
                        if adm == "attributed_only":
                            is_provisional = True
                        break

            # Find matching context
            ctx_ref = cp.proposition.context_ref
            ctx = None
            for cc in contexts:
                if cc.context_frame.id == ctx_ref:
                    ctx = cc
                    break
            is_opaque = ctx_ref == "" or ctx is None

            interp = SelectedInterpretation(
                id=f"interp:{uuid4().hex[:12]}",
                proposition_ref=cp.proposition.id,
                context_ref=ctx_ref,
                confidence=cp.confidence + epistemic_boost,
                selected_evidence_refs=cp.source_evidence_refs,
                is_opaque=is_opaque,
                is_provisional=is_provisional,
            )
            selected.append(interp)

        # Select primary (highest confidence)
        primary = max(selected, key=lambda s: s.confidence) if selected else None

        return InterpretationResult(
            selected=tuple(selected),
            rejected=tuple(rejected),
            primary=primary,
            has_selection=len(selected) > 0,
        )
