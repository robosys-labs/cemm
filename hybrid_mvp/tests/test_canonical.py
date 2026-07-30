from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import torch

from cemm_authoritative_hybrid.canonical import (
    canonical_bytes,
    stable_ref,
    tensor_identity,
)


def test_mapping_order_does_not_change_identity():
    assert canonical_bytes({"b": 2, "a": 1}) == canonical_bytes({"a": 1, "b": 2})
    assert stable_ref("fact", {"b": 2, "a": 1}) == stable_ref("fact", {"a": 1, "b": 2})


def test_type_tags_distinguish_values():
    assert canonical_bytes(1) != canonical_bytes("1")
    assert canonical_bytes(1) != canonical_bytes(1.0)
    assert canonical_bytes(True) != canonical_bytes(1)
    assert canonical_bytes(None) != canonical_bytes(False)


def test_set_and_frozenset_order_independent():
    assert canonical_bytes({2, 1, 3}) == canonical_bytes({3, 1, 2})
    assert canonical_bytes(frozenset({2, 1, 3})) == canonical_bytes(frozenset({3, 1, 2}))


def test_tuple_and_list_keep_order():
    assert canonical_bytes((1, 2, 3)) != canonical_bytes((3, 2, 1))
    assert canonical_bytes([1, 2]) != canonical_bytes((1, 2))


def test_decimal_canonical():
    assert canonical_bytes(Decimal("1.0")) == canonical_bytes(Decimal("1.0"))
    assert canonical_bytes(Decimal("1.0")) != canonical_bytes(Decimal("1.00"))


def test_nested_mapping_sorted_recursively():
    assert canonical_bytes({"z": {"d": 1, "a": 2}, "a": 3}) == canonical_bytes(
        {"a": 3, "z": {"a": 2, "d": 1}}
    )


def test_dataclass_canonical_by_sorted_fields():
    @dataclass
    class Point:
        y: int
        x: int

    assert canonical_bytes(Point(1, 2)) == canonical_bytes(Point(1, 2))
    assert canonical_bytes(Point(1, 2)) != canonical_bytes(Point(2, 1))


def test_stable_ref_namespace_isolates():
    assert stable_ref("fact", {"a": 1}) != stable_ref("rule", {"a": 1})


def test_tensor_identity_is_byte_and_shape_deterministic():
    a = {"w": torch.zeros(2, 2), "b": torch.ones(2)}
    b = {"b": torch.ones(2), "w": torch.zeros(2, 2)}
    assert tensor_identity(a) == tensor_identity(b)


def test_tensor_identity_changes_on_byte_tamper():
    t = torch.zeros(2, 2)
    original = tensor_identity({"w": t})
    t2 = t.clone()
    t2[0, 0] = 1.0
    assert tensor_identity({"w": t2}) != original


def test_tensor_identity_changes_on_shape():
    assert tensor_identity({"w": torch.zeros(2, 2)}) != tensor_identity(
        {"w": torch.zeros(2, 3)}
    )


def test_tensor_identity_changes_on_dtype():
    assert tensor_identity({"w": torch.zeros(2, 2)}) != tensor_identity(
        {"w": torch.zeros(2, 2, dtype=torch.float64)}
    )
