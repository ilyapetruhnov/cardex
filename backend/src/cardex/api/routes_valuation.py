from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cardex.db import get_session
from cardex.schemas import (
    CompareRequest,
    CompareResponse,
    ValuationRequest,
    ValuationResponse,
)
from cardex.service import ProductNotFoundError, get_product_or_raise, value_product
from cardex.valuation import ValuationResult

router = APIRouter(prefix="/api/valuation", tags=["valuation"])


def _to_response(
    product_id: int, product_name: str, set_id: str, result: ValuationResult
) -> ValuationResponse:
    return ValuationResponse(
        product_id=product_id,
        product_name=product_name,
        set_id=set_id,
        ev=result.ev,
        std_dev=result.std_dev,
        price_paid=result.price_paid,
        expected_profit=result.expected_profit,
        roi_pct=result.roi_pct,
        prob_profit=result.prob_profit,
        p10=result.p10,
        p50=result.p50,
        p90=result.p90,
        risk_adjusted_return=result.risk_adjusted_return,
    )


@router.post("", response_model=ValuationResponse)
def value_single(
    req: ValuationRequest, session: Session = Depends(get_session)
) -> ValuationResponse:
    try:
        product = get_product_or_raise(session, req.product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = value_product(session, product, float(req.retail_price), n_sims=req.n_sims)
    return _to_response(product.id, product.name, product.set_id, result)


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest, session: Session = Depends(get_session)) -> CompareResponse:
    scored: list[tuple[ValuationResult, ValuationResponse]] = []
    for item in req.items:
        try:
            product = get_product_or_raise(session, item.product_id)
        except ProductNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        result = value_product(session, product, float(item.retail_price), n_sims=req.n_sims)
        response = _to_response(product.id, product.name, product.set_id, result)
        scored.append((result, response))

    scored.sort(key=lambda pair: pair[0].risk_adjusted_return, reverse=True)
    return CompareResponse(results=[response for _, response in scored])
