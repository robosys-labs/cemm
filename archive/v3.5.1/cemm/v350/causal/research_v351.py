"""Causal structure research over the same proof/evidence substrate used by runtime QA."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log
from typing import Callable, Iterable

from ..learning.model import PinnedRecord
from ..learning.phase14_model_v351 import ExactStructuralCandidateSignal, PredictionErrorFamily
from ..schema.model import UseAuthorization, semantic_fingerprint
from ..state.model_v351 import TransitionMechanismV351
from ..storage.model import RecordKind
from .model_v351 import CausalLearningEvidenceV351


@dataclass(frozen=True, slots=True)
class MechanismHypothesisV351:
    hypothesis_ref: str
    mechanism: TransitionMechanismV351
    dependency_pins: tuple[PinnedRecord, ...]
    closure_proof_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    complexity_cost: float = 0.0

    def __post_init__(self) -> None:
        if not self.hypothesis_ref or not self.closure_proof_refs:
            raise ValueError("causal mechanism hypothesis requires identity and closure proof")
        if not isfinite(self.complexity_cost) or self.complexity_cost < 0.0:
            raise ValueError("causal mechanism complexity cost must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class CausalStructureScoreV351:
    score_ref: str
    hypothesis_ref: str
    log_evidence_score: float
    complexity_penalty: float
    intervention_support_refs: tuple[str, ...]
    counterexample_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    accepted_for_candidate: bool
    proof_refs: tuple[str, ...]


class CausalStructureResearcherV351:
    """Score explicit structural hypotheses without turning association into causation.

    `likelihood_ratio` is an independently supplied evaluator over a typed hypothesis and
    evidence item. Evidence sharing the same source lineage is clustered: the strongest
    contribution in a cluster is used rather than naively multiplying correlated signals.
    """

    def __init__(self, *, minimum_log_score: float = 0.0, complexity_weight: float = 1.0) -> None:
        if not isfinite(minimum_log_score) or not isfinite(complexity_weight) or complexity_weight < 0.0:
            raise ValueError("causal research thresholds must be finite")
        self.minimum_log_score = float(minimum_log_score)
        self.complexity_weight = float(complexity_weight)

    def score(
        self,
        hypothesis: MechanismHypothesisV351,
        evidence: Iterable[CausalLearningEvidenceV351],
        *,
        likelihood_ratio: Callable[[TransitionMechanismV351, CausalLearningEvidenceV351], float],
    ) -> CausalStructureScoreV351:
        clusters: dict[str, list[tuple[float, CausalLearningEvidenceV351]]] = {}
        interventions, mechanism_support, counterexamples, proof_refs, lineages = set(), set(), set(), set(), set()
        for item in evidence:
            ratio = float(likelihood_ratio(hypothesis.mechanism, item))
            if not isfinite(ratio) or ratio <= 0.0:
                raise ValueError("causal likelihood ratio must be finite and positive")
            contribution = log(ratio) * float(item.weight)
            lineage = item.source_lineage_refs[0] if item.source_lineage_refs else item.evidence_ref
            clusters.setdefault(lineage, []).append((contribution, item))
            lineages.update(item.source_lineage_refs)
            interventions.update(item.intervention_support_refs)
            if item.mechanism_pin.key == hypothesis.mechanism.authority_pin.key:
                mechanism_support.update(item.mechanism_support_refs)
            counterexamples.update(item.counterexample_refs)
            proof_refs.update(item.proof_step_refs)

        # Shared-lineage evidence does not count as independent repeated confirmation.
        fit = sum(max(values, key=lambda pair: abs(pair[0]))[0] for values in clusters.values())
        penalty = self.complexity_weight * hypothesis.complexity_cost
        score = fit - penalty
        # Causal admission needs either an intervention or explicit mechanistic support for
        # this exact hypothesis. Generic causal-path proof lineage is not sufficient and
        # temporal/coactivation observations cannot set mechanism_support_refs.
        accepted = bool(interventions or mechanism_support) and not counterexamples and score >= self.minimum_log_score
        return CausalStructureScoreV351(
            score_ref="causal-structure-score:" + semantic_fingerprint(
                "causal-structure-score-v351",
                (
                    hypothesis.hypothesis_ref,
                    tuple(sorted((key, tuple(round(x[0], 12) for x in values)) for key, values in clusters.items())),
                    penalty,
                    tuple(sorted(interventions)),
                    tuple(sorted(mechanism_support)),
                    tuple(sorted(counterexamples)),
                ),
                32,
            ),
            hypothesis_ref=hypothesis.hypothesis_ref,
            log_evidence_score=score,
            complexity_penalty=penalty,
            intervention_support_refs=tuple(sorted(interventions)),
            counterexample_refs=tuple(sorted(counterexamples)),
            source_lineage_refs=tuple(sorted(lineages)),
            accepted_for_candidate=accepted,
            proof_refs=tuple(sorted(proof_refs)),
        )

    def candidate_signal(
        self,
        hypothesis: MechanismHypothesisV351,
        score: CausalStructureScoreV351,
        *,
        evidence_refs: tuple[str, ...],
        competence_case_refs: tuple[str, ...],
        requested_uses: tuple[UseAuthorization, ...],
    ) -> ExactStructuralCandidateSignal:
        if score.hypothesis_ref != hypothesis.hypothesis_ref:
            raise ValueError("causal score does not target exact hypothesis")
        if not score.accepted_for_candidate:
            raise ValueError("causal hypothesis lacks intervention/mechanism-supported candidate evidence")
        return ExactStructuralCandidateSignal(
            signal_ref="causal-candidate-signal:" + semantic_fingerprint(
                "causal-candidate-signal-v351", (hypothesis.hypothesis_ref, score.score_ref), 24,
            ),
            family=PredictionErrorFamily.CAUSAL_STRUCTURE,
            record_kind=RecordKind.TRANSITION_CONTRACT,
            payload=hypothesis.mechanism,
            dependency_pins=hypothesis.dependency_pins,
            evidence_refs=tuple(sorted(set(evidence_refs))),
            source_lineage_refs=tuple(sorted(set((*hypothesis.source_lineage_refs, *score.source_lineage_refs)))),
            competence_case_refs=tuple(competence_case_refs),
            requested_uses=tuple(requested_uses),
            confidence=max(0.0, min(1.0, 1.0 - pow(2.718281828459045, -max(0.0, score.log_evidence_score)))),
            metadata={
                "dependency_closed": True,
                "closure_proof_refs": hypothesis.closure_proof_refs,
                "intervention_or_mechanism_evidence": True,
                "intervention_support_refs": score.intervention_support_refs,
                "causal_structure_score_ref": score.score_ref,
            },
        )


__all__ = [
    "CausalStructureResearcherV351", "CausalStructureScoreV351", "MechanismHypothesisV351",
]
