from cemm.kernel.invariant_guard import InvariantGuard
from cemm.registry.uol_mapper import UOLMapper
from cemm.registry import Registry, RegistryEntry
from cemm.types.context_kernel import ContextKernel


def test_uol_mapping_does_not_create_factual_claims():
    """Invariant: language-specific grammar labels bypass UOL process/state registry."""
    reg = Registry()
    reg.register(RegistryEntry(
        model_id="uol_assert", canonical_key="assert_evaluation",
        kind="uol_semantic",
    ))
    reg.register(RegistryEntry(
        model_id="uol_low_comp", canonical_key="low_competence",
        kind="uol_semantic",
    ))
    mapper = UOLMapper(reg)
    kernel = ContextKernel(id="test")
    atoms = mapper.map_signal("you are dumb", kernel)
    guard = InvariantGuard()
    guard.reset()
    guard.check_uol_not_bypassing_registry(atoms, reg)
    errors = guard.assert_no_errors()
    assert len(errors) == 0
