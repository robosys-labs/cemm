import dataclasses

import pytest

from cemm_authoritative_hybrid.config import ABIRegistry, RuntimeConfig

__cemm_test_inventory__ = {
    "tests/test_config.py::test_current_release_configuration_is_frozen_and_bounded": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:config-release-configuration-is-frozen-and-bounded",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "Foundation-Task-5",
        "source_ast_sha256": "b8f1c5c779a4d32044f6195591633ac223e94d7e39dfc87f21e7b09eaed7d417",
        "supersedes_node_id": "tests/test_config.py::test_release_configuration_is_frozen_and_bounded",
    },
}


def test_current_release_configuration_is_frozen_and_bounded():
    config = RuntimeConfig.release()
    assert config.abis == ABIRegistry(1, 2, 2, 2, 1, 3, 3, 2)
    assert config.max_input_tokens == 64
    assert config.max_complete_candidates == 48
    assert config.max_applications == 24
    assert config.max_graph_depth == 6
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.max_graph_depth = 7
