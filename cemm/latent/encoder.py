from __future__ import annotations

from typing import Any

from ..types.latent_space import LatentSpaceSpec, TypedLatents
from ..training.tl1_feature_extractor import Feature
from ..training.tl1_hash_encoder import hash_encode


_DEFAULT_DIM = 64


_SPACES = [
    LatentSpaceSpec("entity", _DEFAULT_DIM),
    LatentSpaceSpec("process", _DEFAULT_DIM),
    LatentSpaceSpec("state", _DEFAULT_DIM),
    LatentSpaceSpec("claim", _DEFAULT_DIM),
    LatentSpaceSpec("model", _DEFAULT_DIM),
    LatentSpaceSpec("context", _DEFAULT_DIM),
    LatentSpaceSpec("self", _DEFAULT_DIM),
    LatentSpaceSpec("memory", _DEFAULT_DIM),
    LatentSpaceSpec("action", _DEFAULT_DIM),
    LatentSpaceSpec("answer", _DEFAULT_DIM),
]


class LatentEncoder:
    """Deterministic baseline typed latent encoder.

    Produces fixed-size vectors from typed features. Each typed space is hashed
    into its own namespace so entity, process, and state features do not collide.
    """

    def __init__(self, dim: int = _DEFAULT_DIM) -> None:
        self.dim = dim
        self.spaces = {s.name: s for s in _SPACES}

    def encode(self, namespace: str, features: list[Any]) -> list[float]:
        """Encode a list of typed features into a dense float vector."""
        typed_features = [
            Feature(namespace=namespace, key=str(f), value=1.0)
            for f in features
        ]
        sparse = hash_encode(typed_features, num_buckets=self.dim)
        dense = [0.0] * self.dim
        for idx, val in sparse.items():
            if 0 <= idx < self.dim:
                dense[idx] = val
        return dense

    def encode_entity(self, entity_id: str, entity_name: str = "") -> list[float]:
        return self.encode("entity", [entity_id, entity_name])

    def encode_process(self, frame_key: str) -> list[float]:
        return self.encode("process", [frame_key])

    def encode_state(self, state_key: str) -> list[float]:
        return self.encode("state", [state_key])

    def encode_claim(self, predicate: str, object_value: str = "") -> list[float]:
        return self.encode("claim", [predicate, object_value])

    def encode_model(self, registry_key: str) -> list[float]:
        return self.encode("model", [registry_key])

    def encode_context(self, context_id: str) -> list[float]:
        return self.encode("context", [context_id])

    def encode_self(self, mode: str, uncertainty: float = 0.0) -> list[float]:
        return self.encode("self", [mode, str(round(uncertainty, 2))])

    def encode_memory(self, selected_claim_ids: list[str]) -> list[float]:
        return self.encode("memory", selected_claim_ids)

    def encode_action(self, action_kind: str) -> list[float]:
        return self.encode("action", [action_kind])

    def encode_answer(
        self,
        intent: str,
        selected_claim_ids: list[str],
        selected_model_ids: list[str],
    ) -> list[float]:
        return self.encode("answer", [intent] + list(selected_claim_ids) + list(selected_model_ids))

    def encode_typed(
        self,
        entity_ids: list[str] | None = None,
        process_keys: list[str] | None = None,
        state_keys: list[str] | None = None,
        claim_tuples: list[tuple[str, str]] | None = None,
        model_keys: list[str] | None = None,
        context_id: str = "",
        self_mode: str = "",
        self_uncertainty: float = 0.0,
        memory_claim_ids: list[str] | None = None,
        action_kind: str = "",
        answer_intent: str = "",
        answer_claim_ids: list[str] | None = None,
        answer_model_ids: list[str] | None = None,
    ) -> TypedLatents:
        """Encode all typed spaces at once."""
        return TypedLatents(
            entity=self.encode("entity", entity_ids or []),
            process=self.encode("process", process_keys or []),
            state=self.encode("state", state_keys or []),
            claim=self.encode("claim", [f"{p}:{o}" for p, o in (claim_tuples or [])]),
            model=self.encode("model", model_keys or []),
            context=self.encode("context", [context_id] if context_id else []),
            self=self.encode("self", [self_mode, str(round(self_uncertainty, 2))] if self_mode else []),
            memory=self.encode("memory", memory_claim_ids or []),
            action=self.encode("action", [action_kind] if action_kind else []),
            answer=self.encode("answer", [answer_intent] + (answer_claim_ids or []) + (answer_model_ids or [])),
        )
