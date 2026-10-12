from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cardex.models import Product, Set


def test_list_sets(client: TestClient, sample_set: Set) -> None:
    resp = client.get("/api/sets")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == "test-set"


def test_list_cards_for_set(client: TestClient, sample_set: Set) -> None:
    resp = client.get("/api/sets/test-set/cards")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


def test_list_products_for_set(client: TestClient, sample_set: Set) -> None:
    resp = client.get("/api/sets/test-set/products")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Booster Pack"


def test_valuation_returns_sane_metrics(
    client: TestClient, sample_set: Set, db_session: Session
) -> None:
    product = db_session.query(Product).filter(Product.name == "Booster Pack").one()
    resp = client.post(
        "/api/valuation", json={"product_id": product.id, "retail_price": 4.99, "n_sims": 5000}
    )
    assert resp.status_code == 200
    body = resp.json()

    # EV = 2 commons (avg 0.15) + 1 uncommon (0.50) + 1 of {rare=2.00, ultra rare=50.00}
    # = 0.30 + 0.50 + 26.00 = 26.80
    assert body["ev"] == pytest.approx(26.80, rel=0.05)
    assert body["price_paid"] == pytest.approx(4.99)
    assert body["expected_profit"] == pytest.approx(body["ev"] - 4.99, rel=0.05)
    assert 0.0 <= body["prob_profit"] <= 1.0
    assert body["p10"] <= body["p50"] <= body["p90"]


def test_valuation_404_for_unknown_product(client: TestClient, sample_set: Set) -> None:
    resp = client.post("/api/valuation", json={"product_id": 9999, "retail_price": 5.0})
    assert resp.status_code == 404


def test_compare_sorts_by_risk_adjusted_return(
    client: TestClient, sample_set: Set, db_session: Session
) -> None:
    product = db_session.query(Product).filter(Product.name == "Booster Pack").one()
    cheap_product = Product(
        set_id="test-set",
        name="Cheap Pack",
        product_type="pack",
        packs_per_product=1,
        bonus_card_value=0,
    )
    db_session.add(cheap_product)
    db_session.commit()

    resp = client.post(
        "/api/valuation/compare",
        json={
            "items": [
                {"product_id": product.id, "retail_price": 100.0},  # bad deal, overpriced
                {"product_id": cheap_product.id, "retail_price": 0.01},  # great deal
            ],
            "n_sims": 5000,
        },
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert results[0]["product_id"] == cheap_product.id
    assert results[0]["risk_adjusted_return"] >= results[1]["risk_adjusted_return"]
