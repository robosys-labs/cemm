"""LegacyImportGuard — canonical kernel never imports legacy.

Import boundary: standard library only.

Architectural guardrails (AGENTS.md §22, §24):
- legacy → isolated; canonical kernel never imports it
- legacy imports are absent from the canonical kernel
- run the old and new pipelines in parallel and call the new path
  authoritative — forbidden
- call shadow code complete — forbidden

The canonical kernel tree is defined in KERNEL_FOLDER_STRUCTURE.md.
The new architecture kernel modules are in:
  kernel/model, kernel/schema, kernel/epistemics, kernel/learning,
  kernel/understanding, kernel/self_model, kernel/execution,
  kernel/response, kernel/correction, kernel/retirement, kernel/foundations,
  kernel/boot

Legacy modules are everything else in kernel/ that predates the new
architecture (meaning_perceptor, meaning_graph_builder, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Canonical new-architecture kernel packages (subdirectories only)
CANONICAL_KERNEL_PACKAGES: frozenset[str] = frozenset({
    "model",
    "schema",
    "epistemics",
    "learning",
    "understanding",
    "self_model",
    "execution",
    "response",
    "correction",
    "retirement",
    "foundations",
    "boot",
})

# Legacy patterns that must not appear in canonical kernel imports
LEGACY_IMPORT_PATTERNS: tuple[str, ...] = (
    "from cemm.legacy",
    "import cemm.legacy",
    "from ..legacy",
    "from ...legacy",
    "from cemm.kernel.meaning_perceptor",
    "from cemm.kernel.meaning_graph_builder",
    "from cemm.kernel.semantic_kernel_runtime",
    "from cemm.kernel.operational_meaning_compiler",
    "from cemm.kernel.conversation_act_classifier",
    "from cemm.kernel.operational_contract_compiler",
    "from cemm.kernel.operational_causal_router",
    "from cemm.kernel.semantic_program_compiler",
    "from cemm.kernel.semantic_obligation_scheduler",
    "from cemm.kernel.state_transmutation_compiler",
    "from cemm.kernel.state_occupancy_compiler",
    "from cemm.kernel.state_delta_compiler",
    "from cemm.kernel.relation_frame_compiler",
    "from cemm.kernel.transmutation_authorizer",
    "from cemm.kernel.write_contract_builder",
    "from cemm.kernel.memory_update_planner",
    "from cemm.kernel.output_state_updater",
    "from cemm.kernel.outcome_evaluator",
    "from cemm.kernel.turn_execution_planner",
    "from cemm.kernel.contract_executor",
    "from cemm.kernel.affordance_predictor",
    "from cemm.kernel.causal_effect_graph",
    "from cemm.kernel.obligation_graph_builder",
    "from cemm.kernel.obligation_contract_builder",
    "from cemm.kernel.semantic_cpu",
    "from cemm.kernel.semantic_integrity",
    "from cemm.kernel.semantic_working_set",
    "from cemm.kernel.semantic_attention_controller",
    "from cemm.kernel.semantic_clusters",
    "from cemm.kernel.semantic_query_engine",
    "from cemm.kernel.semantic_schema_kernel",
    "from cemm.kernel.session_store",
    "from cemm.kernel.teaching_frame_manager",
    "from cemm.kernel.teaching_interpreter",
    "from cemm.kernel.training_export",
    "from cemm.kernel.training_tasks",
    "from cemm.kernel.uol_metadata",
    "from cemm.kernel.realization_verifier",
    "from cemm.kernel.promotion_gate",
    "from cemm.kernel.predicate_activation_resolver",
    "from cemm.kernel.pragmatic_interpreter",
    "from cemm.kernel.safety_frame_detector",
    "from cemm.kernel.relation_algebra",
    "from cemm.kernel.relation_extractor",
    "from cemm.kernel.retrieval_planner",
    "from cemm.kernel.role_ref_resolver",
    "from cemm.kernel.scope_graph_builder",
    "from cemm.kernel.semantic_obligation_scheduler",
    "from cemm.kernel.situation_frame_builder",
    "from cemm.kernel.text_match",
    "from cemm.kernel.text_normalizer",
    "from cemm.kernel.turn_semantic_index",
    "from cemm.kernel.entity_fact_extractor",
    "from cemm.kernel.entity_grounding_resolver",
    "from cemm.kernel.entity_salience_tracker",
    "from cemm.kernel.error_attribution_engine",
    "from cemm.kernel.frame_binder",
    "from cemm.kernel.implicit_predicate_detector",
    "from cemm.kernel.intent_parser",
    "from cemm.kernel.interpretation_lattice",
    "from cemm.kernel.interpretation_resolver",
    "from cemm.kernel.language_adapter",
    "from cemm.kernel.language_detection",
    "from cemm.kernel.learning_contract_builder",
    "from cemm.kernel.construction_matcher",
    "from cemm.kernel.context_kernel_builder",
    "from cemm.kernel.branch_arbitrator",
    "from cemm.kernel.capability_classifier",
    "from cemm.kernel.anaphora_resolver",
    "from cemm.kernel.answer_graph_ranker",
    "from cemm.kernel.packet_validator",
    "from cemm.kernel.port_resolver",
    "from cemm.kernel.predicate_phrase_extractor",
    "from cemm.kernel.proposition_semantics",
    "from cemm.kernel.query_contract_builder",
    "from cemm.kernel.reaction_contract_builder",
    "from cemm.kernel.reaction_detector",
    "from cemm.kernel.act_resolution_planner",
    "from cemm.kernel.conversation_act_classifier",
    "from cemm.kernel.pipeline",
    "from cemm.kernel.semantic_kernel_runtime",
    "from cemm.kernel.meaning_perceptor",
    "from cemm.kernel.meaning_graph_builder",
    "from ..meaning_perceptor",
    "from ..meaning_graph_builder",
    "from ..semantic_kernel_runtime",
    "from ..operational_meaning_compiler",
    "from ..conversation_act_classifier",
    "from ..semantic_schema_kernel",
    "from ..semantic_cpu",
    "from ..semantic_query_engine",
    "from ..session_store",
    "from ..teaching_frame_manager",
    "from ..teaching_interpreter",
    "from ..output_state_updater",
    "from ..outcome_evaluator",
    "from ..turn_execution_planner",
    "from ..contract_executor",
    "from ..transmutation_authorizer",
    "from ..write_contract_builder",
    "from ..memory_update_planner",
    "from ..semantic_program_compiler",
    "from ..semantic_obligation_scheduler",
    "from ..state_transmutation_compiler",
    "from ..state_occupancy_compiler",
    "from ..state_delta_compiler",
    "from ..relation_frame_compiler",
    "from ..operational_contract_compiler",
    "from ..operational_causal_router",
    "from ..causal_effect_graph",
    "from ..obligation_graph_builder",
    "from ..obligation_contract_builder",
    "from ..affordance_predictor",
    "from ..capability_classifier",
    "from ..realization_verifier",
    "from ..promotion_gate",
    "from ..predicate_activation_resolver",
    "from ..pragmatic_interpreter",
    "from ..safety_frame_detector",
    "from ..relation_algebra",
    "from ..relation_extractor",
    "from ..retrieval_planner",
    "from ..role_ref_resolver",
    "from ..scope_graph_builder",
    "from ..situation_frame_builder",
    "from ..uol_metadata",
    "from ..text_match",
    "from ..text_normalizer",
    "from ..turn_semantic_index",
    "from ..entity_fact_extractor",
    "from ..entity_grounding_resolver",
    "from ..entity_salience_tracker",
    "from ..error_attribution_engine",
    "from ..frame_binder",
    "from ..implicit_predicate_detector",
    "from ..intent_parser",
    "from ..interpretation_lattice",
    "from ..interpretation_resolver",
    "from ..language_adapter",
    "from ..language_detection",
    "from ..learning_contract_builder",
    "from ..construction_matcher",
    "from ..context_kernel_builder",
    "from ..branch_arbitrator",
    "from ..anaphora_resolver",
    "from ..answer_graph_ranker",
    "from ..packet_validator",
    "from ..port_resolver",
    "from ..predicate_phrase_extractor",
    "from ..proposition_semantics",
    "from ..query_contract_builder",
    "from ..reaction_contract_builder",
    "from ..reaction_detector",
    "from ..act_resolution_planner",
    "from ..pipeline",
)


@dataclass(frozen=True, slots=True)
class LegacyImportViolation:
    """A legacy import violation found in a canonical kernel module."""
    file_path: str
    line_number: int
    import_statement: str
    violation_kind: str  # legacy_import, shadow_code, parallel_pipeline


@dataclass(frozen=True, slots=True)
class LegacyImportScanResult:
    """Result of scanning canonical kernel modules for legacy imports."""
    is_clean: bool
    violations: tuple[LegacyImportViolation, ...] = ()
    files_scanned: int = 0


class LegacyImportGuard:
    """Guards that the canonical kernel never imports legacy code.

    legacy → isolated; canonical kernel never imports it.
    legacy imports are absent from the canonical kernel.
    """

    def scan_directory(self, directory: Path) -> LegacyImportScanResult:
        """Scan a directory for legacy imports in canonical kernel modules.

        Only scans .py files in canonical kernel subdirectories.
        """
        violations: list[LegacyImportViolation] = []
        files_scanned = 0

        for pkg in CANONICAL_KERNEL_PACKAGES:
            pkg_dir = directory / pkg
            if not pkg_dir.is_dir():
                continue
            for py_file in pkg_dir.rglob("*.py"):
                if py_file.name.startswith("_debug") or py_file.name.startswith("_test"):
                    continue
                files_scanned += 1
                file_violations = self.scan_file(py_file)
                violations.extend(file_violations)

        return LegacyImportScanResult(
            is_clean=len(violations) == 0,
            violations=tuple(violations),
            files_scanned=files_scanned,
        )

    def scan_file(self, file_path: Path) -> tuple[LegacyImportViolation, ...]:
        """Scan a single file for legacy imports."""
        violations: list[LegacyImportViolation] = []

        try:
            source = file_path.read_text(encoding="utf-8")
        except Exception:
            return tuple()

        for line_num, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue

            for pattern in LEGACY_IMPORT_PATTERNS:
                if pattern in stripped:
                    violations.append(LegacyImportViolation(
                        file_path=str(file_path),
                        line_number=line_num,
                        import_statement=stripped,
                        violation_kind="legacy_import",
                    ))
                    break  # One violation per line

        return tuple(violations)

    def check_no_legacy_imports(self, directory: Path) -> bool:
        """Check that no canonical kernel module imports legacy code."""
        result = self.scan_directory(directory)
        return result.is_clean
