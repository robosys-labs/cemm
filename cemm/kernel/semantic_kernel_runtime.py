"""SemanticKernelRuntime — CPU: single authoritative entrypoint for the semantic cycle.

Wires perception, graph building, attention scheduling, planning, patch
extraction, patch validation, and consolidation into one orchestrator.
Produces a RuntimeCycleResult with the full architectural trace.
"""

from __future__ import annotations
import time
from typing import Any

from .semantic_cpu import SemanticCPU
from .semantic_attention_controller import SemanticAttentionController
from ..learning.patch_validator import PatchValidator
from ..types.runtime_cycle import RuntimeCycleResult


class SemanticKernelRuntime:
    """CPU — single authoritative entrypoint for the semantic runtime cycle.

    Wires all core components into one orchestrator. Use run_turn() to
    process a signal through the full cycle.
    """

    def __init__(
        self,
        concept_lattice: Any | None = None,
        construction_lattice: Any | None = None,
        episodic_store: Any | None = None,
        store: Any | None = None,
        auto_consolidate: bool = False,
    ) -> None:
        self.concept_lattice = concept_lattice
        self.construction_lattice = construction_lattice
        self.episodic_store = episodic_store
        self.auto_consolidate = auto_consolidate

        # Reuse SemanticCPU for core component wiring — avoids duplicating
        # MeaningGraphBuilder, MeaningPerceptor, ActResolutionPlanner,
        # GraphPatchExtractor, ConceptConsolidator setup
        self._cpu = SemanticCPU(
            concept_lattice=concept_lattice,
            construction_lattice=construction_lattice,
            episodic_store=episodic_store,
            auto_consolidate=auto_consolidate,
        )

        # Expose SemanticCPU's public attributes for Pipeline cherry-picking
        self.graph_builder = self._cpu.graph_builder
        self.perceptor = self._cpu.perceptor
        self.planner = self._cpu.planner
        self.patch_extractor = self._cpu.patch_extractor
        self.consolidator = self._cpu.consolidator

        # Phase 3-4 additions
        self._attention = SemanticAttentionController()
        self._patch_validator = PatchValidator(store=store)

    @property
    def attention(self):
        """Expose the SemanticAttentionController for Pipeline use."""
        return self._attention

    def run_turn(
        self,
        signal: Any,
        kernel: Any,
        *,
        percept: Any | None = None,
        retrieval_plan: Any | None = None,
        safety_frame: Any | None = None,
        situation: Any | None = None,
    ) -> RuntimeCycleResult:
        start = time.monotonic()
        result = RuntimeCycleResult(signal=signal, context_kernel=kernel)
        errors: list[str] = []

        # 1. Perceive
        try:
            if percept is None:
                percept = self._cpu.perceptor.perceive(signal, kernel)
            result.percept = percept
        except Exception as e:
            errors.append(f"perceive failed: {e}")
            result.cost_ms = (time.monotonic() - start) * 1000
            result.diagnostics = {"errors": errors}
            return result

        # 2. Build working graph
        try:
            uol_graph = getattr(percept, "uol_graph", None)
            if uol_graph is None:
                uol_graph = self._cpu.graph_builder.build(percept)
                if hasattr(percept, "uol_graph"):
                    percept.uol_graph = uol_graph
            result.uol_graph = uol_graph
        except Exception as e:
            errors.append(f"build failed: {e}")
            result.cost_ms = (time.monotonic() - start) * 1000
            result.diagnostics = {"errors": errors}
            return result

        # 3. Attend — select focus (Phase 3)
        try:
            budget = getattr(kernel, "budget", None) if kernel is not None else None
            working_set = self._attention.attend(uol_graph, kernel, budget)
            result.working_set = working_set
        except Exception as e:
            errors.append(f"attend failed: {e}")

        # 4. Plan
        try:
            act_plan = self._cpu.planner.plan(
                conversation_act=None,
                situation=situation,
                safety_frame=safety_frame,
                meaning_percept=percept,
                retrieval_plan=retrieval_plan,
            )
            result.act_plan = act_plan
        except Exception as e:
            errors.append(f"plan failed: {e}")

        # 5. Extract patches
        try:
            patches = list(self._cpu.patch_extractor.extract(uol_graph))
            result.patch_candidates = patches
        except Exception as e:
            errors.append(f"extract failed: {e}")
            patches = []

        # 6. Validate patches (Phase 4)
        for patch in patches:
            try:
                validation = self._patch_validator.validate(patch, kernel)
                result.validation.append(validation)
            except Exception as e:
                errors.append(f"validate patch {patch.id}: {e}")

        # 7. Consolidate (Phase 4 — only if auto)
        if self.auto_consolidate and patches:
            try:
                consolidation = self._cpu.consolidator.consolidate(patches, source_graph=uol_graph)
                result.consolidation = [consolidation]
            except Exception as e:
                errors.append(f"consolidate failed: {e}")

        result.cost_ms = (time.monotonic() - start) * 1000
        if errors:
            result.diagnostics = {"errors": errors}
        return result
