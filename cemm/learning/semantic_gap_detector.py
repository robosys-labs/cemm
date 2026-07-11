"""SemanticGapDetector — detect unknown or uncertain meaning after candidate generation.
Classifies gaps as unknown (no candidates), ambiguous (multiple candidates),
or structurally incomplete (missing required ports/roles).
"""

from __future__ import annotations

from typing import Any
import uuid

from ..types.semantic_gap import SemanticGap, GapKind
from ..types.semantic_ref import SemanticRef, SemanticRefKind
from ..types.meaning_percept import MeaningPerceptPacket
from ..types.uol_graph import UOLGraph


class SemanticGapDetector:
    """Detects semantic gaps after candidate generation and initial group structure.
    
    A gap is created when:
    - An unknown token has no registered meaning (unknown)
    - A known token has multiple conflicting interpretations (ambiguous)
    - A predicate is missing required typed ports (structurally incomplete)
    """
    
    def detect(
        self,
        percept: MeaningPerceptPacket,
        graph: UOLGraph | None = None,
        known_forms: set[str] | None = None,
    ) -> list[SemanticGap]:
        gaps: list[SemanticGap] = []
        
        # 1. Unknown lexemes from percept
        unknown_lexemes_raw = list(getattr(percept, "unknown_lexemes", []) or [])
        known = known_forms or set()
        
        seen_tokens: set[str] = set()
        for item in unknown_lexemes_raw:
            if isinstance(item, str):
                token = item
            elif isinstance(item, dict):
                token = item.get("surface", item.get("token", ""))
            else:
                token = str(item)
            if not token or token.lower() in known or token in seen_tokens:
                continue
            seen_tokens.add(token)
            span_ref = SemanticRef(
                kind=SemanticRefKind.SPAN,
                id=f"span_{token}",
                label=token,
            )
            gap = SemanticGap(
                gap_id=uuid.uuid4().hex[:16],
                branch_id="",
                group_id="",
                span_ref=span_ref,
                language_tag=getattr(percept, "language", "und"),
                gap_kind=GapKind.LEXEME_SENSE,
                blocking_artifact_ids=(),
                entropy=1.0,
                confidence=0.0,
                surface_form=token,
            )
            gaps.append(gap)
        
        # 2. Unknown lexemes from percept.semantic_gaps (already detected earlier)
        existing_gaps = list(getattr(percept, "semantic_gaps", []) or [])
        gaps.extend(existing_gaps)
        
        # 3. Groups without resolved meaning
        if graph is not None:
            groups = getattr(percept, "meaning_groups", []) or []
            for group in groups:
                group_id = getattr(group, "id", "")
                if not group_id:
                    continue
                group_atoms = [
                    a for a in (graph.atoms or {}).values()
                    if getattr(a, "group_id", "") == group_id
                ]
                has_predicate = any(
                    a.kind in ("action", "process", "predicate", "state")
                    for a in group_atoms
                )
                has_referent = any(
                    a.kind in ("entity", "referent", "self")
                    for a in group_atoms
                )
                if not has_predicate and has_referent:
                    span_ref = SemanticRef(
                        kind=SemanticRefKind.GROUP,
                        id=group_id,
                        label=getattr(group, "surface", ""),
                    )
                    gap = SemanticGap(
                        gap_id=uuid.uuid4().hex[:16],
                        branch_id="",
                        group_id=group_id,
                        span_ref=span_ref,
                        language_tag=getattr(percept, "language", "und"),
                        gap_kind=GapKind.CONSTRUCTION,
                        blocking_artifact_ids=(),
                        entropy=0.7,
                        confidence=0.0,
                        surface_form=getattr(group, "surface", ""),
                    )
                    gaps.append(gap)
        
        # Deduplicate by surface_form and gap_kind
        seen: set[tuple[str, str]] = set()
        unique_gaps: list[SemanticGap] = []
        for gap in gaps:
            key = (gap.surface_form, gap.gap_kind.value)
            if key not in seen:
                seen.add(key)
                unique_gaps.append(gap)
        
        return unique_gaps
    
    def classify_blocking(
        self,
        gaps: list[SemanticGap],
        selected_branch_ids: set[str],
    ) -> list[SemanticGap]:
        """Classify which gaps are blocking execution.
        
        A gap is blocking if it belongs to a selected interpretation branch
        and its resolution is required for a selected obligation.
        """
        blocking: list[SemanticGap] = []
        for gap in gaps:
            if gap.branch_id in selected_branch_ids:
                if gap.gap_kind in (
                    GapKind.LEXEME_SENSE,
                    GapKind.OPERATOR_IDENTITY,
                    GapKind.REQUIRED_PORT,
                    GapKind.ENTITY_IDENTITY,
                ):
                    blocking.append(gap)
        return blocking
