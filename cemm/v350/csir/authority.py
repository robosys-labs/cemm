"""Pinned Kernel Semantic ABI for CEMM v3.5.1 CSIR v2.

The ABI fingerprint is part of semantic identity.  A graph normalized under one
kernel/canonicalizer ABI is never silently compared as equivalent under another.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class KernelSemanticABI:
    kernel_semantic_abi: str
    serialization_abi: str
    canonicalization_abi: str
    normalizer_abi: str
    operations_abi: str
    compiler_barrier_abi: str

    def __post_init__(self) -> None:
        for name in (
            "kernel_semantic_abi",
            "serialization_abi",
            "canonicalization_abi",
            "normalizer_abi",
            "operations_abi",
            "compiler_barrier_abi",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")

    @property
    def fingerprint(self) -> str:
        return _hash(
            {
                "kernel_semantic_abi": self.kernel_semantic_abi,
                "serialization_abi": self.serialization_abi,
                "canonicalization_abi": self.canonicalization_abi,
                "normalizer_abi": self.normalizer_abi,
                "operations_abi": self.operations_abi,
                "compiler_barrier_abi": self.compiler_barrier_abi,
            }
        )


CURRENT_KERNEL_ABI = KernelSemanticABI(
    kernel_semantic_abi="cemm-csir-kernel-v2",
    serialization_abi="cemm-csir-json-v2",
    canonicalization_abi="cemm-csir-canonical-label-v2",
    normalizer_abi="cemm-csir-normal-form-v2",
    operations_abi="cemm-csir-kernel-ops-v2",
    compiler_barrier_abi="cemm-stage5-exact-csir-compiler-v2",
)

KERNEL_SEMANTIC_ABI = CURRENT_KERNEL_ABI.kernel_semantic_abi
CSIR_SERIALIZATION_ABI = CURRENT_KERNEL_ABI.serialization_abi
CSIR_CANONICALIZATION_ABI = CURRENT_KERNEL_ABI.canonicalization_abi
CSIR_NORMALIZER_ABI = CURRENT_KERNEL_ABI.normalizer_abi
CSIR_OPERATIONS_ABI = CURRENT_KERNEL_ABI.operations_abi
CSIR_COMPILER_BARRIER_ABI = CURRENT_KERNEL_ABI.compiler_barrier_abi


def require_kernel_abi(fingerprint: str) -> None:
    if fingerprint != CURRENT_KERNEL_ABI.fingerprint:
        raise ValueError(
            "CSIR kernel ABI mismatch: expected "
            f"{CURRENT_KERNEL_ABI.fingerprint}, got {fingerprint}"
        )


__all__ = [
    "CSIR_CANONICALIZATION_ABI",
    "CSIR_COMPILER_BARRIER_ABI",
    "CSIR_NORMALIZER_ABI",
    "CSIR_OPERATIONS_ABI",
    "CSIR_SERIALIZATION_ABI",
    "CURRENT_KERNEL_ABI",
    "KERNEL_SEMANTIC_ABI",
    "KernelSemanticABI",
    "require_kernel_abi",
]
