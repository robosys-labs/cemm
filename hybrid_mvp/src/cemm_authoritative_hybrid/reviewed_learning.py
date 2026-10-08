"""Authenticated, externally reviewed learning decision (no chat minting).

Signing is reserved for a separate authenticated reviewer service. The
cognitive runtime ONLY receives ReviewApproval and a verifier with externally
provisioned keys; neither the user utterance nor the neural proposer supplies
a signing key. HMAC is a server-to-server trust boundary, not user login.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import secrets
from typing import Mapping

from .canonical import stable_ref

POLICY = "policy:reviewed_designation:v1"
MAX_REVIEW_SECONDS = 3600


def _text(value: object, name: str, maximum: int = 512) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ValueError(f"{name} must be a bounded, nonempty string")
    return value


def _key(key: object) -> bytes:
    if type(key) is not bytes or len(key) < 32:
        raise ValueError("reviewer verifier key must be at least 32 bytes")
    return key


@dataclass(frozen=True, slots=True)
class ReviewApproval:
    policy_ref: str
    reviewer_ref: str
    plan_ref: str
    obligation_ref: str
    source_effect_ref: str
    session_ref: str
    nonce: str
    issued_at: int
    expires_at: int
    signature: str

    def __post_init__(self) -> None:
        for name in (
            "policy_ref", "reviewer_ref", "plan_ref", "obligation_ref",
            "source_effect_ref", "session_ref",
        ):
            _text(getattr(self, name), name)
        if (
            type(self.nonce) is not str or len(self.nonce) != 48
            or any(c not in "0123456789abcdef" for c in self.nonce)
        ):
            raise ValueError("review nonce must be a 192-bit lowercase hex string")
        if type(self.issued_at) is not int or type(self.expires_at) is not int:
            raise TypeError("review timestamps must be exact integers")
        if not 0 < self.expires_at - self.issued_at <= MAX_REVIEW_SECONDS:
            raise ValueError("review validity window must be short and positive")
        if type(self.signature) is not str or len(self.signature) != 64 or any(
            c not in "0123456789abcdef" for c in self.signature
        ):
            raise ValueError("review signature must be lowercase SHA-256 hex")

    @property
    def approval_ref(self) -> str:
        return stable_ref(
            "review_approval", {
                **self.signing_fields(),
                "signature": self.signature,
            },
        )

    def signing_fields(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in (
                "policy_ref", "reviewer_ref", "plan_ref", "obligation_ref",
                "source_effect_ref", "session_ref", "nonce", "issued_at",
                "expires_at",
            )
        }

    def signing_bytes(self) -> bytes:
        return json.dumps(
            self.signing_fields(), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")


def _sign(key: bytes, approval: ReviewApproval) -> str:
    return hmac.new(_key(key), approval.signing_bytes(), hashlib.sha256).hexdigest()


class ReviewerIssuer:
    """Use ONLY within an independently authenticated reviewer service."""

    def __init__(self, reviewer_ref: str, key: bytes, policy_ref: str = POLICY):
        self.reviewer_ref = _text(reviewer_ref, "reviewer_ref")
        self.policy_ref = _text(policy_ref, "policy_ref")
        self.__key = _key(key)

    def approve(
        self, *, plan_ref: str, obligation_ref: str, source_effect_ref: str,
        session_ref: str, issued_at: int, lifetime: int = 300,
    ) -> ReviewApproval:
        if type(lifetime) is not int or not 0 < lifetime <= MAX_REVIEW_SECONDS:
            raise ValueError("invalid approval lifetime")
        approval = ReviewApproval(
            policy_ref=self.policy_ref, reviewer_ref=self.reviewer_ref,
            plan_ref=plan_ref, obligation_ref=obligation_ref,
            source_effect_ref=source_effect_ref, session_ref=session_ref,
            nonce=secrets.token_hex(24), issued_at=issued_at,
            expires_at=issued_at + lifetime, signature="0" * 64,
        )
        return replace(approval, signature=_sign(self.__key, approval))


class ReviewerVerifier:
    """Read-only reviewer allowlist; keys supplied by trusted deployment."""

    def __init__(
        self, reviewer_keys: Mapping[str, bytes], policy_ref: str = POLICY,
    ) -> None:
        self.policy_ref = _text(policy_ref, "policy_ref")
        if not reviewer_keys:
            raise ValueError("at least one approved reviewer key is required")
        self.__keys = {
            _text(ref, "reviewer_ref"): _key(key)
            for ref, key in reviewer_keys.items()
        }

    def verify(self, approval: ReviewApproval, *, now: int) -> None:
        if type(approval) is not ReviewApproval:
            raise TypeError("review must be an exact ReviewApproval")
        if type(now) is not int or not approval.issued_at <= now <= approval.expires_at:
            raise PermissionError("review approval is not currently valid")
        if approval.policy_ref != self.policy_ref:
            raise PermissionError("reviewer policy does not match")
        secret = self.__keys.get(approval.reviewer_ref)
        if secret is None or not hmac.compare_digest(
            _sign(secret, approval), approval.signature
        ):
            raise PermissionError("review approval is unauthorized")
