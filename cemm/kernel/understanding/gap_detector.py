"""GapDetector — sole authority for gap creation (v3.4).

Creates a gap only when a concrete missing or conflicting artifact
blocks a selected interpretation, query, plan, operation, or response.

Import boundary: model + understanding submodules only. No engine imports.

Architectural guardrails (UNDERSTANDING_PIPELINE.md §13, AUTHORITY_MATRIX):
- A gap exists only when missing structure blocks a selected goal.
- Known surface form never suppresses a structural gap.
- Required blocker vocabulary:
    missing_semantic_family
    missing_definition_field
    missing_required_role
    missing_value_type
    missing_constitutive_pattern
    missing_differentiator
    ungrounded_dependency
    unsupported_recursive_cycle
    missing_independent_competence
    actual_context_not_admitted
    expressiveness_blocker
    sense_individuation_pending
    stale_assessment

Authority: gap_creation
Must not decide it: unknown-token logger
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ..model.gap import GapRecord, ProbePlan, LearningBudget


# Canonical blocker vocabulary from UNDERSTANDING_PIPELINE.md §13
BLOCKER_KINDS: tuple[str, ...] = (
    "missing_semantic_family",
    "missing_definition_field",
    "missing_required_role",
    "missing_value_type",
    "missing_constitutive_pattern",
    "missing_differentiator",
    "ungrounded_dependency",
    "unsupported_recursive_cycle",
    "missing_independent_competence",
    "actual_context_not_admitted",
    "expressiveness_blocker",
    "sense_individuation_pending",
    "stale_assessment",
)


@dataclass(frozen=True, slots=True)
class GapDetectionResult:
    """Result of gap detection over a candidate graph."""
    gaps: tuple[GapRecord, ...] = ()
    blocking_gaps: tuple[GapRecord, ...] = ()
    has_blocking: bool = False

    @property
    def gap_count(self) -> int:
        return len(self.gaps)


class GapDetector:
    """Sole authority for gap creation.

    A gap exists only when missing structure blocks a selected goal.
    Known surface form never suppresses a structural gap.

    Does NOT:
    - Create generic token-learning gaps for unknown words
    - Suppress gaps based on surface familiarity
    - Mutate persistent stores
    - Select interpretations
    """

    def detect(
        self,
        candidate_graph: Any | None = None,
        grounding_assessments: list[Any] | None = None,
        epistemic_assessments: list[Any] | None = None,
        capability_assessment: Any | None = None,
        selected_interpretations: list[Any] | None = None,
    ) -> GapDetectionResult:
        """Detect concrete gaps from the understanding pipeline outputs.

        Gaps are created only when missing structure blocks a selected
        interpretation, query, plan, operation, or response.
        """
        gaps: list[GapRecord] = []

        # 1. Check grounding assessments for ungrounded referents
        if grounding_assessments:
            for ga in grounding_assessments:
                is_unknown = getattr(ga, "is_unknown", False)
                if is_unknown:
                    gaps.append(GapRecord(
                        id=f"gap:{uuid4().hex[:12]}",
                        gap_kind="missing_semantic_family",
                        target_artifact_ref=getattr(ga, "referent_ref", ""),
                        blocked_stage="ground",
                        learnable=True,
                        probe_options=(
                            ProbePlan(
                                probe_kind="ask_user",
                                target_ref=getattr(ga, "referent_ref", ""),
                                expected_evidence_kind="definition",
                            ),
                        ),
                    ))

        # 2. Check epistemic assessments for blocked admissibility
        if epistemic_assessments:
            for ea in epistemic_assessments:
                admissibility = getattr(ea, "admissibility", "")
                if admissibility == "blocked":
                    gaps.append(GapRecord(
                        id=f"gap:{uuid4().hex[:12]}",
                        gap_kind="actual_context_not_admitted",
                        target_artifact_ref=getattr(ea, "proposition_ref", ""),
                        blocked_stage="know",
                        learnable=False,
                    ))

        # 3. Check candidate graph for open ports
        if candidate_graph is not None:
            open_ports = getattr(candidate_graph, "open_ports", ())
            for op in open_ports:
                role_name = getattr(op, "role_name", "unknown")
                gaps.append(GapRecord(
                    id=f"gap:{uuid4().hex[:12]}",
                    gap_kind="missing_required_role",
                    target_artifact_ref=role_name,
                    blocked_stage="compose",
                    learnable=True,
                    probe_options=(
                        ProbePlan(
                            probe_kind="ask_user",
                            target_ref=role_name,
                            expected_evidence_kind="role_filler",
                        ),
                    ),
                ))

        # 4. Check capability assessment for missing competence
        if capability_assessment is not None:
            is_capable = getattr(capability_assessment, "is_capable", True)
            if not is_capable:
                limitations = getattr(capability_assessment, "limitations", ())
                for lim in limitations:
                    gaps.append(GapRecord(
                        id=f"gap:{uuid4().hex[:12]}",
                        gap_kind="missing_independent_competence",
                        target_artifact_ref=str(lim),
                        blocked_stage="know",
                        learnable=True,
                    ))

        # 5. Check for opaque lexemes that block actual-world use
        if candidate_graph is not None:
            opaque_refs = getattr(candidate_graph, "opaque_lexeme_refs", ())
            for ref in opaque_refs:
                gaps.append(GapRecord(
                    id=f"gap:{uuid4().hex[:12]}",
                    gap_kind="sense_individuation_pending",
                    target_artifact_ref=ref,
                    blocked_stage="ground",
                    learnable=True,
                    probe_options=(
                        ProbePlan(
                            probe_kind="ask_user",
                            target_ref=ref,
                            expected_evidence_kind="definition",
                        ),
                    ),
                ))

        # Classify blocking gaps
        blocking = tuple(g for g in gaps if g.blocked_stage in ("ground", "know", "compose"))
        blocking_ids = {g.id for g in blocking}

        return GapDetectionResult(
            gaps=tuple(gaps),
            blocking_gaps=blocking,
            has_blocking=len(blocking) > 0,
        )

    def classify_blocking(
        self,
        gaps: tuple[GapRecord, ...],
        selected_refs: set[str],
    ) -> tuple[GapRecord, ...]:
        """Classify which gaps are blocking for the selected interpretations."""
        blocking: list[GapRecord] = []
        for gap in gaps:
            if gap.target_artifact_ref in selected_refs:
                blocking.append(gap)
            elif gap.blocked_stage in ("ground", "know"):
                blocking.append(gap)
        return tuple(blocking)
