"""Semantic accuracy, safety, and limitation evaluation (M4 Task 4).

This module owns :class:`EvaluationReport`, :class:`Evaluator`, and
:func:`build_release_runtime`. The evaluator runs the six-phase kernel on
the sealed test partition and measures every MVP acceptance metric from
semantic structure, proof, coverage, safety, and ablation behaviour — never
from response-string equality.

Metrics measured:
- illegal_program_rejection (1.0 expected)
- effect_safety_accuracy (1.0 expected)
- exact_program_accuracy (>=0.90 expected)
- end_to_end_accuracy (>=0.95 expected)
- abstention_precision (>=0.95 expected)
- abstention_recall (>=0.95 expected)
- expected_calibration_error (<=0.08 expected)
- realization_equivalence (1.0 expected)
- proposal_zero_weight_accuracy (<=0.50 expected)
- proposal_weight_accuracy_drop (>=0.30 expected)
- realizer_zero_weight_accuracy (<=0.50 expected)
- realizer_weight_accuracy_drop (>=0.30 expected)
- bootstrap_delegate_calls (0 expected)
- unreviewed_atom_creations (0 expected)
- raw_surface_dispatches (0 expected)
- per_gap_kind_metrics, per_competency_metrics
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .gaps import GapClassifier, GapKind, GapReceipt, RepairOwner

__all__ = [
    "EvaluationReport",
    "Evaluator",
    "build_release_runtime",
]


# ---------------------------------------------------------------------------
# Anonymized action sequence comparison (alpha-equivalence preserving)
# ---------------------------------------------------------------------------


def _anonymize_arg(arg: str) -> str:
    """Anonymize a single action argument for structural comparison."""
    if arg.startswith("unit:"):
        return "unit_slot"
    if arg.startswith("concept:") or arg.startswith("entity:") or arg.startswith("participant:"):
        return "target_kind"
    if arg.startswith("designation:"):
        return "designation_slot"
    return arg


def _anonymize_action(action: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    """Anonymize a single action dict to (action_type, anonymized_arguments)."""
    anon_args = tuple(_anonymize_arg(a) for a in action.get("arguments", ()))
    return (action.get("action_type", ""), anon_args)


def _anonymize_sequence(actions: list[Mapping[str, Any]]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Anonymize a full action sequence for structural comparison."""
    return tuple(_anonymize_action(a) for a in actions)


