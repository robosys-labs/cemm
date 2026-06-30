from __future__ import annotations
import json
from typing import Any
from ..store.store import Store


class ArtifactStore:
    def __init__(self, store: Store) -> None:
        self._conn = store.conn

    def get_active_artifact(self, model_kind: str) -> dict[str, Any] | None:
        try:
            row = self._conn.execute(
                "SELECT artifact_json FROM models WHERE kind = ? AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
                (model_kind,),
            ).fetchone()
            if not row or not row[0]:
                return None
            return json.loads(row[0])
        except Exception:
            return None

    def find_example(self, artifact: dict[str, Any], text: str, min_score: float = 0.15) -> dict[str, Any] | None:
        examples = artifact.get("examples", [])
        if not examples:
            return None

        text_lower = text.lower()
        text_words = set(text_lower.split())

        best_score = 0.0
        best_example = None

        for ex in examples:
            inp = ex.get("input", {})
            inp_text = ""
            if isinstance(inp, dict):
                inp_text = inp.get("text", "") or inp.get("content", "") or ""
            elif isinstance(inp, str):
                inp_text = inp
            inp_lower = inp_text.lower()
            inp_words = set(inp_lower.split())

            if not inp_words or not text_words:
                continue

            overlap = len(text_words & inp_words)
            union = len(text_words | inp_words)
            if union == 0:
                continue
            jaccard = overlap / union
            score = jaccard * ex.get("confidence", 0.5)

            if score > best_score:
                best_score = score
                best_example = ex

        if best_score < min_score:
            return None
        return best_example
