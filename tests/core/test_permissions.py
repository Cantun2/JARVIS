"""Enforcer : MAIL_SEND jamais accordée ; granted = déclarées − interdites."""

from __future__ import annotations

import pytest

from jarvis.core.contracts import AgentContract, AgentInput, AgentOutput, Permission
from jarvis.core.errors import PermissionDenied
from jarvis.core.permissions import PermissionEnforcer


def _contract(*perms: Permission) -> AgentContract:
    return AgentContract(
        name="t",
        mode="on_demand",
        permissions=perms,
        inputs=AgentInput,
        outputs=AgentOutput,
    )


def test_mail_send_is_denied(enforcer: PermissionEnforcer) -> None:
    with pytest.raises(PermissionDenied, match=r"mail\.send"):
        enforcer.check(_contract(Permission.MAIL_READ, Permission.MAIL_SEND))


def test_allowed_permissions_pass(enforcer: PermissionEnforcer) -> None:
    enforcer.check(_contract(Permission.MAIL_READ, Permission.DESKTOP_LAUNCH))  # ne lève pas


def test_granted_excludes_denied(enforcer: PermissionEnforcer) -> None:
    granted = enforcer.granted(_contract(Permission.MAIL_READ, Permission.NOTIFY_TELEGRAM))
    assert granted == frozenset({Permission.MAIL_READ, Permission.NOTIFY_TELEGRAM})
