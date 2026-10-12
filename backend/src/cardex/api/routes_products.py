from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cardex.db import get_session
from cardex.models import Product
from cardex.schemas import ProductOut

router = APIRouter(prefix="/api/sets", tags=["products"])


@router.get("/{set_id}/products", response_model=list[ProductOut])
def list_products(set_id: str, session: Session = Depends(get_session)) -> list[Product]:
    return session.query(Product).filter(Product.set_id == set_id).all()
