"""Deterministic bounded joint solver for Phase-8 grounding."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from ..schema.model import semantic_fingerprint
from .model import (
    GroundingAssignment,
    GroundingCandidate,
    GroundingConstraint,
    GroundingConstraintKind,
    GroundingResult,
    MentionHypothesis,
)


@dataclass(frozen=True, slots=True)
class _Partial:
    chosen: tuple[GroundingCandidate, ...]
    score: float
    satisfied: tuple[str, ...] = ()
    optional_violations: tuple[str, ...] = ()


class JointGroundingSolver:
    def __init__(
        self,
        *,
        beam_width: int = 64,
        maximum_assignments: int = 8,
        ambiguity_margin: float = 0.35,
        provisional_penalty: float = 0.5,
    ) -> None:
        if beam_width < 1 or maximum_assignments < 1:
            raise ValueError("grounding bounds must be positive")
        if ambiguity_margin < 0 or provisional_penalty < 0:
            raise ValueError("grounding margins/penalties cannot be negative")
        self.beam_width = beam_width
        self.maximum_assignments = maximum_assignments
        self.ambiguity_margin = ambiguity_margin
        self.provisional_penalty = provisional_penalty

    def solve(
        self,
        mentions: Iterable[MentionHypothesis],
        candidates: Iterable[GroundingCandidate],
        *,
        constraints: Iterable[GroundingConstraint] = (),
        evidence_refs: tuple[str, ...] = (),
    ) -> GroundingResult:
        mention_items = tuple(sorted(mentions, key=lambda item: (item.span.start, item.span.end, item.mention_ref)))
        candidate_items = tuple(candidates)
        constraint_items = tuple(sorted(constraints, key=lambda item: item.constraint_ref))
        mention_refs = tuple(item.mention_ref for item in mention_items)
        if len(mention_refs) != len(set(mention_refs)):
            raise ValueError("grounding mentions must be unique")
        by_mention: dict[str, list[GroundingCandidate]] = defaultdict(list)
        for candidate in candidate_items:
            if candidate.mention_ref not in set(mention_refs):
                raise ValueError(f"candidate refers to unknown mention: {candidate.mention_ref}")
            by_mention[candidate.mention_ref].append(candidate)
        for values in by_mention.values():
            values.sort(key=lambda item: (-item.local_score, item.provisional, item.origin.value, item.target_ref))

        missing_mentions = tuple(ref for ref in mention_refs if not by_mention.get(ref))
        solvable = tuple(item for item in mention_items if by_mention.get(item.mention_ref))
        beam = (_Partial((), 0.0),)
        for mention in solvable:
            expanded: list[_Partial] = []
            for partial in beam:
                for candidate in by_mention[mention.mention_ref]:
                    chosen = (*partial.chosen, candidate)
                    status = self._constraints(chosen, constraint_items, complete=False)
                    if status is None:
                        continue
                    satisfied, optional, cross_score = status
                    score = sum(item.local_score for item in chosen)
                    score -= sum(self.provisional_penalty for item in chosen if item.provisional)
                    score += cross_score
                    expanded.append(_Partial(chosen, score, satisfied, optional))
            expanded.sort(key=self._partial_sort_key)
            beam = tuple(expanded[: self.beam_width])
            if not beam:
                break

        complete: list[_Partial] = []
        if solvable:
            for partial in beam:
                status = self._constraints(partial.chosen, constraint_items, complete=True)
                if status is None:
                    continue
                satisfied, optional, cross_score = status
                base = sum(item.local_score for item in partial.chosen)
                base -= sum(self.provisional_penalty for item in partial.chosen if item.provisional)
                complete.append(_Partial(partial.chosen, base + cross_score, satisfied, optional))
        complete.sort(key=self._partial_sort_key)
        complete = complete[: self.maximum_assignments]

        assignments = tuple(self._assignment(item) for item in complete)
        ambiguous_mentions = self._ambiguous_mentions(assignments)
        selected = None
        if assignments:
            decisive = len(assignments) == 1 or assignments[0].score - assignments[1].score > self.ambiguity_margin
            candidate_by_ref = {item.candidate_ref: item for item in candidate_items}
            best_is_resolved = all(
                not candidate_by_ref[ref].provisional
                for ref in assignments[0].candidate_refs
            )
            if decisive and best_is_resolved and not ambiguous_mentions and not missing_mentions:
                selected = assignments[0].assignment_ref

        provisional_only_mentions = {
            mention_ref
            for mention_ref, values in by_mention.items()
            if values and all(item.provisional for item in values)
        }
        unresolved = tuple(sorted(
            (set(missing_mentions) | provisional_only_mentions) - set(ambiguous_mentions)
        ))
        frontier = tuple(sorted({
            candidate.target_ref for candidate in candidate_items
            if candidate.provisional and selected is None
        }))
        grounding_ref = "grounding:" + semantic_fingerprint(
            "grounding-ref",
            (
                tuple(item.mention_ref for item in mention_items),
                tuple(item.candidate_ref for item in candidate_items),
                tuple(item.constraint_ref for item in constraint_items),
            ),
            24,
        )
        return GroundingResult(
            grounding_ref=grounding_ref,
            mentions=mention_items,
            candidates=tuple(sorted(candidate_items, key=lambda item: item.candidate_ref)),
            assignments=assignments,
            selected_assignment_ref=selected,
            unresolved_mention_refs=unresolved,
            ambiguous_mention_refs=ambiguous_mentions,
            frontier_refs=frontier,
            evidence_refs=tuple(sorted(
                set(evidence_refs)
                | {ref for item in mention_items for ref in item.evidence_refs}
                | {ref for item in constraint_items for ref in item.evidence_refs}
                | {
                    ref
                    for item in candidate_items
                    for factor in item.factors
                    for ref in factor.evidence_refs
                }
            )),
            metadata={
                "beam_width": self.beam_width,
                "maximum_assignments": self.maximum_assignments,
                "ambiguity_margin": self.ambiguity_margin,
                "preserved_ambiguity": bool(ambiguous_mentions or (assignments and selected is None)),
                "provisional_frontier_only": bool(
                    assignments
                    and selected is None
                    and frontier
                    and all(
                        candidate_by_ref[ref].provisional
                        for ref in assignments[0].candidate_refs
                    )
                ),
            },
        )

    def _constraints(
        self,
        chosen: tuple[GroundingCandidate, ...],
        constraints: tuple[GroundingConstraint, ...],
        *,
        complete: bool,
    ) -> tuple[tuple[str, ...], tuple[str, ...], float] | None:
        selected = {item.mention_ref: item for item in chosen}
        satisfied = []
        optional = []
        cross_score = 0.0
        for constraint in constraints:
            relevant = [selected.get(ref) for ref in constraint.mention_refs]
            known = [item for item in relevant if item is not None]
            if len(known) < len(relevant):
                if complete and constraint.required:
                    return None
                continue
            ok = self._constraint_satisfied(constraint, tuple(known))
            if ok:
                satisfied.append(constraint.constraint_ref)
                if constraint.constraint_kind == GroundingConstraintKind.COREFER:
                    cross_score += 1.5
                elif constraint.constraint_kind == GroundingConstraintKind.DISTINCT:
                    cross_score += 0.35
                elif constraint.constraint_kind == GroundingConstraintKind.PORT_COMPATIBLE:
                    cross_score += 0.75
            elif constraint.required:
                return None
            else:
                optional.append(constraint.constraint_ref)
                cross_score -= 0.5
        return tuple(sorted(satisfied)), tuple(sorted(optional)), cross_score

    @staticmethod
    def _constraint_satisfied(
        constraint: GroundingConstraint, candidates: tuple[GroundingCandidate, ...]
    ) -> bool:
        kind = constraint.constraint_kind
        if kind == GroundingConstraintKind.COREFER:
            return len({item.target_ref for item in candidates}) == 1
        if kind == GroundingConstraintKind.DISTINCT:
            return len({item.target_ref for item in candidates}) == len(candidates)
        if kind == GroundingConstraintKind.SAME_CONTEXT:
            common = set(candidates[0].context_refs)
            for item in candidates[1:]:
                common.intersection_update(item.context_refs)
            return bool(common)
        if kind == GroundingConstraintKind.PORT_COMPATIBLE:
            contracts = tuple(constraint.metadata.get("port_contracts", ()))
            if not contracts:
                return False
            for item in candidates:
                compatible = False
                for contract in contracts:
                    accepted_types = set(map(str, contract.get("accepted_type_refs", ())))
                    accepted_storage = set(map(str, contract.get("accepted_storage_kinds", ())))
                    if accepted_types and not accepted_types.intersection(item.type_refs):
                        continue
                    if accepted_storage and item.storage_kind.value not in accepted_storage:
                        continue
                    compatible = True
                    break
                if not compatible:
                    return False
            return True
        if kind == GroundingConstraintKind.TYPE_COMPATIBLE:
            expected = set(map(str, constraint.metadata.get("type_refs", ())))
            return not expected or all(expected.intersection(item.type_refs) for item in candidates)
        if kind == GroundingConstraintKind.STORAGE_COMPATIBLE:
            expected = set(map(str, constraint.metadata.get("storage_kinds", ())))
            return not expected or all(item.storage_kind.value in expected for item in candidates)
        return True

    def _ambiguous_mentions(
        self, assignments: tuple[GroundingAssignment, ...]
    ) -> tuple[str, ...]:
        if len(assignments) < 2:
            return ()
        best = assignments[0]
        alternatives = tuple(
            item for item in assignments[1:]
            if best.score - item.score <= self.ambiguity_margin
        )
        if not alternatives:
            return ()
        best_map = dict(best.mention_to_target)
        ambiguous = set()
        for alternative in alternatives:
            other = dict(alternative.mention_to_target)
            for mention_ref, target_ref in best_map.items():
                if other.get(mention_ref) != target_ref:
                    ambiguous.add(mention_ref)
        return tuple(sorted(ambiguous))

    @staticmethod
    def _assignment(partial: _Partial) -> GroundingAssignment:
        mapping = tuple(sorted((item.mention_ref, item.target_ref) for item in partial.chosen))
        refs = tuple(sorted(item.candidate_ref for item in partial.chosen))
        factor_refs = tuple(sorted({factor.factor_ref for item in partial.chosen for factor in item.factors}))
        return GroundingAssignment(
            assignment_ref="grounding-assignment:" + semantic_fingerprint(
                "grounding-assignment-ref", (mapping, refs), 24
            ),
            candidate_refs=refs,
            mention_to_target=mapping,
            score=partial.score,
            factor_refs=factor_refs,
            satisfied_constraint_refs=partial.satisfied,
            violated_optional_constraint_refs=partial.optional_violations,
        )

    @staticmethod
    def _partial_sort_key(item: _Partial):
        return (-item.score, tuple((candidate.mention_ref, candidate.target_ref) for candidate in item.chosen))
