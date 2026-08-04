import dataclasses

import pytest

from cemm_authoritative_hybrid.config import ABIRegistry, RuntimeConfig


def test_release_configuration_is_frozen_and_bounded():
    config = RuntimeConfig.release()
    assert config.abis == ABIRegistry(1, 1, 1, 1, 1, 1, 1, 1)
    assert config.max_input_tokens == 64
    assert config.max_complete_candidates == 48
    assert config.max_applications == 24
    assert config.max_graph_depth == 6
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.max_graph_depth = 7
