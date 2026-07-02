from __future__ import annotations
import json
import math
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from ..store.store import Store
from ..types.model import Model, ModelKind, ModelStatus
from ..types.claim import Claim, ClaimStatus
from ..types.signal import Signal, SignalKind, SourceType
from ..registry.registry import Registry, RegistryEntry


_SEMANTIC_INTERPRETER_WORDS_PATH = Path(__file__).parents[1] / "data" / "semantic_interpreter_words.json"


def _load_semantic_interpreter_words() -> dict:
    if not _SEMANTIC_INTERPRETER_WORDS_PATH.exists():
        return {}
    return json.loads(_SEMANTIC_INTERPRETER_WORDS_PATH.read_text(encoding="utf-8"))


class Inductor:
    def __init__(self, store: Store, feedback_threshold: int = 5, registry: Registry | None = None) -> None:
        self._store = store
        self._feedback_threshold = feedback_threshold
        self._registry = registry
        words = _load_semantic_interpreter_words()
        self._causal_connectors = list(words.get("causal_connectors", []))
        self._causal_phrase_connectors = set(words.get("causal_phrase_connectors", []))
        self._stop_words = set(words.get("stop_words", []))

    def set_threshold(self, value: int) -> None:
        self._feedback_threshold = value

    def maybe_induct(self, domain: str | None = None) -> list[Model]:
        candidates: list[Model] = []
        candidates.extend(self._find_repeated_predicates(domain))
        candidates.extend(self._find_failed_retrieval_patterns())
        candidates.extend(self._find_causal_patterns(domain))
        candidates.extend(self._find_narrative_causal_patterns(domain))
        candidates.extend(self._find_uol_patterns(domain))
        candidates.extend(self._find_sequential_patterns())
        candidates.extend(self._find_slot_completion())
        return candidates

    def _extract_causal_phrase(self, words: list[str], direction: str) -> str:
        """Naive phrase extraction: keep content words until a stop word or connector."""
        if direction == "left":
            phrase = []
            for w in reversed(words):
                if w in self._stop_words or w in self._causal_phrase_connectors:
                    break
                phrase.insert(0, w)
            return "_".join(phrase) if phrase else ""
        phrase = []
        for w in words:
            if w in self._stop_words:
                if phrase:
                    break
                continue
            phrase.append(w)
        return "_".join(phrase) if phrase else ""

    def _find_narrative_causal_patterns(self, domain: str | None = None) -> list[Model]:
        """Discover causal rules from explicit causal language in signals."""
        recent_signals = self._store.signals.recent(1000)
        counts: dict[tuple[str, str], list[Signal]] = defaultdict(list)
        for signal in recent_signals:
            if not signal.content:
                continue
            if domain and getattr(signal, "domain", None) != domain:
                continue
            content = " " + signal.content.lower().strip() + " "
            for connector in self._causal_connectors:
                if connector not in content:
                    continue
                parts = content.split(connector, 1)
                if len(parts) != 2:
                    continue
                left_words = parts[0].strip().split()
                right_words = parts[1].strip().split()
                left_phrase = self._extract_causal_phrase(left_words, "left")
                right_phrase = self._extract_causal_phrase(right_words, "right")
                if not left_phrase or not right_phrase:
                    continue
                counts[(left_phrase, right_phrase)].append(signal)

        candidates: list[Model] = []
        for (left, right), signals in counts.items():
            if len(signals) < self._feedback_threshold:
                continue
            name = f"causal:{left}->{right}"
            if self._existing_causal_rule(name, right, None):
                continue
            now = time.time()
            model = Model(
                id=uuid.uuid4().hex[:16],
                kind=ModelKind.CAUSAL_RULE,
                name=name,
                description=f"Narrative causal rule: {left} -> {right} (from {len(signals)} signals)",
                preconditions=[f"process:{left}"],
                effects=[f"process:{right}"],
                evidence_signal_ids=[s.id for s in signals],
                confidence=min(1.0, 0.5 + 0.1 * len(signals)),
                status=ModelStatus.CANDIDATE,
                created_at=now,
                updated_at=now,
            )
            self._store.models.put(model)
            candidates.append(model)
        return candidates

    def _find_repeated_predicates(self, domain: str | None = None) -> list[Model]:
        recent = self._store.claims.find_active(100)
        predicate_counts: Counter = Counter()
        for claim in recent:
            if domain and claim.domain != domain:
                continue
            predicate_counts[claim.predicate] += 1

        candidates: list[Model] = []
        for predicate, count in predicate_counts.items():
            if count >= self._feedback_threshold:
                existing = self._store.models.find_by_name(predicate)
                if any(m.status == ModelStatus.ACTIVE for m in existing):
                    continue
                model = Model(
                    id=uuid.uuid4().hex[:16],
                    kind=ModelKind.PREDICATE,
                    name=predicate,
                    description=f"Auto-induced predicate from {count} observations",
                    status=ModelStatus.CANDIDATE,
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                self._store.models.put(model)
                candidates.append(model)
        return candidates

    def _find_failed_retrieval_patterns(self) -> list[Model]:
        self_state = self._store.self_store.latest()
        if self_state is None:
            return []
        patterns = self_state.meta_memory.failed_retrieval_patterns
        if len(patterns) < 3:
            return []
        common = Counter(patterns).most_common(3)
        candidates: list[Model] = []
        for pattern, count in common:
            if count < 2:
                continue
            model = Model(
                id=uuid.uuid4().hex[:16],
                kind=ModelKind.INDUCTOR,
                name=f"retrieval_pattern_{pattern[:32]}",
                description=f"Failed retrieval pattern observed {count} times",
                status=ModelStatus.CANDIDATE,
                created_at=time.time(),
                updated_at=time.time(),
            )
            self._store.models.put(model)
            candidates.append(model)
        return candidates

    @staticmethod
    def _weighted_outcomes(
        claims_list: list[Claim], now: float,
    ) -> tuple[dict[str, float], float, float, list[str], list[str]]:
        half_life_hours = 720.0
        neg_boost = 2.0
        weighted: dict[str, float] = {}
        total_weight = 0.0
        total_trust = 0.0
        signal_ids: list[str] = []
        claim_ids: list[str] = []
        for claim in claims_list:
            age_hours = (now - claim.observed_at) / 3600.0
            time_weight = math.exp(-math.log(2) * age_hours / half_life_hours)
            outcome = claim.qualifiers.get("outcome", "unknown")
            outcome_weight = neg_boost if outcome == "failure" else 1.0
            w = time_weight * outcome_weight
            outcome_key = outcome
            weighted[outcome_key] = weighted.get(outcome_key, 0.0) + w
            total_weight += w
            total_trust += claim.trust
            if claim.evidence_signal_ids:
                signal_ids.extend(claim.evidence_signal_ids)
            claim_ids.append(claim.id)
        return weighted, total_weight, total_trust, signal_ids, claim_ids

    def _existing_causal_rule(self, name: str, obj_id: str, subj_id: str | None) -> bool:
        existing = self._store.models.find_by_name(name)
        for m in existing:
            if m.kind == ModelKind.CAUSAL_RULE and m.status == ModelStatus.ACTIVE:
                preconds = set(m.preconditions)
                if f"object:{obj_id}" not in preconds:
                    continue
                if subj_id is None:
                    return True
                any_actor = any(p.startswith("actor:") for p in preconds)
                if not any_actor:
                    return True
                if f"actor:{subj_id}" in preconds:
                    return True
        return False

    def _build_causal_candidate(
        self, predicate: str, obj_id: str, subj_id: str | None,
        majority_outcome: str, weighted_total: float,
        consistency: float, total_trust: float, claim_count: int,
        signal_ids: list[str], claim_ids: list[str],
        permission: object,
    ) -> Model:
        now = time.time()
        mean_trust = total_trust / max(claim_count, 1)
        confidence = min(1.0, 0.2 + 0.3 * consistency + 0.2 * min(1.0, claim_count / 20) + 0.3 * mean_trust)
        preconditions = [f"object:{obj_id}"]
        if subj_id:
            preconditions.append(f"actor:{subj_id}")
        model = Model(
            id=uuid.uuid4().hex[:16],
            kind=ModelKind.CAUSAL_RULE,
            name=predicate,
            description=(
                f"Causal rule: {predicate} {' '.join(preconditions)} -> "
                f"{majority_outcome} (weighted {weighted_total:.1f}, "
                f"{consistency:.0%} consistent)"
            ),
            preconditions=preconditions,
            effects=[f"outcome:{majority_outcome}"],
            evidence_signal_ids=list(set(signal_ids)),
            related_claim_ids=claim_ids,
            confidence=confidence,
            trust=mean_trust,
            status=ModelStatus.CANDIDATE,
            created_at=now,
            updated_at=now,
            permission=permission,
        )
        self._store.models.put(model)
        return model

    def _find_causal_patterns(self, domain: str | None = None) -> list[Model]:
        recent = self._store.claims.find_active(200)
        now = time.time()
        filtered: list[Claim] = []
        for claim in recent:
            if domain and claim.domain != domain:
                continue
            if "outcome" not in claim.qualifiers:
                continue
            filtered.append(claim)

        general_groups: dict[tuple[str, str | None], list[Claim]] = defaultdict(list)
        actor_groups: dict[tuple[str, str | None, str | None], list[Claim]] = defaultdict(list)
        for claim in filtered:
            general_groups[(claim.predicate, claim.object_entity_id)].append(claim)
            actor_groups[(claim.predicate, claim.object_entity_id, claim.subject_entity_id)].append(claim)

        candidates: list[Model] = []
        general_done: set[tuple[str, str | None]] = set()

        for (predicate, obj_id), claims_list in general_groups.items():
            if len(claims_list) < self._feedback_threshold:
                continue
            if self._existing_causal_rule(predicate, obj_id, None):
                continue
            weighted, total_weight, total_trust, sig_ids, cl_ids = self._weighted_outcomes(claims_list, now)
            if not weighted:
                continue
            majority_outcome = max(weighted, key=weighted.get)
            majority_weight = weighted[majority_outcome]
            consistency = majority_weight / total_weight
            if consistency < 0.8:
                continue
            model = self._build_causal_candidate(
                predicate, obj_id, None, majority_outcome, total_weight,
                consistency, total_trust, len(claims_list),
                sig_ids, cl_ids, claims_list[0].permission,
            )
            candidates.append(model)
            general_done.add((predicate, obj_id))

        for (predicate, obj_id, subj_id), claims_list in actor_groups.items():
            if (predicate, obj_id) in general_done:
                continue
            if len(claims_list) < self._feedback_threshold:
                continue
            if self._existing_causal_rule(predicate, obj_id, subj_id):
                continue
            weighted, total_weight, total_trust, sig_ids, cl_ids = self._weighted_outcomes(claims_list, now)
            if not weighted:
                continue
            majority_outcome = max(weighted, key=weighted.get)
            majority_weight = weighted[majority_outcome]
            consistency = majority_weight / total_weight
            if consistency < 0.8:
                continue
            model = self._build_causal_candidate(
                predicate, obj_id, subj_id, majority_outcome, total_weight,
                consistency, total_trust, len(claims_list),
                sig_ids, cl_ids, claims_list[0].permission,
            )
            candidates.append(model)

        return candidates

    def _find_uol_patterns(self, domain: str | None = None) -> list[Model]:
        recent = self._store.claims.find_active(100)
        from collections import Counter
        predicate_counts = Counter(c.predicate for c in recent if not domain or c.domain == domain)
        candidates: list[Model] = []
        for predicate, count in predicate_counts.items():
            if count >= self._feedback_threshold:
                existing = self._store.models.find_by_name(predicate)
                if any(m.kind.value == "uol_semantic" for m in existing):
                    continue
                model = Model(
                    id=uuid.uuid4().hex[:16],
                    kind=ModelKind.UOL_SEMANTIC,
                    name=predicate,
                    description=f"Auto-induced UOL semantic from {count} observations",
                    status=ModelStatus.CANDIDATE,
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                self._store.models.put(model)
                candidates.append(model)
                if self._registry is not None:
                    existing_entry = self._registry.get_uol_semantic(predicate)
                    if existing_entry is None:
                        self._registry.register(RegistryEntry(
                            model_id=model.id,
                            canonical_key=predicate,
                            kind="uol_semantic",
                            aliases=[predicate],
                            description=f"Auto-induced UOL semantic from {count} observations",
                        ))
        return candidates

    def _find_sequential_patterns(self) -> list[Model]:
        """Find repeated Action → Signal patterns (causal induction).

        Acceptance test: Action A repeatedly followed by Signal B within 5 seconds
        → candidate causal_rule with confidence = support / (support + failures)
        """
        recent_actions = self._store.actions.recent(200)
        if len(recent_actions) < self._feedback_threshold:
            return []

        now = time.time()
        pattern_support: dict[tuple[str, str], int] = defaultdict(int)
        pattern_signal_ids: dict[tuple[str, str], list[str]] = defaultdict(list)
        action_result_counts: dict[str, int] = defaultdict(int)

        for action in recent_actions:
            if not action.result_signal_id:
                continue
            sig = self._store.signals.get(action.result_signal_id)
            if not sig:
                continue
            action_result_counts[action.kind.value] += 1
            time_diff = abs(sig.observed_at - action.created_at)
            if time_diff <= 5.0:
                key = (action.kind.value, sig.kind.value)
                pattern_support[key] += 1
                pattern_signal_ids[key].append(sig.id)

        candidates: list[Model] = []
        for (ak, sk), support in pattern_support.items():
            if support < self._feedback_threshold:
                continue
            total_with_result = action_result_counts.get(ak, 0)
            failures = max(total_with_result - support, 0)
            confidence = support / max(support + failures, 1)

            existing = self._store.models.find_by_name(f"causal:{ak}->{sk}")
            if any(m.status == ModelStatus.ACTIVE for m in existing):
                continue

            sig_ids = pattern_signal_ids.get((ak, sk), [])
            model = Model(
                id=uuid.uuid4().hex[:16],
                kind=ModelKind.CAUSAL_RULE,
                name=f"causal:{ak}->{sk}",
                description=(
                    f"Sequential pattern: {ak} -> {sk} "
                    f"(support={support}, failures={failures})"
                ),
                preconditions=[f"action_kind:{ak}"],
                effects=[f"signal_kind:{sk}"],
                evidence_signal_ids=sig_ids,
                confidence=round(confidence, 3),
                status=ModelStatus.CANDIDATE,
                created_at=now,
                updated_at=now,
            )
            self._store.models.put(model)
            candidates.append(model)

        return candidates

    def _find_slot_completion(self) -> list[Model]:
        """Find repeated slot-completion patterns: system ASK → user input.

        Skips intermediary system signals (TRACE, MEMORY_UPDATE, SIMULATION_RESULT)
        to find the user's response after an ACTION_RESULT within the same context.
        Uses observation_semantics to classify completion categories:
        - entity_completion: user response includes a target_entity_id
        - value_completion: user response has speech_act in {answer, provide, confirm}
        - generic_response: user responded but no specific slot metadata
        """
        recent_signals = self._store.signals.recent(200)
        if len(recent_signals) < self._feedback_threshold:
            return []

        by_context: dict[str, list[Signal]] = defaultdict(list)
        for sig in recent_signals:
            by_context[sig.context_id].append(sig)
        for ctx in by_context:
            by_context[ctx].sort(key=lambda s: s.observed_at)

        skip_kinds = {
            SignalKind.TRACE, SignalKind.MEMORY_UPDATE,
            SignalKind.SIMULATION_RESULT, SignalKind.SYSTEM,
        }
        now = time.time()
        completion_counts: Counter = Counter()
        completion_signal_ids: dict[str, list[str]] = defaultdict(list)
        for ctx, signals in by_context.items():
            for i in range(len(signals) - 1):
                a = signals[i]
                if a.kind != SignalKind.ACTION_RESULT:
                    continue
                for j in range(i + 1, len(signals)):
                    b = signals[j]
                    gap = b.observed_at - a.observed_at
                    if gap > 5.0:
                        break
                    if b.kind in skip_kinds:
                        continue
                    if b.source_type == SourceType.USER:
                        obs = b.observation_semantics
                        if obs and (obs.target_entity_id or obs.semantic_cluster_key):
                            completion_counts["entity_completion"] += 1
                            completion_signal_ids["entity_completion"].extend([a.id, b.id])
                        elif obs and obs.speech_act in ("answer", "provide", "confirm"):
                            completion_counts["value_completion"] += 1
                            completion_signal_ids["value_completion"].extend([a.id, b.id])
                        else:
                            completion_counts["generic_response"] += 1
                            completion_signal_ids["generic_response"].extend([a.id, b.id])
                    break

        candidates: list[Model] = []
        for pattern, count in completion_counts.items():
            if count < self._feedback_threshold:
                continue
            existing = self._store.models.find_by_name(f"completion:{pattern}")
            if any(m.status == ModelStatus.ACTIVE for m in existing):
                continue
            sig_ids = list(set(completion_signal_ids.get(pattern, [])))
            model = Model(
                id=uuid.uuid4().hex[:16],
                kind=ModelKind.CONTEXT_RULE,
                name=f"completion:{pattern}",
                description=f"Slot completion pattern: {pattern} ({count} occurrences)",
                evidence_signal_ids=sig_ids,
                confidence=min(1.0, count / 20),
                status=ModelStatus.CANDIDATE,
                created_at=now,
                updated_at=now,
            )
            self._store.models.put(model)
            candidates.append(model)

        return candidates
