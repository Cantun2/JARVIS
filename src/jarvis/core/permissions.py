"""Point d'enforcement unique des permissions.

Appelé exclusivement par l'orchestrateur. La policy décide quelles permissions
peuvent être accordées ; certaines (ex. MAIL_SEND) ne le sont jamais par défaut.
"""

from __future__ import annotations

from jarvis.core.contracts import AgentContract, Permission
from jarvis.core.errors import PermissionDenied

# Permissions jamais accordées automatiquement, même si un agent les déclare.
DEFAULT_DENIED: frozenset[Permission] = frozenset({Permission.MAIL_SEND})


class PermissionEnforcer:
    """Vérifie les contrats et calcule l'ensemble effectif de permissions accordées."""

    def __init__(self, denied: frozenset[Permission] = DEFAULT_DENIED) -> None:
        self._denied = denied

    def check(self, contract: AgentContract) -> None:
        """Lève PermissionDenied si le contrat demande une permission interdite."""
        forbidden = set(contract.permissions) & self._denied
        if forbidden:
            names = ", ".join(sorted(p.value for p in forbidden))
            raise PermissionDenied(
                f"Agent '{contract.name}' demande une permission interdite : {names}"
            )

    def granted(self, contract: AgentContract) -> frozenset[Permission]:
        """Permissions effectivement accordées = déclarées − interdites."""
        return frozenset(contract.permissions) - self._denied
