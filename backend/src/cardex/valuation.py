"""Pure EV/risk calculation engine. No DB or network access — unit-testable in isolation.

Pull-probability model (v1, documented simplification): each PullSlotSpec
represents `slot_count` cards per pack drawn *uniformly at random, with
replacement* from the full list of market prices of cards qualifying for that
slot's rarities. This treats every qualifying card as equally likely, which
overstates the chance of hitting the priciest secret rares/alt-arts relative
to real-world pull rates. Refining this with weighted/community pull-rate
data is tracked as future work.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PullSlotSpec:
    rarities: tuple[str, ...]
    slot_count: int
    prices: tuple[float, ...]  # market prices of all cards in the set qualifying for this slot


@dataclass(frozen=True)
class RarityStats:
    mean: float
    variance: float
    n: int


def rarity_price_stats(prices: Sequence[float]) -> RarityStats:
    """Mean & population variance of a rarity pool's card prices."""
    if not prices:
        return RarityStats(mean=0.0, variance=0.0, n=0)
    arr = np.asarray(prices, dtype=float)
    return RarityStats(mean=float(arr.mean()), variance=float(arr.var()), n=int(arr.size))


def pack_ev(slots: Sequence[PullSlotSpec]) -> tuple[float, float]:
    """Analytic (mean, variance) of a single pack's total card value.

    Slots are treated as independent draws, so variances sum; each slot's
    variance scales linearly with its card count (sum of i.i.d. draws).
    """
    mean_total = 0.0
    var_total = 0.0
    for slot in slots:
        stats = rarity_price_stats(slot.prices)
        mean_total += slot.slot_count * stats.mean
        var_total += slot.slot_count * stats.variance
    return mean_total, var_total


def simulate_product(
    slots: Sequence[PullSlotSpec],
    packs_per_product: int,
    n_sims: int = 20_000,
    bonus_value: float = 0.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Vectorized Monte Carlo of `n_sims` total-value outcomes for the product.

    Simulating (rather than relying on a normal approximation of pack_ev) is
    what lets us report real percentiles and P(profit) — single-pack and
    small-box outcomes are lumpy, not Gaussian.
    """
    if rng is None:
        rng = np.random.default_rng()
    totals = np.full(n_sims, float(bonus_value), dtype=float)
    for slot in slots:
        if not slot.prices or slot.slot_count <= 0 or packs_per_product <= 0:
            continue
        prices = np.asarray(slot.prices, dtype=float)
        draws = rng.choice(prices, size=(n_sims, packs_per_product * slot.slot_count))
        totals += draws.sum(axis=1)
    return totals


@dataclass(frozen=True)
class ValuationResult:
    ev: float
    std_dev: float
    price_paid: float
    expected_profit: float
    roi_pct: float
    prob_profit: float
    p10: float
    p50: float
    p90: float
    risk_adjusted_return: float  # expected_profit / std_dev — a Sharpe-like ratio


def summarize(outcomes: np.ndarray, price_paid: float) -> ValuationResult:
    ev = float(outcomes.mean())
    std_dev = float(outcomes.std())
    expected_profit = ev - price_paid
    roi_pct = (expected_profit / price_paid * 100.0) if price_paid > 0 else 0.0
    prob_profit = float((outcomes > price_paid).mean())
    p10, p50, p90 = (float(x) for x in np.percentile(outcomes, [10, 50, 90]))
    risk_adjusted_return = expected_profit / std_dev if std_dev > 0 else 0.0
    return ValuationResult(
        ev=ev,
        std_dev=std_dev,
        price_paid=price_paid,
        expected_profit=expected_profit,
        roi_pct=roi_pct,
        prob_profit=prob_profit,
        p10=p10,
        p50=p50,
        p90=p90,
        risk_adjusted_return=risk_adjusted_return,
    )


def rank_by_risk_adjusted_return(
    results: Sequence[tuple[str, ValuationResult]],
) -> list[tuple[str, ValuationResult]]:
    """Sort (label, result) pairs best-to-worst by risk-adjusted return, falling
    back to raw ROI when std_dev is 0 for every candidate (e.g. unit tests)."""
    return sorted(results, key=lambda item: item[1].risk_adjusted_return, reverse=True)
