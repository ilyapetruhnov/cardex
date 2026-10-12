from __future__ import annotations

from decimal import Decimal

import httpx
import respx
from sqlalchemy.orm import Session

from cardex.models import Card, Set
from cardex.pokemontcg_client import PokemonTcgClient
from cardex.sync import sync_sets_by_name

BASE_URL = "https://api.carddex.dev/compat/pokemontcg/v2"

SETS_RESPONSE = {
    "data": [
        {
            "id": "sv3pt5",
            "name": "Scarlet & Violet 151",
            "series": "Scarlet & Violet",
            "releaseDate": "2023/09/22",
            "total": 207,
        }
    ]
}

CARDS_PAGE_1 = {
    "data": [
        {
            "id": "sv3pt5-1",
            "name": "Bulbasaur",
            "number": "1",
            "rarity": "Common",
            "tcgplayer": {"prices": {"normal": {"market": 0.15, "mid": 0.20}}},
        },
        {
            "id": "sv3pt5-2",
            "name": "Mew ex",
            "number": "151",
            "rarity": "Double Rare",
            "tcgplayer": {"prices": {"holofoil": {"market": 25.50}}},
        },
        {
            "id": "sv3pt5-3",
            "name": "No Price Card",
            "number": "3",
            "rarity": "Common",
            "tcgplayer": None,
        },
    ]
}


@respx.mock
def test_sync_sets_by_name_upserts_set_and_cards(db_session: Session) -> None:
    respx.get(f"{BASE_URL}/sets", params={"q": 'name:"*151*"'}).mock(
        return_value=httpx.Response(200, json=SETS_RESPONSE)
    )
    respx.get(f"{BASE_URL}/cards").mock(
        side_effect=[
            httpx.Response(200, json=CARDS_PAGE_1),
            httpx.Response(200, json={"data": []}),
        ]
    )

    client = PokemonTcgClient()
    synced = sync_sets_by_name(db_session, "151", client=client)

    assert len(synced) == 1
    assert synced[0].id == "sv3pt5"

    set_in_db = db_session.get(Set, "sv3pt5")
    assert set_in_db is not None
    assert set_in_db.name == "Scarlet & Violet 151"
    assert set_in_db.total_cards == 207

    cards = db_session.query(Card).filter(Card.set_id == "sv3pt5").order_by(Card.id).all()
    assert len(cards) == 3
    assert cards[0].market_price == Decimal("0.15")
    assert cards[1].market_price == Decimal("25.50")
    assert cards[2].market_price is None


@respx.mock
def test_sync_sets_by_name_is_idempotent(db_session: Session) -> None:
    respx.get(f"{BASE_URL}/sets", params={"q": 'name:"*151*"'}).mock(
        return_value=httpx.Response(200, json=SETS_RESPONSE)
    )
    respx.get(f"{BASE_URL}/cards").mock(
        side_effect=[
            httpx.Response(200, json=CARDS_PAGE_1),
            httpx.Response(200, json={"data": []}),
            httpx.Response(200, json=CARDS_PAGE_1),
            httpx.Response(200, json={"data": []}),
        ]
    )

    client = PokemonTcgClient()
    sync_sets_by_name(db_session, "151", client=client)
    sync_sets_by_name(db_session, "151", client=client)

    assert db_session.query(Set).count() == 1
    assert db_session.query(Card).count() == 3
