from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.address import AddressCreateRequest, AddressUpdateRequest
from app.services.address_service import AddressService

app_router = APIRouter(prefix='/app/addresses')


@app_router.get('')
def list_addresses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': AddressService.list_addresses(db, current_user.id)}


@app_router.post('')
def create_address(payload: AddressCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': AddressService.create_address(db, current_user.id, payload.model_dump())}


@app_router.put('/{address_id}')
def update_address(address_id: int, payload: AddressUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': AddressService.update_address(db, current_user.id, address_id, payload.model_dump(exclude_none=True))}


@app_router.delete('/{address_id}')
def delete_address(address_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    AddressService.delete_address(db, current_user.id, address_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.patch('/{address_id}/default')
def set_default(address_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': AddressService.set_default(db, current_user.id, address_id)}
