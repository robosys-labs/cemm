"""TransmutationAuthorizer — sole authority for state-transition permission.

A state delta is not a state update. Only an authorized and successfully
applied transition changes occupancy.

Checks:
1. Contract provenance exists (frame_id from an authorized contract)
2. Authority is not untrusted
3. Transmutation kind is not predicted/rejected
4. Persistence policy is not quarantine/reject
5. State family and dimension are valid
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..types.state_transmutation import (
    StateTransmutationFrame,
    STATE_FAMILIES,
    DIRECTIONS,
)


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    """Result of authorizing a state transmutation."""
    transmutation_id: str
    authorized: bool
    reason: str = ""
    applied_persistence: str = ""


class TransmutationAuthorizer:
    """Sole authority for state-transition permission.

    Compilation proposes; authorizing permits; transactional application
    changes occupancy.
    """

    _REJECTED_KINDS = frozenset({"predicted", "rejected"})
    _REJECTED_AUTHORITIES = frozenset({"untrusted"})
    _REJECTED_PERSISTENCE = frozenset({"quarantine", "reject"})

    def authorize(
        self,
        transmutation: StateTransmutationFrame,
        contract_provenance: dict[str, Any] | None,
    ) -> AuthorizationResult:
        tid = transmutation.transmutation_id

        if contract_provenance is None:
            return AuthorizationResult(tid, False, "no contract provenance")

        frame_id = contract_provenance.get("frame_id", "")
        if not frame_id:
            return AuthorizationResult(tid, False, "contract provenance missing frame_id")

        if transmutation.authority in self._REJECTED_AUTHORITIES:
            return AuthorizationResult(
                tid, False,
                f"authority '{transmutation.authority}' is not trusted for state application",
            )

        if transmutation.transmutation_kind in self._REJECTED_KINDS:
            return AuthorizationResult(
                tid, False,
                f"transmutation kind '{transmutation.transmutation_kind}' cannot be applied",
            )

        if transmutation.persistence_policy in self._REJECTED_PERSISTENCE:
            return AuthorizationResult(
                tid, False,
                f"persistence policy '{transmutation.persistence_policy}' blocks application",
            )

        if transmutation.state_family and transmutation.state_family not in STATE_FAMILIES:
            return AuthorizationResult(
                tid, False,
                f"unknown state family '{transmutation.state_family}'",
            )

        if transmutation.direction and transmutation.direction not in DIRECTIONS:
            return AuthorizationResult(
                tid, False,
                f"unknown direction '{transmutation.direction}'",
            )

        return AuthorizationResult(
            tid, True, "",
            applied_persistence=transmutation.persistence_policy,
        )
