"""Integrated FormResolver -> StructuralModeProjector R3 mode coverage."""
from __future__ import annotations

import json
from pathlib import Path

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.mode import StructuralModeProjector

__cemm_test_inventory__ = {'tests/test_r3_form_mode_integration.py::test_reviewed_conditional_and_hypothetical_forms_project_simulation': {'activation_phase': 'R3',
                                                                                                                 'assertion_ref': 'assertion:r3-reviewed-conditional-hypothetical-project-simulate',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R3-Self-Close',
                                                                                                                 'owner_ref': 'situation-context',
                                                                                                                 'source_ast_sha256': '07c0d298a26964c6abde10ea456c9eeff65a987045b599a5a14ea9637693cb74'}}

ROOT = Path(__file__).resolve().parents[1]


def test_reviewed_conditional_and_hypothetical_forms_project_simulation() -> None:
    form_pack = json.loads((ROOT / "data" / "languages" / "en" / "forms.json").read_text(encoding="utf-8"))
    resolver = FormResolver(form_pack, RuntimeConfig.release())
    projector = StructuralModeProjector()
    for text in ("if x", "suppose x", "imagine x"):
        assert projector.project(resolver.resolve(text)).mode is SemanticMode.SIMULATE
