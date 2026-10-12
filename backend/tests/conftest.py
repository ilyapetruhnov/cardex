from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cardex.models import Base, Card, Product, PullSlot, Set


@pytest.fixture(autouse=True)
def _isolated_database_url(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Point the app's own engine (used by the FastAPI lifespan's init_db) at a
    throwaway in-memory DB so tests never touch a real cardex.db file."""
    from cardex.config import get_settings
    from cardex.db import reset_engine

    monkeypatch.setenv("CARDEX_DATABASE_URL", "sqlite:///:memory:")
    get_settings.cache_clear()
    reset_engine()
    yield
    get_settings.cache_clear()
    reset_engine()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def sample_set(db_session: Session) -> Set:
    set_ = Set(id="test-set", name="Test Set", series="Test Series", release_date="2026/01/01",
               total_cards=5)
    db_session.add(set_)

    cards = [
        Card(id="t1", set_id="test-set", name="Common A", number="1", rarity="Common",
             market_price=Decimal("0.10")),
        Card(id="t2", set_id="test-set", name="Common B", number="2", rarity="Common",
             market_price=Decimal("0.20")),
        Card(id="t3", set_id="test-set", name="Uncommon A", number="3", rarity="Uncommon",
             market_price=Decimal("0.50")),
        Card(id="t4", set_id="test-set", name="Rare A", number="4", rarity="Rare",
             market_price=Decimal("2.00")),
        Card(id="t5", set_id="test-set", name="Ultra Rare A", number="5", rarity="Ultra Rare",
             market_price=Decimal("50.00")),
    ]
    db_session.add_all(cards)

    slots = [
        PullSlot(set_id="test-set", rarities=["Common"], slot_count=2),
        PullSlot(set_id="test-set", rarities=["Uncommon"], slot_count=1),
        PullSlot(set_id="test-set", rarities=["Rare", "Ultra Rare"], slot_count=1),
    ]
    db_session.add_all(slots)

    product = Product(
        set_id="test-set", name="Booster Pack", product_type="pack", packs_per_product=1,
        bonus_card_value=Decimal("0"),
    )
    db_session.add(product)

    db_session.commit()
    return set_


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    from cardex.api.app import create_app
    from cardex.db import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session

    with TestClient(app) as test_client:
        yield test_client
