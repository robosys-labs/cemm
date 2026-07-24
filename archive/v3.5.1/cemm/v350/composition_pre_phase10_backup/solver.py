"""Bounded deterministic factor-graph solver with pruning trace."""
from __future__ import annotations

from dataclasses import dataclass

from ..schema.model import semantic_fingerprint
from .model import MeaningFactor, MeaningFactorGraph, MeaningHypothesis, MeaningSolveResult, PruningTrace


@dataclass(frozen=True, slots=True)
class _Partial:
    assignments: tuple[tuple[str, str], ...]
    score: float
    satisfied: tuple[str, ...]


class MeaningFactorSolver:
    def __init__(self, *, beam_width: int = 96, maximum_hypotheses: int = 12, maximum_expansions: int = 20000) -> None:
        if min(beam_width, maximum_hypotheses, maximum_expansions) < 1:
            raise ValueError("factor solver bounds must be positive")
        self.beam_width = beam_width
        self.maximum_hypotheses = maximum_hypotheses
        self.maximum_expansions = maximum_expansions

    def solve(self, graph: MeaningFactorGraph) -> MeaningSolveResult:
        variables = tuple(sorted(graph.variables, key=lambda item: (len(item.values), item.variable_kind.value, item.variable_ref)))
        factors = tuple(graph.factors)
        factor_by_variable = {item.variable_ref: [] for item in variables}
        for factor in factors:
            for ref in factor.variable_refs:
                factor_by_variable[ref].append(factor)
        trace: list[PruningTrace] = []
        beam = (_Partial((), 0.0, ()),)
        expansions = 0
        exhausted = False
        for depth, variable in enumerate(variables):
            expanded: list[_Partial] = []
            for partial in beam:
                mapping = dict(partial.assignments)
                for value in variable.values:
                    expansions += 1
                    if expansions > self.maximum_expansions:
                        exhausted = True
                        break
                    proposal = {**mapping, variable.variable_ref: value.value_ref}
                    rejected = []
                    satisfied = set(partial.satisfied)
                    soft_score = 0.0
                    for factor in factor_by_variable[variable.variable_ref]:
                        status, contribution = _evaluate_factor(factor, proposal)
                        if status is False and factor.hard:
                            rejected.append(factor.factor_ref)
                        elif status is True:
                            satisfied.add(factor.factor_ref)
                            soft_score += contribution
                    if rejected:
                        trace.append(PruningTrace(
                            trace_ref="pruning:" + semantic_fingerprint(
                                "meaning-pruning", (graph.graph_ref, variable.variable_ref, value.value_ref, tuple(sorted(rejected)), depth), 24
                            ),
                            variable_ref=variable.variable_ref,
                            value_ref=value.value_ref,
                            reason="hard factor has no compatible completion",
                            factor_refs=tuple(sorted(rejected)),
                            depth=depth,
                        ))
                        continue
                    expanded.append(_Partial(
                        assignments=tuple(sorted(proposal.items())),
                        score=partial.score + value.score + soft_score,
                        satisfied=tuple(sorted(satisfied)),
                    ))
                if exhausted:
                    break
            expanded.sort(key=lambda item: (-item.score, item.assignments))
            beam = tuple(expanded[: self.beam_width])
            if exhausted or not beam:
                break

        complete: list[MeaningHypothesis] = []
        for partial in beam:
            mapping = dict(partial.assignments)
            rejected = []
            satisfied = set(partial.satisfied)
            score = partial.score
            for factor in factors:
                status, contribution = _evaluate_factor(factor, mapping, complete=True)
                if status is False and factor.hard:
                    rejected.append(factor.factor_ref)
                elif status is True:
                    if factor.factor_ref not in satisfied:
                        score += contribution
                    satisfied.add(factor.factor_ref)
            if rejected:
                continue
            unresolved = tuple(sorted(
                set(graph.unresolved_refs)
                | {item.variable_ref for item in variables if item.variable_ref not in mapping}
            ))
            assignments = tuple(sorted(mapping.items()))
            complete.append(MeaningHypothesis(
                hypothesis_ref="meaning-hypothesis:" + semantic_fingerprint(
                    "meaning-hypothesis", (graph.graph_ref, assignments), 24
                ),
                assignments=assignments,
                score=score,
                satisfied_factor_refs=tuple(sorted(satisfied)),
                unresolved_refs=unresolved,
                evidence_refs=graph.evidence_refs,
            ))
        complete.sort(key=lambda item: (-item.score, item.assignments))
        complete = complete[: self.maximum_hypotheses]
        return MeaningSolveResult(
            solve_ref="meaning-solve:" + semantic_fingerprint(
                "meaning-solve", (graph.graph_ref, tuple(item.hypothesis_ref for item in complete), expansions, exhausted), 24
            ),
            factor_graph_ref=graph.graph_ref,
            hypotheses=tuple(complete),
            pruning_trace=tuple(trace),
            exhausted=exhausted,
            expansions=expansions,
            evidence_refs=graph.evidence_refs,
            metadata={"beam_width": self.beam_width, "maximum_hypotheses": self.maximum_hypotheses,
                      "maximum_expansions": self.maximum_expansions},
        )


def _evaluate_factor(factor: MeaningFactor, assignment: dict[str, str], *, complete: bool = False):
    known = tuple(ref for ref in factor.variable_refs if ref in assignment)
    if not known:
        return None, 0.0
    positions = {ref: index for index, ref in enumerate(factor.variable_refs)}
    compatible = []
    for allowed in factor.allowed_value_tuples:
        if all(allowed[positions[ref]] == assignment[ref] for ref in known):
            compatible.append(allowed)
    if factor.hard:
        if not compatible:
            return False, 0.0
        if len(known) < len(factor.variable_refs):
            return None, 0.0
        return True, 0.0
    if len(known) < len(factor.variable_refs):
        return None, 0.0
    current = tuple(assignment[ref] for ref in factor.variable_refs)
    score_map = dict(factor.tuple_scores)
    if factor.allowed_value_tuples and current not in factor.allowed_value_tuples:
        return False, 0.0
    return True, float(score_map.get(current, 0.0))
