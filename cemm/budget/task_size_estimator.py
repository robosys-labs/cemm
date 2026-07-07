"""Semantic task-size estimation.

This module deliberately does not inspect natural-language cue strings.  It
estimates work from already-built runtime structures: graph counts, relation
counts, query status, answer evidence, patch count, and explicit document-like
metadata when present.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskSizeEstimate:
    score: float = 0.0
    level: str = "small"  # small, medium, large, huge
    features: dict[str, float] = field(default_factory=dict)


class TaskSizeEstimator:
    def estimate(self, *, situation: Any | None = None, signal: Any | None = None, uol_graph: Any | None = None, relation_frames: list[Any] | None = None) -> TaskSizeEstimate:
        graph = uol_graph or getattr(situation, "uol_graph", None)
        relations = relation_frames if relation_frames is not None else list(getattr(situation, "relation_frames", []) or [])
        sig = signal or getattr(situation, "signal", None)
        evidence = getattr(situation, "evidence", None)
        binding = getattr(situation, "answer_binding", None) or getattr(evidence, "answer_binding", None)

        atoms = float(len(getattr(graph, "atoms", {}) or {}))
        edges = float(len(getattr(graph, "edges", []) or []))
        groups = float(len(getattr(graph, "groups", []) or []))
        candidates = float(len(getattr(graph, "candidate_sets", []) or []))
        patches = float(len(getattr(graph, "patch_candidates", []) or []))
        relation_count = float(len(relations or []))
        fill_count = float(len(getattr(binding, "slot_fills", []) or []))
        raw_len = float(len(str(getattr(sig, "content", "") or "")))

        # Optional upstream document/task metadata. These are semantic metadata,
        # not language parsing.
        metadata = getattr(sig, "metadata", None) or getattr(sig, "features", None) or {}
        doc_pages = float(metadata.get("page_count", 0) or metadata.get("pages", 0) or 0) if isinstance(metadata, dict) else 0.0
        doc_sections = float(metadata.get("section_count", 0) or metadata.get("sections", 0) or 0) if isinstance(metadata, dict) else 0.0

        score = (
            min(1.0, atoms / 250.0) * 0.18
            + min(1.0, edges / 300.0) * 0.14
            + min(1.0, groups / 40.0) * 0.12
            + min(1.0, candidates / 50.0) * 0.10
            + min(1.0, patches / 20.0) * 0.08
            + min(1.0, relation_count / 150.0) * 0.12
            + min(1.0, fill_count / 20.0) * 0.06
            + min(1.0, raw_len / 12000.0) * 0.10
            + min(1.0, doc_pages / 100.0) * 0.06
            + min(1.0, doc_sections / 80.0) * 0.04
        )
        if score < 0.25:
            level = "small"
        elif score < 0.55:
            level = "medium"
        elif score < 0.82:
            level = "large"
        else:
            level = "huge"
        return TaskSizeEstimate(score=max(0.0, min(1.0, score)), level=level, features={
            "atoms": atoms,
            "edges": edges,
            "groups": groups,
            "candidate_sets": candidates,
            "patch_candidates": patches,
            "relation_frames": relation_count,
            "slot_fills": fill_count,
            "raw_chars": raw_len,
            "document_pages": doc_pages,
            "document_sections": doc_sections,
        })
