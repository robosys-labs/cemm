from pathlib import Path


def test_patch_replaces_deterministic_stage6_7_and_installs_phase14_stage11_13_services():
    root = Path(__file__).resolve().parents[2]
    script = (root / "apply_phases13_14.py").read_text(encoding="utf-8")
    assert '"recurrent_semantic_solver": RecurrentSemanticDynamicsV351()' in script
    assert '"semantic_attractor_stabilizer": RecurrentAttractorStabilizerV351()' in script
    assert '"learning_engine": Phase14LearningEngineV351()' in script
    assert '"commit_coordinator": Stage13LearningCommitterV351(self.session_memory)' in script
    assert "DeterministicMeaningDynamics()," in script  # appears only as the exact old anchor being replaced
    assert "evidence_lattice=cycle.artifacts.get(\"evidence_lattice\")" in script


def test_phase14_runtime_code_contains_no_nonce_or_concept_specific_handler():
    root = Path(__file__).resolve().parents[2]
    production = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "cemm/v350/learning").glob("*_v351.py")
    ).casefold()
    for forbidden in ("zorb", "nuvra-7f31", "if text ==", "subject ->", "object ->"):
        assert forbidden not in production


def test_phase14_automatic_competence_requires_package_pinned_executor_identity():
    root = Path(__file__).resolve().parents[2]
    source = (root / "cemm/v350/learning/maintenance_v351.py").read_text(encoding="utf-8")
    assert 'competence_executor_pins' in source
    assert 'COMPETENCE_RUNNER_REF' in source
    assert 'COMPETENCE_RUNNER_REVISION' in source
    assert 'competence-executor-pin-required' in source
