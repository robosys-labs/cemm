"""CEMM v3.5 semantic schema metamodel."""
from .codec import (
    SchemaDecodeError,
    entitlement_from_document,
    record_from_document,
    record_to_document,
    schema_from_document,
)
from .model import *  # noqa: F401,F403
from .registry import (
    DuplicateRevisionError,
    InheritanceCycleError,
    SchemaRegistry,
    SchemaRegistryError,
    ValidationIssue,
    ValidationReport,
)

__all__ = [
    "SchemaDecodeError",
    "entitlement_from_document",
    "record_from_document",
    "record_to_document",
    "schema_from_document",
    "DuplicateRevisionError",
    "InheritanceCycleError",
    "SchemaRegistry",
    "SchemaRegistryError",
    "ValidationIssue",
    "ValidationReport",
]
