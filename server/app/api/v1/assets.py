from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.asset import UserAssetLedger
from app.models.enums import AssetType
from app.models.user import User
from app.schemas.asset import AssetTransferRequest
from app.services.asset_service import AssetService

app_router = APIRouter(prefix='/app/assets')


@app_router.get('/summary')
def summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': AssetService.summary(db, current_user.id)}


@app_router.get('/{asset_type}')
def asset_detail(asset_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = AssetService.get_account(db, current_user.id, AssetType(asset_type))
    return {'code': 0, 'message': 'success', 'data': account}


@app_router.get('/{asset_type}/ledgers')
def ledgers(asset_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(UserAssetLedger).filter(
        UserAssetLedger.user_id == current_user.id,
        UserAssetLedger.asset_type == AssetType(asset_type),
    ).order_by(UserAssetLedger.id.desc()).all()
    return {'code': 0, 'message': 'success', 'data': rows}


@app_router.post('/signin')
def sign_in(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': AssetService.sign_in(db, current_user.id)}


@app_router.post('/points/transfer')
def transfer_points(payload: AssetTransferRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    AssetService.transfer_points(db, current_user, payload.to_user_id, payload.amount, payload.remark)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}
