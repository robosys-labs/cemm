"""EntitySalienceTracker - track entity salience across groups and turns.

Language-agnostic: scores entities by recency, role prominence, and mention
count. Surface patterns are referent fields, not English strings.

Formula: salience = recency * 0.5 + role_prominence * 0.3 + mention_bonus * 0.2
"""

from __future__ import annotations

from typing import Any

from ..types.meaning_percept import MeaningGroup, ReferentAtom

_ROLE_PROMINENCE: dict[str, float] = {
    "actor": 1.0,
    "speaker": 0.95,
    "topic": 0.85,
    "target": 0.7,
    "object": 0.65,
    "place": 0.6,
    "possessor": 0.5,
    "listener": 0.45,
}


class EntitySalienceTracker:
    """Track entity salience across groups and turns.

    Scores each entity based on:
    - recency: position in group sequence (later groups = higher)
    - role_prominence: semantic role (actor > topic > target > ...)
    - mention_count: how often the entity appears
    """

    def track(
        self,
        referents: list[ReferentAtom],
        groups: list[MeaningGroup],
        prior_salience: dict[str, float] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, float]]:
        """Score and rank entity salience.

        Args:
            referents: Flat list of all referent atoms.
            groups: Meaning groups (each has its own referent list).
            prior_salience: Salience map from previous turn(s).

        Returns:
            Tuple of (ranked_entities, updated_salience_map).
            Each ranked entity dict has keys: key, score, count, top_role.
        """
        salience: dict[str, float] = dict(prior_salience or {})
        mention_counts: dict[str, int] = {}
        roles: dict[str, list[str]] = {}
        group_order: dict[str, int] = {}

        for group_index, group in enumerate(groups):
            for ref in group.referents:
                key = ref.entity_id or ref.surface.lower()
                mention_counts[key] = mention_counts.get(key, 0) + 1
                roles.setdefault(key, []).append(ref.role)
                group_order[key] = group_index

        for ref in referents:
            if ref.group_id:
                continue
            key = ref.entity_id or ref.surface.lower()
            mention_counts[key] = mention_counts.get(key, 0) + 1
            roles.setdefault(key, []).append(ref.role)
            if key not in group_order:
                group_order[key] = 0

        total_groups = max(1, len(groups))
        seen_keys = set(list(mention_counts.keys()) + list(salience.keys()))

        for key in seen_keys:
            recency = (
                1.0 - (group_order.get(key, 0) / total_groups)
                if key in group_order
                else 0.0
            )
            role_prom = self._role_prominence(
                roles.get(key, ["topic"]),
            )
            mention_bonus = min(mention_counts.get(key, 0), 5)
            score = (
                recency * 0.5
                + role_prom * 0.3
                + mention_bonus * 0.04
            )
            salience[key] = score

        ranked: list[dict[str, Any]] = sorted(
            [
                {
                    "key": k,
                    "score": v,
                    "count": mention_counts.get(k, 0),
                    "top_role": self._top_role(
                        roles.get(k, ["topic"]),
                    ),
                }
                for k, v in salience.items()
            ],
            key=lambda x: x["score"],
            reverse=True,
        )

        return ranked, salience

    @staticmethod
    def _role_prominence(role_list: list[str]) -> float:
        """Compute maximum role prominence from a list of roles."""
        if not role_list:
            return 0.5
        return max(_ROLE_PROMINENCE.get(r, 0.5) for r in role_list)

    @staticmethod
    def _top_role(role_list: list[str]) -> str:
        """Return the most prominent role from a list."""
        if not role_list:
            return "topic"
        return max(
            role_list,
            key=lambda r: _ROLE_PROMINENCE.get(r, 0.5),
        )
