"""Exact non-semantic use authority helpers for Phase-16 causal policies.

Semantic identity and executable use remain separate.  A policy/projection/adapter pin being
present in an AuthorityGeneration proves exact identity only; a matching per-use ALLOW is still
required for the concrete context and permission.  DENY always dominates ALLOW.
"""
from __future__ import annotations

from ..csir.authority_v351 import AuthoritySnapshotV351
from ..csir.model import ExactAuthorityPin


class CausalUseAuthorityError(PermissionError):
    pass


def require_exact_use(
    snapshot: AuthoritySnapshotV351,
    target_pin: ExactAuthorityPin,
    *,
    operation: str,
    context_ref: str,
    permission_ref: str,
) -> tuple[ExactAuthorityPin, ...]:
    if not isinstance(snapshot, AuthoritySnapshotV351):
        raise CausalUseAuthorityError("pinned AuthoritySnapshotV351 required")
    snapshot.require_known_pin(target_pin)
    matching = tuple(
        item for item in snapshot.use_authorizations
        if item.target_pin.key == target_pin.key
        and item.operation == operation
        and (
            not item.context_scopes
            or context_ref in item.context_scopes
            or "global" in item.context_scopes
        )
        and (
            not item.permission_scopes
            or permission_ref in item.permission_scopes
            or "public" in item.permission_scopes
            or "global" in item.permission_scopes
        )
    )
    if any(item.decision.casefold() == "deny" for item in matching):
        raise CausalUseAuthorityError(f"exact {operation} use explicitly denied:{target_pin.key}")
    allowed = tuple(item for item in matching if item.decision.casefold() == "allow")
    if not allowed:
        raise CausalUseAuthorityError(f"exact {operation} use authorization missing:{target_pin.key}")
    return tuple(item.authorization_pin for item in allowed)


def require_authorization_pins(
    snapshot: AuthoritySnapshotV351,
    authorization_pins: tuple[ExactAuthorityPin, ...],
    *,
    allowed_operations: tuple[str, ...],
    context_ref: str,
    permission_ref: str,
) -> tuple[ExactAuthorityPin, ...]:
    """Validate cycle-supplied exact UseAuthorization identities.

    This is used for interventions/counterfactual operators whose assignment carries the
    authorization identity itself rather than the target policy pin. Every supplied pin must
    resolve to an ALLOW authorization in the pinned generation and be in scope.
    """
    if not isinstance(snapshot, AuthoritySnapshotV351):
        raise CausalUseAuthorityError("pinned AuthoritySnapshotV351 required")
    if not authorization_pins:
        raise CausalUseAuthorityError("exact authorization pins required")
    by_key = {item.authorization_pin.key: item for item in snapshot.use_authorizations}
    validated = []
    for pin in authorization_pins:
        snapshot.require_known_pin(pin)
        item = by_key.get(pin.key)
        if item is None:
            raise CausalUseAuthorityError(f"pin is not an exact UseAuthorization:{pin.key}")
        if item.operation not in allowed_operations:
            raise CausalUseAuthorityError(
                f"authorization operation {item.operation} is not valid for this causal use"
            )
        if item.decision.casefold() != "allow":
            raise CausalUseAuthorityError("causal use authorization is not ALLOW")
        if item.context_scopes and context_ref not in item.context_scopes and "global" not in item.context_scopes:
            raise CausalUseAuthorityError("causal use authorization is outside context scope")
        if (
            item.permission_scopes
            and permission_ref not in item.permission_scopes
            and "public" not in item.permission_scopes
            and "global" not in item.permission_scopes
        ):
            raise CausalUseAuthorityError("causal use authorization widens permission scope")
        validated.append(pin)
    return tuple(validated)


__all__ = ["CausalUseAuthorityError", "require_authorization_pins", "require_exact_use"]
