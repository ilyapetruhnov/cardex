"""Thin client for the pokemontcg.io v2 API protocol (sets + cards + TCGplayer
prices). Defaults to carddex.dev's pokemontcg.io v2-compatible endpoint, which
serves the same request/response shape."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Self

import httpx

from cardex.config import get_settings

# Preference order when a card has multiple print finishes (holofoil, reverse
# holo, 1st edition, ...) — pick the first variant that's actually priced.
_PRICE_VARIANT_PRIORITY = (
    "holofoil",
    "normal",
    "reverseHolofoil",
    "1stEditionHolofoil",
    "1stEditionNormal",
    "unlimitedHolofoil",
    "unlimited",
)


@dataclass(frozen=True)
class SetData:
    id: str
    name: str
    series: str
    release_date: str
    total_cards: int


@dataclass(frozen=True)
class CardData:
    id: str
    set_id: str
    name: str
    number: str
    rarity: str | None
    market_price: Decimal | None


def _extract_market_price(card_json: dict[str, Any]) -> Decimal | None:
    prices = (card_json.get("tcgplayer") or {}).get("prices") or {}
    ordered = [prices[v] for v in _PRICE_VARIANT_PRIORITY if v in prices]
    ordered += [v for k, v in prices.items() if k not in _PRICE_VARIANT_PRIORITY]
    for variant_prices in ordered:
        value = variant_prices.get("market") or variant_prices.get("mid")
        if value is not None:
            return Decimal(str(value))
    return None


class PokemonTcgClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        headers = {}
        key = api_key if api_key is not None else settings.pokemontcg_api_key
        if key:
            headers["X-Api-Key"] = key
        self._client = httpx.Client(
            base_url=base_url or settings.pokemontcg_base_url,
            headers=headers,
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def search_sets(self, name_query: str) -> list[SetData]:
        resp = self._client.get("/sets", params={"q": f'name:"*{name_query}*"'})
        resp.raise_for_status()
        return [
            SetData(
                id=item["id"],
                name=item["name"],
                series=item.get("series", ""),
                release_date=item.get("releaseDate", ""),
                total_cards=item.get("total", 0),
            )
            for item in resp.json()["data"]
        ]

    def fetch_cards_for_set(self, set_id: str, page_size: int = 250) -> Iterator[CardData]:
        page = 1
        while True:
            resp = self._client.get(
                "/cards",
                params={"q": f"set.id:{set_id}", "page": page, "pageSize": page_size},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            if not data:
                return
            for item in data:
                yield CardData(
                    id=item["id"],
                    set_id=set_id,
                    name=item["name"],
                    number=item.get("number", ""),
                    rarity=item.get("rarity"),
                    market_price=_extract_market_price(item),
                )
            if len(data) < page_size:
                return
            page += 1