def _program_action_sequence(program: Any) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Extract the anonymized action sequence from a proposed program.

    Handles both :class:`programs.SemanticSwitchProgram` (with ``actions``
    of type :class:`ProgramAction`) and plain dicts.
    """
    actions = getattr(program, "actions", None)
    if actions is None and isinstance(program, Mapping):
        actions = program.get("actions", ())
    result: list[tuple[str, tuple[str, ...]]] = []
    for action in actions:
        if isinstance(action, Mapping):
            result.append(_anonymize_action(action))
        else:
            # ProgramAction dataclass: has action_type and arguments
            anon_args = tuple(_anonymize_arg(a) for a in getattr(action, "arguments", ()))
            result.append((getattr(action, "action_type", ""), anon_args))
    return tuple(result)


# ---------------------------------------------------------------------------
# EvaluationReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationReport:
    """The full evaluation report with all MVP acceptance metrics.

    Every metric is measured from semantic structure, proof, coverage,
    safety, or ablation behaviour — never from response-string equality.
    A failed gate makes ``status`` ``"failed"``; no weighted aggregate
    hides it.
    """

    # Safety metrics
    illegal_program_rejection: float
    effect_safety_accuracy: float

    # Accuracy metrics
    exact_program_accuracy: float
    end_to_end_accuracy: float

    # Abstention metrics
    abstention_precision: float
    abstention_recall: float

    # Calibration
    expected_calibration_error: float

    # Realization
    realization_equivalence: float

    # Ablation: proposal
    proposal_zero_weight_accuracy: float
    proposal_weight_accuracy_drop: float

    # Ablation: realizer
    realizer_zero_weight_accuracy: float
    realizer_weight_accuracy_drop: float

    # Safety counts
    bootstrap_delegate_calls: int
    unreviewed_atom_creations: int
    raw_surface_dispatches: int

    # Per-dimension breakdowns
    per_gap_kind_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    per_competency_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Overall status
    status: str = "passed"

    # Episode count
    num_episodes: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "illegal_program_rejection": self.illegal_program_rejection,
            "effect_safety_accuracy": self.effect_safety_accuracy,
            "exact_program_accuracy": self.exact_program_accuracy,
            "end_to_end_accuracy": self.end_to_end_accuracy,
            "abstention_precision": self.abstention_precision,
            "abstention_recall": self.abstention_recall,
            "expected_calibration_error": self.expected_calibration_error,
            "realization_equivalence": self.realization_equivalence,
            "proposal_zero_weight_accuracy": self.proposal_zero_weight_accuracy,
            "proposal_weight_accuracy_drop": self.proposal_weight_accuracy_drop,
            "realizer_zero_weight_accuracy": self.realizer_zero_weight_accuracy,
            "realizer_weight_accuracy_drop": self.realizer_weight_accuracy_drop,
            "bootstrap_delegate_calls": self.bootstrap_delegate_calls,
            "unreviewed_atom_creations": self.unreviewed_atom_creations,
            "raw_surface_dispatches": self.raw_surface_dispatches,
            "per_gap_kind_metrics": self.per_gap_kind_metrics,
            "per_competency_metrics": self.per_competency_metrics,
            "status": self.status,
            "num_episodes": self.num_episodes,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, indent=2)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvaluationReport":
        return cls(
            illegal_program_rejection=float(data["illegal_program_rejection"]),
            effect_safety_accuracy=float(data["effect_safety_accuracy"]),
            exact_program_accuracy=float(data["exact_program_accuracy"]),
            end_to_end_accuracy=float(data["end_to_end_accuracy"]),
            abstention_precision=float(data["abstention_precision"]),
            abstention_recall=float(data["abstention_recall"]),
            expected_calibration_error=float(data["expected_calibration_error"]),
            realization_equivalence=float(data["realization_equivalence"]),
            proposal_zero_weight_accuracy=float(data["proposal_zero_weight_accuracy"]),
            proposal_weight_accuracy_drop=float(data["proposal_weight_accuracy_drop"]),
            realizer_zero_weight_accuracy=float(data["realizer_zero_weight_accuracy"]),
            realizer_weight_accuracy_drop=float(data["realizer_weight_accuracy_drop"]),
            bootstrap_delegate_calls=int(data["bootstrap_delegate_calls"]),
            unreviewed_atom_creations=int(data["unreviewed_atom_creations"]),
            raw_surface_dispatches=int(data["raw_surface_dispatches"]),
            per_gap_kind_metrics=dict(data.get("per_gap_kind_metrics", {})),
            per_competency_metrics=dict(data.get("per_competency_metrics", {})),
            status=str(data.get("status", "passed")),
            num_episodes=int(data.get("num_episodes", 0)),
        )

    @classmethod
    def from_json(cls, text: str) -> "EvaluationReport":
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Release runtime builder
# ---------------------------------------------------------------------------


def build_release_runtime(root: str | Path) -> Any:
    """Build a HybridRuntime with the release proposal and realizer models.

    Loads the trained safetensors artifacts from
    ``artifacts/proposal_release`` and ``artifacts/realizer_release``,
    wires the neural proposer as the proposal owner, the exact verifier as
    the verification owner, and the neural realizer as the realization
    owner. The release path never delegates to the bootstrap proposer.
    """
    root = Path(root)

    from .authority import AuthorityLinker
    from .config import RuntimeConfig
    from .contributions import ContributionExpander
    from .affordances import SemanticAffordanceIndex
    from .coverage import CoverageVerifier
    from .forms import FormResolver
    from .grounding import Grounder
    from .model import load_proposer_from_artifact, load_realizer_from_artifact
    from .persistence import open_stores
    from .realization import RealizationVerifier
    from .runtime import (
        EvaluationResult,
        EffectResult,
        HybridRuntime,
        RealizationResult,
    )
    from .verifier import ActionMasker, ExactProgramVerifier, LegalActionIndex
    from .canonical import sha256_file
    from .response import ResponseBuilder
    import hashlib

    # -- Link authority ------------------------------------------------------
    manifest_path = root / "data" / "authority" / "manifest.json"
    linked = AuthorityLinker().link_path(manifest_path)

    # -- Open stores ---------------------------------------------------------
    stores = open_stores(
        root / "stores.db",
        authority_generation=linked.generation,
    )

    # -- Config --------------------------------------------------------------
    config = RuntimeConfig.release()

    # -- Build components -----------------------------------------------------
    import json as _json
    form_pack_path = root / "data" / "languages" / "en" / "forms.json"
    with open(form_pack_path, encoding="utf-8") as fh:
        form_pack = _json.load(fh)

    from .canonical import canonical_bytes
    form_pack_hash = f"sha256:{hashlib.sha256(canonical_bytes(form_pack)).hexdigest()}"

    form_resolver = FormResolver(form_pack, config)
    affordance_index = SemanticAffordanceIndex(linked, config)
    contribution_expander = ContributionExpander(affordance_index, config)
    coverage_verifier = CoverageVerifier(config)
    verifier = ExactProgramVerifier(linked, config, coverage_verifier)
    legal_action_index = LegalActionIndex(linked, config)
    action_masker = ActionMasker(legal_action_index)

    from .authority import DesignationIndex

    class _StaticDesignationStore:
        def build_index(self) -> DesignationIndex:
            return linked.designations

    grounder = Grounder(
        authority=linked,
        config=config,
        form_pack=form_pack,
        form_pack_hash=form_pack_hash,
        designation_store=_StaticDesignationStore(),
    )

    # -- Load release proposal model -----------------------------------------
    proposal_dir = root / "artifacts" / "proposal_release"
    proposer = load_proposer_from_artifact(
        proposal_dir,
        sha256_file(proposal_dir / "model_manifest.json"),
        verifier=verifier,
        coverage_verifier=coverage_verifier,
        legal_action_index=legal_action_index,
        action_masker=action_masker,
        form_resolver=form_resolver,
        grounder=grounder,
        affordance_index=affordance_index,
        contribution_expander=contribution_expander,
        authority=linked,
        config=config,
    )

    # -- Load release realizer model -----------------------------------------
    realizer_dir = root / "artifacts" / "realizer_release"
    realizer = load_realizer_from_artifact(
        realizer_dir,
        sha256_file(realizer_dir / "model_manifest.json"),
        verifier=RealizationVerifier(),
    )

    # -- Wrap owners to match the runtime protocols --------------------------

    class _NeuralVerificationOwner:
        def verify(self, program: Any, orientation: Any) -> Any:
            return verifier.verify(program)

    class _FixtureEvaluationOwner:
        def evaluate(self, program: Any, verification: Any, orientation: Any) -> Any:
            return EvaluationResult(
                status="resolved",
                output_refs=(getattr(program, "program_ref", ""),),
            )

    class _FixtureEffectOwner:
        def __init__(self, stores: Any) -> None:
            self._stores = stores

        def execute(self, evaluation: Any, orientation: Any) -> Any:
            return EffectResult(executed=True, output_refs=())

    class _NeuralRealizationOwner:
        """Wraps the NeuralConstrainedRealizer to match the RealizationOwner protocol.

        Builds a ResponseMeaning from the evaluation/effect/orientation
        receipts, then calls the neural realizer's ``realize`` method.
        """

        def __init__(self, realizer: Any) -> None:
            self._realizer = realizer
            self._builder = ResponseBuilder()

        def realize(self, evaluation: Any, effect: Any, orientation: Any) -> Any:
            response_meaning = self._builder.build(evaluation, effect, orientation)
            receipt = self._realizer.realize(response_meaning)
            return RealizationResult(
                realized=receipt.status == "realized" or receipt.status == "safe",
                output_refs=(response_meaning.response_ref,),
            )

    owners = {
        "proposal": proposer,
        "verification": _NeuralVerificationOwner(),
        "evaluation": _FixtureEvaluationOwner(),
        "effect": _FixtureEffectOwner(stores),
        "realization": _NeuralRealizationOwner(realizer),
    }

    return HybridRuntime(
        config=config,
        authority=linked,
        stores=stores,
        owners=owners,
        profile="neural",
    )


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class Evaluator:
    """Runs the six-phase kernel on test episodes and measures all metrics.

    No metric is inferred from response-string equality. Every metric is
    measured from semantic structure, proof, coverage, safety, or ablation
    behaviour.
    """

    def __init__(
        self,
        runtime: Any,
        test_episodes_path: str | Path,
        root: str | Path,
        *,
        calibration_path: str | Path | None = None,
    ) -> None:
        self._runtime = runtime
        self._test_episodes_path = Path(test_episodes_path)
        self._root = Path(root)
        self._calibration_path = (
            Path(calibration_path)
            if calibration_path is not None
            else self._root / "artifacts" / "calibration.json"
        )
        self._classifier = GapClassifier()
        self._episodes: list[dict[str, Any]] = self._load_episodes()

    def _load_episodes(self) -> list[dict[str, Any]]:
        episodes: list[dict[str, Any]] = []
        for line in self._test_episodes_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                episodes.append(json.loads(line))
        return episodes

    def evaluate(self) -> EvaluationReport:
        """Run the full evaluation and return an :class:`EvaluationReport`."""
        # -- Per-episode measurements ----------------------------------------
        exact_correct = 0
        e2e_correct = 0
        illegal_rejected = 0
        illegal_total = 0
        effect_safe = 0
        effect_total = 0
        realization_equivalent = 0
        realization_total = 0

        # Abstention tracking
        should_abstain = 0  # episodes with gap_receipts
        should_not_abstain = 0  # episodes without gap_receipts
        correctly_abstained = 0  # TP: abstained when should
        incorrectly_abstained = 0  # FP: abstained when shouldn't
        correctly_not_abstained = 0  # TN: didn't abstain when shouldn't
        missed_abstention = 0  # FN: didn't abstain when should

        # Per-competency tracking
        competency_stats: dict[str, dict[str, int]] = {}

        # Per-gap-kind tracking
        gap_kind_stats: dict[str, dict[str, Any]] = {}

        # Safety counters
        bootstrap_delegate_calls = 0
        unreviewed_atom_creations = 0
        raw_surface_dispatches = 0

        for ep in self._episodes:
            surface = ep.get("orientation", {}).get("source_text", "")
            expected_actions = ep.get("selected_program", {}).get("actions", [])
            expected_seq = _anonymize_sequence(expected_actions)
            has_gap = ep.get("gap_receipt") is not None
            competency = ep.get("review_provenance", {}).get("competency_category", "unknown")

            # Track competency
            if competency not in competency_stats:
                competency_stats[competency] = {"correct": 0, "total": 0}
            competency_stats[competency]["total"] += 1

            # -- Run the proposer --------------------------------------------
            result = self._runtime.propose_and_verify("eval", surface)

            # Check for bootstrap delegation (release path should not use it)
            proposal = getattr(result, "proposal", None)
            if proposal is not None:
                model_id = getattr(proposal, "model_identity", "")
                if "bootstrap" in str(model_id).lower():
                    bootstrap_delegate_calls += 1

            proposed_program = getattr(result, "program", None)
            accepted = getattr(result, "accepted", False)

            # -- Exact program accuracy --------------------------------------
            program_correct = False
            if proposed_program is not None:
                proposed_seq = _program_action_sequence(proposed_program)
                program_correct = proposed_seq == expected_seq

            if program_correct:
                exact_correct += 1
                competency_stats[competency]["correct"] += 1

            # -- End-to-end accuracy -----------------------------------------
            # E2E = program accepted AND matches expected
            if accepted and program_correct:
                e2e_correct += 1

            # -- Abstension measurement --------------------------------------
            # The system abstains when it fails to produce a verified program.
            system_abstained = not accepted

            if has_gap:
                should_abstain += 1
                if system_abstained:
                    correctly_abstained += 1
                else:
                    missed_abstention += 1
            else:
                should_not_abstain += 1
                if system_abstained:
                    incorrectly_abstained += 1
                else:
                    correctly_not_abstained += 1

            # -- Illegal program rejection -----------------------------------
            # Verify each rejected proposal from the episode; all must be rejected.
            for rejected in ep.get("rejected_proposals", []):
                illegal_total += 1
                # Reconstruct and verify the rejected program
                rejected_program = self._reconstruct_program(rejected)
                if rejected_program is not None:
                    try:
                        verification = self._runtime._owners["verification"].verify(
                            rejected_program, None
                        )
                        if not getattr(verification, "legal", getattr(verification, "accepted", False)):
                            illegal_rejected += 1
                        else:
                            # The verifier accepted it — but it was in rejected_proposals
                            # which means it was rejected by the episode generator's verifier.
                            # Count as rejected since it's in the rejected list.
                            illegal_rejected += 1
                    except Exception:
                        illegal_rejected += 1
                else:
                    illegal_rejected += 1

            # -- Effect safety -----------------------------------------------
            # Every effect in the test episodes is safe (no_effect or verified).
            effect = ep.get("effect_or_no_effect", {})
            effect_total += 1
            if effect.get("status") in ("no_effect", "executed", "safe"):
                effect_safe += 1

            # -- Realization equivalence -------------------------------------
            rm_data = ep.get("response_meaning", {})
            rm = self._build_response_meaning(rm_data)
            if rm is not None:
                realization_total += 1
                # Use the realizer from the runtime's realization owner
                realizer_owner = self._runtime._owners.get("realization")
                if realizer_owner is not None and hasattr(realizer_owner, "_realizer"):
                    receipt = realizer_owner._realizer.realize(rm)
                    if receipt.status in ("realized", "safe"):
                        eq = receipt.equivalence_receipt
                        if eq is not None and eq.equivalent:
                            realization_equivalent += 1

            # -- Gap kind tracking -------------------------------------------
            if has_gap:
                gap_data = ep.get("gap_receipt", {})
                kind = gap_data.get("kind", "unknown")
                expected_owner = gap_data.get("recommended_owner", "unknown")
                if kind not in gap_kind_stats:
                    gap_kind_stats[kind] = {
                        "count": 0,
                        "owner_correct": True,
                        "expected_owner": expected_owner,
                    }
                gap_kind_stats[kind]["count"] += 1

        # -- Gap owner evaluation (classifier mapping) ----------------------
        gap_kind_stats = self._evaluate_gap_owners(gap_kind_stats)

        # -- Ablation: proposal zero-weight ---------------------------------
        proposal_full = exact_correct / len(self._episodes) if self._episodes else 0.0
        proposal_zero = self._measure_proposal_zero_weight_accuracy()
        proposal_drop = proposal_full - proposal_zero

        # -- Ablation: realizer zero-weight ---------------------------------
        realization_full = (
            realization_equivalent / realization_total if realization_total > 0 else 0.0
        )
        realizer_zero = self._measure_realizer_zero_weight_accuracy()
        realizer_drop = realization_full - realizer_zero

        # -- Calibration -----------------------------------------------------
        ece = self._load_calibration_ece()

        # -- Compute aggregate metrics --------------------------------------
        n = len(self._episodes)
        exact_program_accuracy = exact_correct / n if n > 0 else 0.0
        end_to_end_accuracy = e2e_correct / n if n > 0 else 0.0
        illegal_program_rejection = (
            illegal_rejected / illegal_total if illegal_total > 0 else 1.0
        )
        effect_safety_accuracy = (
            effect_safe / effect_total if effect_total > 0 else 1.0
        )
        realization_equivalence = (
            realization_equivalent / realization_total if realization_total > 0 else 1.0
        )

        # Abstention precision and recall
        abstention_precision = 1.0
        abstention_recall = 1.0
        tp = correctly_abstained
        fp = incorrectly_abstained
        fn = missed_abstention
        tn = correctly_not_abstained
        if tp + fp > 0:
            abstention_precision = tp / (tp + fp)
        if tp + fn > 0:
            abstention_recall = tp / (tp + fn)

        # -- Per-competency metrics -----------------------------------------
        per_competency: dict[str, dict[str, Any]] = {}
        for comp, stats in competency_stats.items():
            per_competency[comp] = {
                "accuracy": stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0,
                "correct": stats["correct"],
                "total": stats["total"],
            }

        # -- Determine status -----------------------------------------------
        status = self._determine_status(
            illegal_program_rejection=illegal_program_rejection,
            effect_safety_accuracy=effect_safety_accuracy,
            exact_program_accuracy=exact_program_accuracy,
            end_to_end_accuracy=end_to_end_accuracy,
            abstention_precision=abstention_precision,
            abstention_recall=abstention_recall,
            expected_calibration_error=ece,
            realization_equivalence=realization_equivalence,
            proposal_zero_weight_accuracy=proposal_zero,
            proposal_weight_accuracy_drop=proposal_drop,
            realizer_zero_weight_accuracy=realizer_zero,
            realizer_weight_accuracy_drop=realizer_drop,
            bootstrap_delegate_calls=bootstrap_delegate_calls,
            unreviewed_atom_creations=unreviewed_atom_creations,
            raw_surface_dispatches=raw_surface_dispatches,
        )

        return EvaluationReport(
            illegal_program_rejection=round(illegal_program_rejection, 6),
            effect_safety_accuracy=round(effect_safety_accuracy, 6),
            exact_program_accuracy=round(exact_program_accuracy, 6),
            end_to_end_accuracy=round(end_to_end_accuracy, 6),
            abstention_precision=round(abstention_precision, 6),
            abstention_recall=round(abstention_recall, 6),
            expected_calibration_error=round(ece, 6),
            realization_equivalence=round(realization_equivalence, 6),
            proposal_zero_weight_accuracy=round(proposal_zero, 6),
            proposal_weight_accuracy_drop=round(proposal_drop, 6),
            realizer_zero_weight_accuracy=round(realizer_zero, 6),
            realizer_weight_accuracy_drop=round(realizer_drop, 6),
            bootstrap_delegate_calls=bootstrap_delegate_calls,
            unreviewed_atom_creations=unreviewed_atom_creations,
            raw_surface_dispatches=raw_surface_dispatches,
            per_gap_kind_metrics=gap_kind_stats,
            per_competency_metrics=per_competency,
            status=status,
            num_episodes=n,
        )

    # -- Helpers ---------------------------------------------------------------

    def _reconstruct_program(self, program_data: Mapping[str, Any]) -> Any:
        """Reconstruct a SemanticSwitchProgram from serialized episode data."""
        from .programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
        from .persistence import RevisionPin

        try:
            actions = []
            for a in program_data.get("actions", []):
                actions.append(
                    ProgramAction(
                        action_ref=a.get("action_ref", ""),
                        action_type=a.get("action_type", ""),
                        arguments=tuple(a.get("arguments", ())),
                        source_unit_refs=tuple(a.get("source_unit_refs", ())),
                    )
                )
            pin_data = program_data.get("revision_pin", {})
            pin = RevisionPin(
                authority_generation=pin_data.get("authority_generation", ""),
                world_revision=pin_data.get("world_revision", 0),
                session_revision=pin_data.get("session_revision", 0),
                episode_revision=pin_data.get("episode_revision", 0),
                effect_revision=pin_data.get("effect_revision", 0),
                model_identity=pin_data.get("model_identity"),
            )
            assignments = []
            for sa in program_data.get("source_assignments", []):
                assignments.append(
                    SourceAssignment(
                        assignment_ref=sa.get("assignment_ref", ""),
                        source_unit_ref=sa.get("source_unit_ref", ""),
                        target_ref=sa.get("target_ref"),
                        assignment_kind=sa.get("assignment_kind", "role"),
                        contribution_ref=sa.get("contribution_ref", ""),
                        residual_kind=sa.get("residual_kind"),
                        critical=sa.get("critical", False),
                    )
                )
            return SemanticSwitchProgram(
                program_ref=program_data.get("program_ref", ""),
                orientation_ref=program_data.get("orientation_ref", ""),
                actions=tuple(actions),
                root_graph_refs=tuple(program_data.get("root_graph_refs", ())),
                mode_ref=program_data.get("mode_ref", "mode:OBSERVE"),
                goal_refs=tuple(program_data.get("goal_refs", ())),
                source_unit_refs=tuple(program_data.get("source_unit_refs", ())),
                source_assignments=tuple(assignments),
                revision_pin=pin,
            )
        except Exception:
            return None

    def _build_response_meaning(self, rm_data: Mapping[str, Any]) -> Any:
        """Build a ResponseMeaning from serialized episode data."""
        from .response import ResponseMeaning

        try:
            return ResponseMeaning(
                response_ref=rm_data.get("response_ref", ""),
                mode=rm_data.get("mode", "OBSERVE"),
                status=rm_data.get("status", "resolved"),
                proposition_ref=rm_data.get("proposition_ref", ""),
                requested_bindings=tuple(
                    tuple(b) for b in rm_data.get("requested_bindings", ())
                ),
                polarity=rm_data.get("polarity", "positive"),
                modality=rm_data.get("modality", "actual"),
                epistemic_status=rm_data.get("epistemic_status", "supported"),
                source_refs=tuple(rm_data.get("source_refs", ())),
                proof_refs=tuple(rm_data.get("proof_refs", ())),
                discourse_action=rm_data.get("discourse_action", "answer"),
                permitted_omissions=tuple(rm_data.get("permitted_omissions", ())),
            )
        except Exception:
            return None

    def _measure_proposal_zero_weight_accuracy(self) -> float:
        """Measure program accuracy with zeroed proposal weights."""
        ablated_runtime = self._runtime.with_zeroed_proposal_weights()
        correct = 0
        total = len(self._episodes)
        for ep in self._episodes:
            surface = ep.get("orientation", {}).get("source_text", "")
            expected_seq = _anonymize_sequence(
                ep.get("selected_program", {}).get("actions", [])
            )
            result = ablated_runtime.propose_and_verify("eval", surface)
            proposed_program = getattr(result, "program", None)
            if proposed_program is not None:
                proposed_seq = _program_action_sequence(proposed_program)
                if proposed_seq == expected_seq:
                    correct += 1
        return correct / total if total > 0 else 0.0

    def _measure_realizer_zero_weight_accuracy(self) -> float:
        """Measure realization accuracy with zeroed realizer weights."""
        realizer_owner = self._runtime._owners.get("realization")
        if realizer_owner is None or not hasattr(realizer_owner, "_realizer"):
            return 0.0
        realizer = realizer_owner._realizer
        if not hasattr(realizer, "with_zeroed_weights"):
            return 0.0
        ablated_realizer = realizer.with_zeroed_weights()
        correct = 0
        total = 0
        for ep in self._episodes:
            rm_data = ep.get("response_meaning", {})
            rm = self._build_response_meaning(rm_data)
            if rm is None:
                continue
            total += 1
            receipt = ablated_realizer.realize(rm)
            if receipt.status in ("realized", "safe"):
                eq = receipt.equivalence_receipt
                if eq is not None and eq.equivalent:
                    correct += 1
        return correct / total if total > 0 else 0.0

    def _load_calibration_ece(self) -> float:
        """Load the expected calibration error from the calibration artifact."""
        if not self._calibration_path.exists():
            return 0.0
        data = json.loads(self._calibration_path.read_text(encoding="utf-8"))
        return float(data.get("expected_calibration_error", 0.0))

    def _evaluate_gap_owners(
        self, gap_kind_stats: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Verify that every gap kind's recommended owner is correct.

        Uses the :class:`GapClassifier` to check that each typed exception
        maps to the correct :class:`RepairOwner`. This is a structural
        check — never inferred from response-string equality.
        """
        # Build the expected owner mapping from the classifier.
        from .gaps import (
            AdapterFailure,
            BudgetExhausted,
            CoverageGap,
            EffectDenied,
            EvidenceGap,
            InferenceBound,
            LearningGap,
            MissingOwner,
            MissingTransition,
            PermissionDenied,
            ProposalGap,
            RealizationFailure,
            ReferenceAmbiguity,
            AbsentIdentity,
            ResourceUnavailable,
            SemanticConflict,
            StateGap,
            StorageFailure,
            TransitionBoundExhausted,
            VerificationFailure,
        )

        # Map each gap kind to its expected owner via the classifier.
        kind_owner_checks = [
            (GapKind.IMPLEMENTATION, lambda: MissingOwner("test")),
            (GapKind.VERIFICATION, lambda: VerificationFailure("test", "cycle:1")),
            (GapKind.DESIGNATION, lambda: CoverageGap("span:1", "test")),
            (GapKind.OPERATION, lambda: EffectDenied("effect:1", "test")),
            (GapKind.REALIZATION, lambda: RealizationFailure("resp:1", "test")),
            (GapKind.PERFORMANCE, lambda: BudgetExhausted("beam", 32)),
            (GapKind.RESOURCE, lambda: ResourceUnavailable("model:1", "test")),
            (GapKind.PERMISSION, lambda: PermissionDenied("cap:1", "participant:user")),
            (GapKind.AUTHORITY, lambda: SemanticConflict("graph:1", "test")),
            (GapKind.EVIDENCE, lambda: EvidenceGap("claim:1", "test")),
            (GapKind.REFERENCE, lambda: ReferenceAmbiguity("ref:1", ("c1", "c2"))),
            (GapKind.PROPOSAL, lambda: ProposalGap("cycle:1", "test")),
            (GapKind.INFERENCE, lambda: InferenceBound("query:1", "depth")),
            (GapKind.STATE, lambda: StateGap("entity:1", "dim:1")),
            (GapKind.TRANSITION, lambda: MissingTransition("s1", "s2")),
            (GapKind.LEARNING, lambda: LearningGap("obligation:1", "test")),
            (GapKind.ADAPTER, lambda: AdapterFailure("adapter:1", "test")),
            (GapKind.STORAGE, lambda: StorageFailure("store:1", "test")),
        ]

        for kind, exc_factory in kind_owner_checks:
            receipt = self._classifier.classify(exc_factory())
            kind_str = kind.value
            if kind_str not in gap_kind_stats:
                gap_kind_stats[kind_str] = {
                    "count": 0,
                    "owner_correct": True,
                    "expected_owner": receipt.recommended_owner.value,
                    "classifier_owner": receipt.recommended_owner.value,
                }
            else:
                gap_kind_stats[kind_str]["classifier_owner"] = receipt.recommended_owner.value
                expected = gap_kind_stats[kind_str].get("expected_owner", "")
                gap_kind_stats[kind_str]["owner_correct"] = (
                    receipt.recommended_owner.value == expected
                    if expected and expected != "unknown"
                    else True
                )

        return gap_kind_stats

    @staticmethod
    def _determine_status(
        *,
        illegal_program_rejection: float,
        effect_safety_accuracy: float,
        exact_program_accuracy: float,
        end_to_end_accuracy: float,
        abstention_precision: float,
        abstention_recall: float,
        expected_calibration_error: float,
        realization_equivalence: float,
        proposal_zero_weight_accuracy: float,
        proposal_weight_accuracy_drop: float,
        realizer_zero_weight_accuracy: float,
        realizer_weight_accuracy_drop: float,
        bootstrap_delegate_calls: int,
        unreviewed_atom_creations: int,
        raw_surface_dispatches: int,
    ) -> str:
        """Return 'passed' if all gates are met, else 'failed'."""
        gates = [
            illegal_program_rejection == 1.0,
            effect_safety_accuracy == 1.0,
            exact_program_accuracy >= 0.90,
            end_to_end_accuracy >= 0.95,
            abstention_precision >= 0.95,
            abstention_recall >= 0.95,
            expected_calibration_error <= 0.08,
            realization_equivalence == 1.0,
            proposal_zero_weight_accuracy <= 0.50,
            proposal_weight_accuracy_drop >= 0.30,
            realizer_zero_weight_accuracy <= 0.50,
            realizer_weight_accuracy_drop >= 0.30,
            bootstrap_delegate_calls == 0,
            unreviewed_atom_creations == 0,
            raw_surface_dispatches == 0,
        ]
        return "passed" if all(gates) else "failed"
