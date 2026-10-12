"""Default pull-slot templates and example sealed products.

The template below approximates a modern-era (Scarlet & Violet onward)
11-card pack. The "hit" slot pools every rarity above Uncommon together
(see the v1 simplification documented in `valuation.py`); the reverse-holo
slot reuses the same canonical price captured per card rather than a
distinct reverse-holo price point — a further approximation worth revisiting
once per-variant pricing is stored.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from cardex.models import Product, PullSlot, Set

STANDARD_MODERN_PACK_TEMPLATE: list[tuple[tuple[str, ...], int]] = [
    (("Common",), 6),
    (("Uncommon",), 3),
    (
        (
            "Rare",
            "Rare Holo",
            "Double Rare",
            "ACE SPEC Rare",
            "Illustration Rare",
            "Ultra Rare",
            "Special Illustration Rare",
            "Hyper Rare",
            "Shiny Rare",
            "Shiny Ultra Rare",
        ),
        1,
    ),
    (("Common", "Uncommon", "Rare", "Rare Holo"), 1),  # reverse holo slot
]

DEFAULT_PRODUCTS: list[tuple[str, str, int]] = [
    ("Booster Pack", "pack", 1),
    ("Booster Bundle", "bundle", 6),
    ("Booster Box", "box", 36),
]


def seed_pull_slots(session: Session, set_id: str) -> list[PullSlot]:
    """Replace any existing PullSlot config for `set_id` with the standard template."""
    session.query(PullSlot).filter(PullSlot.set_id == set_id).delete()
    slots = [
        PullSlot(set_id=set_id, rarities=list(rarities), slot_count=count)
        for rarities, count in STANDARD_MODERN_PACK_TEMPLATE
    ]
    session.add_all(slots)
    return slots


def seed_default_products(session: Session, set_id: str) -> list[Product]:
    """Create Booster Pack/Bundle/Box products for `set_id` if not already present."""
    existing_names = {
        name for (name,) in session.query(Product.name).filter(Product.set_id == set_id).all()
    }
    created = []
    for name, product_type, packs in DEFAULT_PRODUCTS:
        if name in existing_names:
            continue
        product = Product(
            set_id=set_id,
            name=name,
            product_type=product_type,
            packs_per_product=packs,
            bonus_card_value=Decimal("0"),
        )
        session.add(product)
        created.append(product)
    return created


def seed_set(session: Session, set_id: str) -> None:
    seed_pull_slots(session, set_id)
    seed_default_products(session, set_id)
    session.commit()


def seed_all_sets(session: Session) -> None:
    for (set_id,) in session.query(Set.id).all():
        seed_pull_slots(session, set_id)
        seed_default_products(session, set_id)
    session.commit()
