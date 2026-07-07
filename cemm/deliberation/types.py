"""Deliberation and anytime-distillation types for CEMM v3.1 Phase 7.

The types are intentionally language-agnostic. Document structure arrives as
semantic metadata from upstream parsing/perception; this layer does not infer
meaning from user-visible surface strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SourceDescriptor:
    """Structured source metadata available before expensive reading."""

    source_id: str
    source_type: str = "unknown"  # document, pdf, corpus, webpage, memory_set, etc.
    unit_count: int = 0
    token_count: int = 0
    section_count: int = 0
    artifact_count: int = 0
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    risk_tags: set[str] = field(default_factory=set)


@dataclass
class DocumentSection:
    section_id: str
    index: int = 0
    depth: int = 1
    role: str = "body"  # abstract, toc, intro, body, conclusion, appendix, references
    parent_id: str = ""
    page_start: int = 0
    page_end: int = 0
    token_estimate: int = 0
    line_count: int = 0
    salience: float = 0.5
    title_atom_id: str = ""
    source_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentArtifact:
    artifact_id: str
    artifact_type: str = "unknown"  # table, figure, citation, equation, code_block
    section_id: str = ""
    page: int = 0
    salience: float = 0.5
    source_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentMap:
    source_id: str
    title_ref: str = ""
    page_count: int = 0
    token_estimate: int = 0
    sections: list[DocumentSection] = field(default_factory=list)
    artifacts: list[DocumentArtifact] = field(default_factory=list)
    metadata_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    coverage_denominator: int = 0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def size_score(self) -> float:
        section_load = min(1.0, len(self.sections) / 40.0)
        token_load = min(1.0, self.token_estimate / 80000.0) if self.token_estimate else 0.0
        artifact_load = min(1.0, len(self.artifacts) / 40.0)
        return max(section_load, token_load, artifact_load)


@dataclass(frozen=True)
class ReadUnit:
    unit_id: str
    source_id: str
    unit_type: str  # metadata, section_full, section_boundary, artifact, gap_probe
    target_id: str = ""
    priority: int = 5
    cost_ms: float = 100.0
    coverage_weight: float = 0.0
    required: bool = False
    reason: str = ""
    source_refs: tuple[str, ...] = ()


@dataclass
class DeliberationPlan:
    strategy: str = "direct_answer"
    depth: str = "shallow"  # none, shallow, sampled, recursive, deep
    retrieval_policy: str = "normal"  # none, narrow, sampled, broad
    distillation_policy: str = "none"  # none, rapid_skim, recursive, deep
    confidence_target: float = 0.5
    coverage_target: float = 0.5
    max_recursive_steps: int = 0
    stop_conditions: list[str] = field(default_factory=list)
    disclosure_requirements: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class DistillationPlan:
    strategy: str = "none"
    source_ids: list[str] = field(default_factory=list)
    read_units: list[ReadUnit] = field(default_factory=list)
    recursive_passes: int = 0
    sampling_policy: str = "none"
    coverage_estimate: float = 0.0
    expected_blind_spots: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class DistilledUnit:
    unit_id: str
    source_id: str
    unit_type: str
    payload: Any = None
    summary_atoms: list[Any] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    coverage_weight: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class DistillationResult:
    strategy: str = "none"
    units: list[DistilledUnit] = field(default_factory=list)
    merged_atoms: list[Any] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    coverage_estimate: float = 0.0
    confidence: float = 0.0
    blind_spots: list[str] = field(default_factory=list)
    partial: bool = False
    diagnostics: dict[str, Any] = field(default_factory=dict)


ContentProvider = Callable[[ReadUnit], Any]
