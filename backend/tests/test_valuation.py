from __future__ import annotations

import numpy as np
import pytest

from cardex.valuation import (
    PullSlotSpec,
    pack_ev,
    rank_by_risk_adjusted_return,
    rarity_price_stats,
    simulate_product,
    summarize,
)


def test_rarity_price_stats_empty() -> None:
    stats = rarity_price_stats([])
    assert stats == rarity_price_stats([])
    assert stats.mean == 0.0
    assert stats.variance == 0.0
    assert stats.n == 0


def test_rarity_price_stats_basic() -> None:
    stats = rarity_price_stats([1.0, 2.0, 3.0])
    assert stats.mean == pytest.approx(2.0)
    assert stats.n == 3
    # population variance of [1,2,3] is 2/3
    assert stats.variance == pytest.approx(2.0 / 3.0)


def test_pack_ev_sums_slots_independently() -> None:
    slots = [
        PullSlotSpec(rarities=("Common",), slot_count=2, prices=(1.0, 1.0)),
        PullSlotSpec(rarities=("Rare",), slot_count=1, prices=(10.0, 20.0)),
    ]
    mean, variance = pack_ev(slots)
    # 2 * mean(1,1) + 1 * mean(10,20) = 2*1 + 15 = 17
    assert mean == pytest.approx(17.0)
    # 2 * var(1,1)=0 + 1 * var(10,20)=25 => 25
    assert variance == pytest.approx(25.0)


def test_simulate_product_matches_analytic_mean_for_large_n() -> None:
    slots = [
        PullSlotSpec(rarities=("Common",), slot_count=4, prices=(0.1, 0.2, 0.3)),
        PullSlotSpec(rarities=("Rare",), slot_count=1, prices=(1.0, 5.0, 50.0)),
    ]
    rng = np.random.default_rng(42)
    outcomes = simulate_product(slots, packs_per_product=1, n_sims=50_000, rng=rng)
    analytic_mean, _ = pack_ev(slots)
    assert outcomes.mean() == pytest.approx(analytic_mean, rel=0.03)


def test_simulate_product_scales_with_pack_count() -> None:
    slots = [PullSlotSpec(rarities=("Common",), slot_count=1, prices=(1.0, 2.0, 3.0))]
    rng = np.random.default_rng(0)
    one_pack = simulate_product(slots, packs_per_product=1, n_sims=20_000, rng=rng)
    rng = np.random.default_rng(0)
    six_packs = simulate_product(slots, packs_per_product=6, n_sims=20_000, rng=rng)
    assert six_packs.mean() == pytest.approx(one_pack.mean() * 6, rel=0.05)


def test_simulate_product_applies_bonus_value() -> None:
    slots = [PullSlotSpec(rarities=("Common",), slot_count=1, prices=(1.0,))]
    outcomes = simulate_product(slots, packs_per_product=1, n_sims=100, bonus_value=5.0)
    assert np.all(outcomes == 6.0)


def test_simulate_product_handles_empty_pool() -> None:
    slots = [PullSlotSpec(rarities=("Secret",), slot_count=1, prices=())]
    outcomes = simulate_product(slots, packs_per_product=1, n_sims=100)
    assert np.all(outcomes == 0.0)


def test_summarize_profitable_outcome() -> None:
    outcomes = np.array([10.0, 10.0, 10.0, 10.0])
    result = summarize(outcomes, price_paid=5.0)
    assert result.ev == pytest.approx(10.0)
    assert result.std_dev == pytest.approx(0.0)
    assert result.expected_profit == pytest.approx(5.0)
    assert result.roi_pct == pytest.approx(100.0)
    assert result.prob_profit == pytest.approx(1.0)
    assert result.risk_adjusted_return == 0.0  # std_dev is 0 -> guarded, not division by zero


def test_summarize_zero_price_guards_roi() -> None:
    outcomes = np.array([1.0, 2.0, 3.0])
    result = summarize(outcomes, price_paid=0.0)
    assert result.roi_pct == 0.0


def test_rank_by_risk_adjusted_return_orders_best_first() -> None:
    low = summarize(np.array([1.0, 1.0]), price_paid=0.5)  # ev=1, profit=0.5, std=0
    high = summarize(np.array([8.0, 12.0]), price_paid=5.0)  # ev=10, profit=5, std=2
    ranked = rank_by_risk_adjusted_return([("low", low), ("high", high)])
    assert [label for label, _ in ranked] == ["high", "low"]
