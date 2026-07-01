"""BudgetTracker : cumul, dépassement, et 0 = illimité."""

from __future__ import annotations

import pytest

from jarvis.core.context import BudgetTracker
from jarvis.core.contracts import Budget
from jarvis.core.errors import BudgetExceeded


def test_charge_accumulates() -> None:
    t = BudgetTracker(Budget(max_tokens_day=1000))
    t.charge(tokens=100)
    t.charge(tokens=50, usd=0.02)
    assert t.tokens == 150
    assert t.spent == {"tokens": 150.0, "usd": 0.02}


def test_token_cap_enforced() -> None:
    t = BudgetTracker(Budget(max_tokens_day=100))
    with pytest.raises(BudgetExceeded, match="tokens"):
        t.charge(tokens=101)


def test_usd_cap_enforced() -> None:
    t = BudgetTracker(Budget(max_usd_day=0.05))
    with pytest.raises(BudgetExceeded, match="usd"):
        t.charge(usd=0.06)


def test_zero_means_unlimited() -> None:
    t = BudgetTracker(Budget())  # tout à 0
    t.charge(tokens=10_000_000, usd=999.0)  # ne lève pas
    assert t.tokens == 10_000_000
