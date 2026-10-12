"""Ingestion: search carddex.dev and upsert Sets/Cards into the local DB."""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from cardex.models import Card, Set
from cardex.pokemontcg_client import CardData, PokemonTcgClient, SetData


def sync_sets_by_name(
    session: Session, name_query: str, client: PokemonTcgClient | None = None
) -> list[Set]:
    """Search for sets matching `name_query`, upsert each along with all its cards."""
    owns_client = client is None
    client = client or PokemonTcgClient()
    try:
        matches = client.search_sets(name_query)
        synced = [upsert_set(session, data) for data in matches]
        for data in matches:
            sync_cards_for_set(session, data.id, client)
        session.commit()
        return synced
    finally:
        if owns_client:
            client.close()


def upsert_set(session: Session, data: SetData) -> Set:
    existing = session.get(Set, data.id)
    if existing is None:
        existing = Set(
            id=data.id,
            name=data.name,
            series=data.series,
            release_date=data.release_date,
            total_cards=data.total_cards,
        )
        session.add(existing)
    else:
        existing.name = data.name
        existing.series = data.series
        existing.release_date = data.release_date
        existing.total_cards = data.total_cards
    return existing


def sync_cards_for_set(session: Session, set_id: str, client: PokemonTcgClient) -> int:
    now = dt.datetime.now(dt.UTC)
    count = 0
    for card_data in client.fetch_cards_for_set(set_id):
        upsert_card(session, card_data, now)
        count += 1
    return count


def upsert_card(session: Session, data: CardData, updated_at: dt.datetime) -> Card:
    existing = session.get(Card, data.id)
    if existing is None:
        existing = Card(
            id=data.id,
            set_id=data.set_id,
            name=data.name,
            number=data.number,
            rarity=data.rarity,
            market_price=data.market_price,
            price_updated_at=updated_at,
        )
        session.add(existing)
    else:
        existing.name = data.name
        existing.number = data.number
        existing.rarity = data.rarity
        existing.market_price = data.market_price
        existing.price_updated_at = updated_at
    return existing
