"""AuthorityGeneration-owned semantic applicability indexes.

This module removes vocabulary-size scans from the Stage-4 hot path. It indexes exact,
ACTIVE property definitions by holder type once per immutable authority generation.
The index contains no world facts and makes no applicability assertion by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..schema.model import SchemaClass


@dataclass(frozen=True, slots=True)
class SchemaApplicabilityIndex:
    authority_generation: int
    authority_fingerprint: str
    property_pins_by_holder_type: Mapping[str, tuple[tuple[str, int], ...]]
    unrestricted_property_pins: tuple[tuple[str, int], ...] = ()

    @classmethod
    def build(
        cls,
        registry,
        *,
        authority_generation: int,
        authority_fingerprint: str,
    ) -> "SchemaApplicabilityIndex":
        if authority_generation < 1 or not authority_fingerprint:
            raise ValueError("applicability index requires exact AuthorityGeneration")
        by_type: dict[str, set[tuple[str, int]]] = {}
        unrestricted: set[tuple[str, int]] = set()
        for schema in registry.active_schemas(SchemaClass.PROPERTY):
            pin = (schema.schema_ref, schema.revision)
            holder_types = tuple(sorted(set(getattr(schema, "holder_type_refs", ()) or ())))
            if not holder_types:
                unrestricted.add(pin)
                continue
            for holder_type in holder_types:
                by_type.setdefault(holder_type, set()).add(pin)
        return cls(
            authority_generation=authority_generation,
            authority_fingerprint=authority_fingerprint,
            property_pins_by_holder_type={
                key: tuple(sorted(value)) for key, value in sorted(by_type.items())
            },
            unrestricted_property_pins=tuple(sorted(unrestricted)),
        )

    def property_schemas_for_types(self, type_refs, registry):
        pins = set(self.unrestricted_property_pins)
        for type_ref in set(type_refs):
            pins.update(self.property_pins_by_holder_type.get(type_ref, ()))
        return tuple(registry.schema(ref, revision) for ref, revision in sorted(pins))


__all__ = ["SchemaApplicabilityIndex"]
