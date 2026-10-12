from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    series: str
    release_date: str
    total_cards: int


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    number: str
    rarity: str | None
    market_price: Decimal | None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    set_id: str
    name: str
    product_type: str
    packs_per_product: int
    bonus_card_value: Decimal


class ValuationRequest(BaseModel):
    product_id: int
    retail_price: Decimal = Field(gt=0)
    n_sims: int = Field(default=20_000, ge=1_000, le=200_000)


class ValuationResponse(BaseModel):
    product_id: int
    product_name: str
    set_id: str
    ev: float
    std_dev: float
    price_paid: float
    expected_profit: float
    roi_pct: float
    prob_profit: float
    p10: float
    p50: float
    p90: float
    risk_adjusted_return: float


class CompareRequestItem(BaseModel):
    product_id: int
    retail_price: Decimal = Field(gt=0)


class CompareRequest(BaseModel):
    items: list[CompareRequestItem]
    n_sims: int = Field(default=20_000, ge=1_000, le=200_000)


class CompareResponse(BaseModel):
    results: list[ValuationResponse]  # sorted best-to-worst by risk-adjusted return
