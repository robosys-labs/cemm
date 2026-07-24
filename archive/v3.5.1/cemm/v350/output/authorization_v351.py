"""Typed Phase-12 disclosure authorization contracts.

A channel contract is transport authority, not disclosure authority.  Disclosure grants are
immutable, content-addressed auxiliary authority in the Stage-0 ``AuthoritySnapshotV351`` and
are additionally backed by exact durable substrate pins checked by the effect boundary.

The contract intentionally uses structural audience selectors rather than hard-coded user IDs:
a reviewed grant may authorize the current ParticipantFrame response audience, or an exact
static audience set.  It never broadens context/permission scope and never authorizes emission
without the separate channel contract and Stage-20 semantic-preservation proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from ..csir.authority_v351 import AuthoritySnapshotV351
from ..csir.model import ExactAuthorityPin
from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint


class DisclosureAuthorizationError(ValueError):
    pass


class DisclosureDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class DisclosureAudienceMode(str, Enum):
    """Stable structural audience selectors; not a domain ontology."""

    RESPONSE_AUDIENCE = "response_audience"
    EXACT_SET = "exact_set"


@dataclass(frozen=True, slots=True)
class DisclosureAuthorizationGrantV351:
    """Exact reviewed grant for protected conversational disclosure.

    ``grant_pin`` must be present exactly in ``AuthoritySnapshotV351.auxiliary_exact_pins`` and
    its ``content_hash`` must equal ``content_fingerprint``.  The grant itself therefore cannot
    be swapped or edited mid-pass. ``substrate_pins`` identify the durable policy/competence/
    release records whose existence and exact fingerprints are rechecked by Stage 20's effect
    boundary before any disclosure or external emission.
    """

    grant_pin: ExactAuthorityPin
    decision: DisclosureDecision
    channel_refs: tuple[str, ...]
    permission_refs: tuple[str, ...]
    context_refs: tuple[str, ...] = ()
    audience_mode: DisclosureAudienceMode = DisclosureAudienceMode.RESPONSE_AUDIENCE
    exact_audience_refs: tuple[str, ...] = ()
    language_tags: tuple[str, ...] = ()
    substrate_pins: tuple[PinnedRecord, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    active: bool = False

    def __post_init__(self) -> None:
        if self.grant_pin.kind != "disclosure_authorization":
            raise DisclosureAuthorizationError(
                "disclosure grant pin kind must be disclosure_authorization"
            )
        for values, label in (
            (self.channel_refs, "channel refs"),
            (self.permission_refs, "permission refs"),
            (self.context_refs, "context refs"),
            (self.exact_audience_refs, "exact audience refs"),
            (self.language_tags, "language tags"),
            (self.evidence_refs, "evidence refs"),
        ):
            if len(values) != len(set(values)):
                raise DisclosureAuthorizationError(f"duplicate disclosure {label}")
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise DisclosureAuthorizationError(f"disclosure {label} must be non-empty refs")
        if not self.channel_refs:
            raise DisclosureAuthorizationError("disclosure grant requires explicit channel scope")
        if not self.permission_refs:
            raise DisclosureAuthorizationError("disclosure grant requires explicit permission scope")
        if self.audience_mode is DisclosureAudienceMode.EXACT_SET and not self.exact_audience_refs:
            raise DisclosureAuthorizationError("exact-set disclosure grant requires exact audience refs")
        if self.audience_mode is DisclosureAudienceMode.RESPONSE_AUDIENCE and self.exact_audience_refs:
            raise DisclosureAuthorizationError(
                "response-audience disclosure grant cannot also carry exact audience refs"
            )
        if not self.substrate_pins:
            raise DisclosureAuthorizationError(
                "disclosure grant requires exact durable policy/competence substrate pins"
            )
        substrate_keys = tuple((pin.key, pin.record_fingerprint) for pin in self.substrate_pins)
        if len(substrate_keys) != len(set(substrate_keys)):
            raise DisclosureAuthorizationError("duplicate disclosure substrate pins")
        if self.active and not self.evidence_refs:
            raise DisclosureAuthorizationError("active disclosure grant requires review/competence evidence")

    @property
    def content_fingerprint(self) -> str:
        # The pin's own content_hash is deliberately excluded to avoid circular hashing.
        pin_identity = (
            self.grant_pin.kind,
            self.grant_pin.namespace,
            self.grant_pin.ref,
            self.grant_pin.revision,
            self.grant_pin.scope_ref,
        )
        return semantic_fingerprint(
            "disclosure-authorization-grant-v351",
            (
                pin_identity,
                self.decision.value,
                tuple(sorted(self.channel_refs)),
                tuple(sorted(self.permission_refs)),
                tuple(sorted(self.context_refs)),
                self.audience_mode.value,
                tuple(sorted(self.exact_audience_refs)),
                tuple(sorted(self.language_tags)),
                tuple(sorted((pin.key, pin.record_fingerprint) for pin in self.substrate_pins)),
                tuple(sorted(self.evidence_refs)),
                self.active,
            ),
            64,
        )

    def validate_exact_authority(self, snapshot: AuthoritySnapshotV351) -> None:
        snapshot.require_known_pin(self.grant_pin)
        if self.grant_pin.content_hash != self.content_fingerprint:
            raise DisclosureAuthorizationError(
                "disclosure grant content fingerprint differs from exact authority pin"
            )

    def matches(self, *, cycle, selected_candidate) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        if not self.active:
            reasons.append("disclosure_grant_inactive")
        if self.decision is not DisclosureDecision.ALLOW:
            reasons.append("disclosure_grant_not_allow")
        if str(cycle.channel_ref) not in set(self.channel_refs):
            reasons.append("disclosure_channel_out_of_scope")
        if str(cycle.permission_ref) not in set(self.permission_refs):
            reasons.append("disclosure_permission_out_of_scope")
        if self.context_refs and str(cycle.context_ref) not in set(self.context_refs):
            reasons.append("disclosure_context_out_of_scope")
        language = str(getattr(selected_candidate, "language_tag", "") or "")
        if self.language_tags and language not in set(self.language_tags):
            reasons.append("disclosure_language_out_of_scope")

        requested = tuple(sorted(set(tuple(getattr(cycle, "audience_refs", ()) or ()))))
        if not requested:
            reasons.append("disclosure_requires_explicit_audience")
        elif self.audience_mode is DisclosureAudienceMode.EXACT_SET:
            if set(requested) != set(self.exact_audience_refs):
                reasons.append("disclosure_exact_audience_mismatch")
        else:
            frame = cycle.artifacts.get("participant_frame") if hasattr(cycle, "artifacts") else None
            response_audience = tuple(sorted(set(tuple(getattr(frame, "response_audience_refs", ()) or ()))))
            if not response_audience or not set(requested).issubset(set(response_audience)):
                reasons.append("disclosure_audience_not_response_participant")
        return not reasons, tuple(sorted(set(reasons)))


def build_disclosure_authorization_grant_pin(
    *,
    ref: str,
    revision: int,
    namespace: str,
    scope_ref: str,
    decision: DisclosureDecision,
    channel_refs: Iterable[str],
    permission_refs: Iterable[str],
    context_refs: Iterable[str] = (),
    audience_mode: DisclosureAudienceMode = DisclosureAudienceMode.RESPONSE_AUDIENCE,
    exact_audience_refs: Iterable[str] = (),
    language_tags: Iterable[str] = (),
    substrate_pins: Iterable[PinnedRecord],
    evidence_refs: Iterable[str],
    active: bool,
) -> DisclosureAuthorizationGrantV351:
    """Construct a self-consistent content-addressed grant for release tooling/tests."""

    placeholder = ExactAuthorityPin(
        "disclosure_authorization", namespace, ref, revision, "pending", scope_ref
    )
    draft = DisclosureAuthorizationGrantV351(
        grant_pin=placeholder,
        decision=decision,
        channel_refs=tuple(channel_refs),
        permission_refs=tuple(permission_refs),
        context_refs=tuple(context_refs),
        audience_mode=audience_mode,
        exact_audience_refs=tuple(exact_audience_refs),
        language_tags=tuple(language_tags),
        substrate_pins=tuple(substrate_pins),
        evidence_refs=tuple(evidence_refs),
        active=active,
    )
    pin = ExactAuthorityPin(
        "disclosure_authorization", namespace, ref, revision, draft.content_fingerprint, scope_ref
    )
    return DisclosureAuthorizationGrantV351(
        grant_pin=pin,
        decision=decision,
        channel_refs=tuple(channel_refs),
        permission_refs=tuple(permission_refs),
        context_refs=tuple(context_refs),
        audience_mode=audience_mode,
        exact_audience_refs=tuple(exact_audience_refs),
        language_tags=tuple(language_tags),
        substrate_pins=tuple(substrate_pins),
        evidence_refs=tuple(evidence_refs),
        active=active,
    )


__all__ = [
    "DisclosureAudienceMode",
    "DisclosureAuthorizationError",
    "DisclosureAuthorizationGrantV351",
    "DisclosureDecision",
    "build_disclosure_authorization_grant_pin",
]
