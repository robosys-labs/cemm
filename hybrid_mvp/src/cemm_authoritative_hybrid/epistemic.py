"""Closed canonical epistemic-status identities shared by semantic owners."""

from __future__ import annotations


EPISTEMIC_STATUS_REFS = frozenset(
    {
        "epistemic_status:attributed",
        "epistemic_status:conflict",
        "epistemic_status:contested",
        "epistemic_status:contradicted",
        "epistemic_status:denied",
        "epistemic_status:observed",
        "epistemic_status:partial",
        "epistemic_status:pending",
        "epistemic_status:simulated",
        "epistemic_status:supported",
        "epistemic_status:unknown",
    }
)


def exact_epistemic_status_ref(value: object) -> str:
    """Return one reviewed canonical status ref or fail at its earliest owner."""

    if type(value) is not str or not value:
        raise TypeError("epistemic_status_ref must be exact nonempty str")
    if value not in EPISTEMIC_STATUS_REFS:
        raise ValueError("epistemic_status_ref is not a canonical reviewed identity")
    return value


__all__ = ["EPISTEMIC_STATUS_REFS", "exact_epistemic_status_ref"]
