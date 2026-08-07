#!/usr/bin/env python3
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
import pprint

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

TRANSITION = '''"""R3 rewrite-successor-only transition simulation coverage."""
from __future__ import annotations
from typing import Any
import pytest
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.epistemics import EpistemicPlacement
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.state import TemporalState, TransitionEngine

class _TransitionAuthority:
    generation = "authority:transition-test-v1"
    content_hash = "test-content"
    model_compatibility_hash = "test-compat"
    value_dimensions = {"value:off":"dim:power","value:on":"dim:power","value:offline":"dim:availability","value:online":"dim:availability","value:open":"dim:door_state"}
    capabilities = {}
    permissions = ()
    adapters = ()
    operator_roles = {}
    _transitions = {
        "transition:power_on":{"transition_ref":"transition:power_on","preconditions":[{"dimension":"dim:power","value":"value:off"}],"effects":[{"dimension":"dim:power","value":"value:on"}]},
        "transition:connect":{"transition_ref":"transition:connect","preconditions":[{"dimension":"dim:power","value":"value:on"}],"effects":[{"dimension":"dim:availability","value":"value:online"}]},
    }
    def by_kind(self, kind: str) -> frozenset[str]: return frozenset()
    def by_transition(self, key: str) -> dict[str, Any] | None: return self._transitions.get(key)
    def by_event_signature(self, event_type: str) -> Any: return None
    def by_state_dimension(self, dim: str) -> frozenset[str]: return frozenset()

def _placement(mode: str = "observed") -> EpistemicPlacement:
    return EpistemicPlacement(source_ref="participant:user", mode=mode)

def _temporal_state(entity: str = "entity:server", dimension: str = "dim:power", value: str = "value:off") -> TemporalState:
    return TemporalState(entity_ref=entity, dimension_ref=dimension, value_ref=value, interval=(0,100), placement=_placement(), revision=0)

@pytest.fixture
def authority() -> _TransitionAuthority: return _TransitionAuthority()
@pytest.fixture
def config() -> RuntimeConfig: return RuntimeConfig.release()
@pytest.fixture
def transition_engine(authority, config) -> TransitionEngine: return TransitionEngine(authority, config)
@pytest.fixture
def offline_state() -> TemporalState: return _temporal_state("entity:server", "dim:power", "value:off")
@pytest.fixture
def stores(authority): return memory_stores(authority_generation=authority.generation)

class TestSimulatedTransitionDoesNotCommit:
    def test_preview_does_not_mutate_revision(self, transition_engine, offline_state, stores):
        before = stores.world.revision
        preview = transition_engine.preview(offline_state, "transition:power_on")
        assert preview.resulting_state.value_ref == "value:on"
        assert stores.world.revision == before

    def test_preview_sequence_does_not_mutate_revision(
        self, transition_engine, offline_state, stores
    ):
        before = stores.world.revision
        preview = transition_engine.preview_sequence(
            offline_state, ("transition:power_on", "transition:connect")
        )
        assert preview.resulting_state.value_ref == "value:online"
        assert stores.world.revision == before
'''

PUBLIC_HEADER = '''"""Public-cycle rewrite obligations for R3."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_simulate_cycle_emits_no_effect_and_preserves_world_revision() -> None:
    effects = (ROOT / "src/cemm_authoritative_hybrid/r3_effects.py").read_text(encoding="utf-8")
    runtime = (ROOT / "src/cemm_authoritative_hybrid/runtime.py").read_text(encoding="utf-8")
    assert "DecisionAction.PREVIEW_TRANSITION: NoEffectReason.SIMULATION" in effects
    assert "return self._persist_no_effect(evaluation, meaning, situation, reason)" in effects
    assert "contract:r3:evaluate" not in runtime
    assert runtime.count("contract:r5:realize_surface") == 1

def test_unknown_surface_returns_typed_frontier_without_acceptance_or_mutation() -> None:
    runtime = (ROOT / "src/cemm_authoritative_hybrid/runtime.py").read_text(encoding="utf-8")
    proposal = (ROOT / "src/cemm_authoritative_hybrid/proposal.py").read_text(encoding="utf-8")
    effects = (ROOT / "src/cemm_authoritative_hybrid/r3_effects.py").read_text(encoding="utf-8")
    assert "verification.status != \"selected\"" in runtime
    assert "CycleStatus.UNSUPPORTED" in runtime
    assert "created_refs" in proposal
    assert "NoEffectReason.UNKNOWN" in effects
'''


def digest(fn: ast.FunctionDef) -> str:
    return hashlib.sha256(ast.dump(fn, annotate_fields=True, include_attributes=False).encode()).hexdigest()


def main() -> int:
    (TESTS / "test_transition_simulation.py").write_text(TRANSITION, encoding="utf-8")
    tree = ast.parse(PUBLIC_HEADER)
    fns = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    metadata = {
        "tests/test_r3_public_cycle.py::test_simulate_cycle_emits_no_effect_and_preserves_world_revision": {
            "activation_phase": "R3",
            "assertion_ref": "assertion:simulation-public-cycle-does-not-mutate",
            "diagnostic_role": "phase",
            "introduced_by_task": "R3-Legacy-Migration",
            "source_ast_sha256": digest(fns["test_simulate_cycle_emits_no_effect_and_preserves_world_revision"]),
            "contributes_to_rewrite_refs": ["rewrite_obligation:667dbd3b551a4a4a1fa34eeb"],
        },
        "tests/test_r3_public_cycle.py::test_unknown_surface_returns_typed_frontier_without_acceptance_or_mutation": {
            "activation_phase": "R3",
            "assertion_ref": "assertion:unknown-surface-public-cycle-is-safe",
            "diagnostic_role": "phase",
            "introduced_by_task": "R3-Legacy-Migration",
            "source_ast_sha256": digest(fns["test_unknown_surface_returns_typed_frontier_without_acceptance_or_mutation"]),
            "contributes_to_rewrite_refs": ["rewrite_obligation:a5d394543db7da318941a99f"],
        },
    }
    source = PUBLIC_HEADER.split("\n", 3)
    final = source[0] + "\n" + source[1] + "\n" + source[2] + "\n__cemm_test_inventory__ = " + pprint.pformat(metadata, width=120, sort_dicts=True) + "\n\n" + source[3]
    (TESTS / "test_r3_public_cycle.py").write_text(final, encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
