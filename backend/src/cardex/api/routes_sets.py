from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cardex.db import get_session
from cardex.models import Card, Set
from cardex.schemas import CardOut, SetOut

router = APIRouter(prefix="/api/sets", tags=["sets"])


@router.get("", response_model=list[SetOut])
def list_sets(session: Session = Depends(get_session)) -> list[Set]:
    return session.query(Set).order_by(Set.release_date.desc()).all()


@router.get("/{set_id}", response_model=SetOut)
def get_set(set_id: str, session: Session = Depends(get_session)) -> Set:
    set_ = session.get(Set, set_id)
    if set_ is None:
        raise HTTPException(status_code=404, detail="Set not found")
    return set_


@router.get("/{set_id}/cards", response_model=list[CardOut])
def list_cards(set_id: str, session: Session = Depends(get_session)) -> list[Card]:
    return session.query(Card).filter(Card.set_id == set_id).order_by(Card.number).all()
