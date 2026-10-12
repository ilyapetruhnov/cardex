from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Set(Base):
    """A Pokémon TCG set, e.g. 'Scarlet & Violet—151'."""

    __tablename__ = "sets"

    id: Mapped[str] = mapped_column(primary_key=True)  # pokemontcg.io set id, e.g. "sv3pt5"
    name: Mapped[str]
    series: Mapped[str]
    release_date: Mapped[str]
    total_cards: Mapped[int]

    cards: Mapped[list[Card]] = relationship(back_populates="set", cascade="all, delete-orphan")
    products: Mapped[list[Product]] = relationship(
        back_populates="set", cascade="all, delete-orphan"
    )
    pull_slots: Mapped[list[PullSlot]] = relationship(
        back_populates="set", cascade="all, delete-orphan"
    )


class Card(Base):
    """A single card printing with its current market price."""

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(primary_key=True)  # pokemontcg.io card id
    set_id: Mapped[str] = mapped_column(ForeignKey("sets.id"), index=True)
    name: Mapped[str]
    number: Mapped[str]
    rarity: Mapped[str | None]
    market_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_updated_at: Mapped[dt.datetime | None]

    set: Mapped[Set] = relationship(back_populates="cards")


class Product(Base):
    """A sealed product (pack, bundle, box, ETB, ...) tied to a set."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    set_id: Mapped[str] = mapped_column(ForeignKey("sets.id"), index=True)
    name: Mapped[str]
    product_type: Mapped[str]
    packs_per_product: Mapped[int]
    # Manual override for guaranteed non-card-pool value (e.g. an ETB promo
    # card). Defaults to 0; v1 does not attempt to price these automatically.
    bonus_card_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))

    set: Mapped[Set] = relationship(back_populates="products")


class PullSlot(Base):
    """One slot in a set's pack structure: N cards drawn uniformly from a rarity pool.

    Defined per-set (not per-product) because every pack-based product for a
    set shares the same odds; only the pack count differs.
    """

    __tablename__ = "pull_slots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    set_id: Mapped[str] = mapped_column(ForeignKey("sets.id"), index=True)
    rarities: Mapped[list[str]] = mapped_column(JSON)
    slot_count: Mapped[int]

    set: Mapped[Set] = relationship(back_populates="pull_slots")
