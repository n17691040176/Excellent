from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.bank_card import BankCardCreateRequest, BankCardUpdateRequest
from app.services.bank_card_service import BankCardService

app_router = APIRouter(prefix='/app/bank-cards')


@app_router.get('')
def list_bank_cards(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': [BankCardService.serialize(item) for item in BankCardService.list_cards(db, current_user.id)]}


@app_router.post('')
def create_bank_card(payload: BankCardCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = BankCardService.create(db, current_user.id, payload.model_dump())
    return {'code': 0, 'message': 'success', 'data': BankCardService.serialize(card)}


@app_router.put('/{card_id}')
def update_bank_card(card_id: int, payload: BankCardUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = BankCardService.update(db, current_user.id, card_id, payload.model_dump(exclude_none=True))
    return {'code': 0, 'message': 'success', 'data': BankCardService.serialize(card)}


@app_router.patch('/{card_id}/default')
def set_default_bank_card(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = BankCardService.set_default(db, current_user.id, card_id)
    return {'code': 0, 'message': 'success', 'data': BankCardService.serialize(card)}


@app_router.delete('/{card_id}')
def delete_bank_card(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    BankCardService.delete(db, current_user.id, card_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}
