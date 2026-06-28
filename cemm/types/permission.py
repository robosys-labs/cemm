from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class PermissionScope(str, Enum):
    PUBLIC = "public"
    USER_PRIVATE = "user_private"
    SESSION_PRIVATE = "session_private"
    SYSTEM_PRIVATE = "system_private"


class RetentionPolicy(str, Enum):
    EPHEMERAL = "ephemeral"
    SESSION = "session"
    LONG_TERM = "long_term"


@dataclass
class Permission:
    scope: PermissionScope = PermissionScope.PUBLIC
    may_store: bool = True
    may_retrieve: bool = True
    may_use: bool = True
    may_share: bool = False
    may_execute: bool = False
    retention: RetentionPolicy = RetentionPolicy.LONG_TERM

    @classmethod
    def public(cls) -> "Permission":
        return cls(
            scope=PermissionScope.PUBLIC,
            may_store=True, may_retrieve=True, may_use=True,
            may_share=False, may_execute=True,
            retention=RetentionPolicy.LONG_TERM,
        )

    @classmethod
    def user_private(cls) -> "Permission":
        return cls(
            scope=PermissionScope.USER_PRIVATE,
            may_store=True, may_retrieve=True, may_use=True,
            may_share=False, may_execute=False,
            retention=RetentionPolicy.SESSION,
        )

    @classmethod
    def session_private(cls) -> "Permission":
        return cls(
            scope=PermissionScope.SESSION_PRIVATE,
            may_store=True, may_retrieve=True, may_use=True,
            may_share=False, may_execute=False,
            retention=RetentionPolicy.EPHEMERAL,
        )
