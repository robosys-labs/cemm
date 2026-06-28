import pytest
from cemm.types.permission import Permission, PermissionScope, RetentionPolicy


class TestPermissions:
    def test_public_defaults(self):
        p = Permission.public()
        assert p.scope == PermissionScope.PUBLIC
        assert p.may_store
        assert p.may_retrieve
        assert p.may_use
        assert not p.may_share
        assert p.may_execute

    def test_user_private_defaults(self):
        p = Permission.user_private()
        assert p.scope == PermissionScope.USER_PRIVATE
        assert p.may_store
        assert not p.may_share
        assert not p.may_execute
        assert p.retention == RetentionPolicy.SESSION

    def test_session_private_defaults(self):
        p = Permission.session_private()
        assert p.scope == PermissionScope.SESSION_PRIVATE
        assert p.retention == RetentionPolicy.EPHEMERAL
        assert not p.may_execute

    def test_execution_gated(self):
        p = Permission.public()
        assert p.may_execute
        p2 = Permission(scope=PermissionScope.USER_PRIVATE)
        assert not p2.may_execute
