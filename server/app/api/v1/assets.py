from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.api.v1.mobile_serializers import (
    normalize_asset_type,
    page_slice,
    serialize_asset_account,
    serialize_asset_ledger,
)
from app.db.session import get_db
from app.models.asset import UserAssetLedger, UserPowerBank
from app.models.enums import AssetType
from app.models.user import User
from app.schemas.asset import AssetTransferRequest
from app.services.asset_service import AssetService
from app.utils.helpers import now

app_router = APIRouter(prefix='/app/assets')


@app_router.get('/summary')
def summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = AssetService.summary(db, current_user.id)
    payload = dict(data)
    payload.update({key.lower(): value for key, value in data.items()})
    return {'code': 0, 'message': 'success', 'data': payload}


@app_router.get('/power-banks')
def power_banks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': AssetService.list_power_banks(db, current_user.id)}


@app_router.get('/{asset_type}')
def asset_detail(asset_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    AssetService.settle_power_bank_income(db, current_user.id)
    normalized_type = normalize_asset_type(asset_type)
    if normalized_type == AssetType.POWER_BANK and not AssetService.supports_power_bank_asset_account(db):
        active_count = AssetService.active_power_bank_count(db, current_user.id)
        total_bound_count = db.query(UserPowerBank).filter(UserPowerBank.user_id == current_user.id).count()
        return {
            'code': 0,
            'message': 'success',
            'data': {
                'id': 0,
                'user_id': current_user.id,
                'asset_type': normalized_type.value,
                'total_amount': float(total_bound_count),
                'available_amount': float(active_count),
                'frozen_amount': 0.0,
                'consumed_amount': float(max(total_bound_count - active_count, 0)),
                'withdrawn_amount': 0.0,
                'updated_at': None,
            },
        }
    account = AssetService.get_account(db, current_user.id, normalized_type)
    if normalized_type == AssetType.POWER_BANK:
        account = AssetService.sync_power_bank_account_snapshot(db, current_user.id, account)
    return {'code': 0, 'message': 'success', 'data': serialize_asset_account(account)}


@app_router.get('/{asset_type}/ledgers')
def ledgers(
    asset_type: str,
    page: int = 1,
    page_size: int = 20,
    recent_days: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    AssetService.settle_power_bank_income(db, current_user.id)
    query = db.query(UserAssetLedger).filter(
        UserAssetLedger.user_id == current_user.id,
        UserAssetLedger.asset_type == normalize_asset_type(asset_type),
    )
    if recent_days and recent_days > 0:
        query = query.filter(UserAssetLedger.created_at >= now() - timedelta(days=recent_days))
    rows = query.order_by(UserAssetLedger.id.desc()).all()
    return {'code': 0, 'message': 'success', 'data': [serialize_asset_ledger(item) for item in page_slice(rows, page, page_size)]}


@app_router.post('/signin')
def sign_in(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': AssetService.sign_in(db, current_user.id)}


@app_router.post('/points/transfer')
def transfer_points(payload: AssetTransferRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    AssetService.transfer_points(db, current_user, payload.to_user_id, payload.amount, payload.remark)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}
