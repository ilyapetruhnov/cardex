"""Glue between the DB layer and the pure valuation engine."""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from cardex.models import Card, Product, PullSlot
from cardex.valuation import PullSlotSpec, ValuationResult, simulate_product, summarize


class ProductNotFoundError(Exception):
    pass


def build_pull_slot_specs(session: Session, set_id: str) -> list[PullSlotSpec]:
    slots = session.query(PullSlot).filter(PullSlot.set_id == set_id).all()
    specs = []
    for slot in slots:
        rows = (
            session.query(Card.market_price)
            .filter(
                Card.set_id == set_id,
                Card.rarity.in_(slot.rarities),
                Card.market_price.is_not(None),
            )
            .all()
        )
        prices = tuple(float(price) for (price,) in rows if price is not None)
        specs.append(
            PullSlotSpec(rarities=tuple(slot.rarities), slot_count=slot.slot_count, prices=prices)
        )
    return specs


def get_product_or_raise(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise ProductNotFoundError(f"Product {product_id} not found")
    return product


def value_product(
    session: Session,
    product: Product,
    retail_price: float,
    n_sims: int = 20_000,
    rng: np.random.Generator | None = None,
) -> ValuationResult:
    specs = build_pull_slot_specs(session, product.set_id)
    outcomes = simulate_product(
        specs,
        product.packs_per_product,
        n_sims=n_sims,
        bonus_value=float(product.bonus_card_value),
        rng=rng,
    )
    return summarize(outcomes, retail_price)
