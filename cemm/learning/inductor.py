from __future__ import annotations
from ..store.store import Store
from ..types.model import Model, ModelKind, ModelStatus
from ..types.claim import Claim, ClaimStatus
from ..types.signal import Signal, SignalKind, SourceType
import math, time, uuid
from collections import Counter, defaultdict


class Inductor:
    def __init__(self, store: Store, feedback_threshold: int = 5) -> None:
        self._store = store
        self._feedback_threshold = feedback_threshold

    def set_threshold(self, value: int) -> None:
        self._feedback_threshold = value

    def maybe_induct(self, domain: str | None = None) -> list[Model]:
        candidates: list[Model] = []
        candidates.extend(self._find_repeated_predicates(domain))
        candidates.extend(self._find_failed_retrieval_patterns())
        candidates.extend(self._find_causal_patterns(domain))
        candidates.extend(self._find_uol_patterns(domain))
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
        return candidates
