from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.api.v1.mobile_serializers import (
    page_slice,
    serialize_local_life_merchant,
    serialize_local_life_service,
    serialize_order,
    serialize_store,
)
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.local_life import (
    AdminLocalLifeMerchantCreateRequest,
    AdminLocalLifeMerchantUpdateRequest,
    AdminLocalLifeServiceCreateRequest,
    AdminLocalLifeServiceUpdateRequest,
    AdminLocalLifeStoreCreateRequest,
    AdminLocalLifeStoreUpdateRequest,
    AdminMerchantCommissionRuleCreateRequest,
    AdminMerchantCommissionRuleUpdateRequest,
    LocalLifeOrderCreateRequest,
    LocalLifeVerifyRequest,
)
from app.services.local_life_service import LocalLifeServiceLayer

app_router = APIRouter(prefix='/app/local-life')
admin_router = APIRouter(prefix='/admin/local-life')


@app_router.get('/merchants')
def merchants(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = LocalLifeServiceLayer.list_merchants(db)
    return {'code': 0, 'message': 'success', 'data': [serialize_local_life_merchant(item) for item in rows]}


@app_router.get('/services')
def services(
    merchant_id: int | None = Query(default=None),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = page_slice(LocalLifeServiceLayer.list_services(db, merchant_id), page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_local_life_service(db, item) for item in rows]}


@app_router.get('/merchants/{merchant_id}')
def merchant_detail(merchant_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': serialize_local_life_merchant(LocalLifeServiceLayer.get_merchant(db, merchant_id))}


@app_router.get('/merchants/{merchant_id}/stores')
def merchant_stores(merchant_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = LocalLifeServiceLayer.list_stores(db, merchant_id)
    return {'code': 0, 'message': 'success', 'data': [serialize_store(item) for item in rows]}


@app_router.get('/services/{service_id}')
def service_detail(service_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': serialize_local_life_service(db, LocalLifeServiceLayer.get_service(db, service_id))}


@app_router.get('/orders')
def my_local_life_orders(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = page_slice(LocalLifeServiceLayer.my_orders(db, current_user.id), page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_order(db, item) for item in rows]}


@app_router.get('/orders/{order_id}')
def local_life_order_detail(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    detail = LocalLifeServiceLayer.get_order_detail(db, current_user.id, order_id)
    payload = {
        'order': serialize_order(db, detail['order']),
        'local_order': detail['local_order'],
        'service': serialize_local_life_service(db, detail['service']) if detail.get('service') else None,
        'merchant': serialize_local_life_merchant(detail['merchant']) if detail.get('merchant') else None,
        'store': serialize_store(detail['store']) if detail.get('store') else None,
    }
    return {'code': 0, 'message': 'success', 'data': payload}


@app_router.post('/orders')
def create_local_life_order(
    payload: LocalLifeOrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = LocalLifeServiceLayer.create_order(
        db,
        current_user.id,
        payload.service_id,
        payload.store_id,
        payload.quantity,
        payload.points_amount,
        payload.balance_amount,
    )
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, order)}


@app_router.get('/revenue-summary')
def revenue_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.revenue_summary(db, current_user.id)}


@admin_router.get('/merchants')
def admin_merchants(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.list_merchants_for_admin(db, current_user)}


@admin_router.post('/merchants')
def create_merchant(
    payload: AdminLocalLifeMerchantCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.create_merchant_for_admin(db, current_user, payload.model_dump())}


@admin_router.put('/merchants/{merchant_id}')
def update_merchant(
    merchant_id: int,
    payload: AdminLocalLifeMerchantUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.update_merchant_for_admin(db, merchant_id, current_user, payload.model_dump())}


@admin_router.delete('/merchants/{merchant_id}')
def delete_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    LocalLifeServiceLayer.delete_merchant_for_admin(db, merchant_id, current_user)
    return {'code': 0, 'message': 'success', 'data': True}


@admin_router.get('/stores')
def admin_stores(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.list_stores_for_admin(db, current_user)}


@admin_router.post('/stores')
def create_store(
    payload: AdminLocalLifeStoreCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.create_store_for_admin(db, current_user, payload.model_dump())}


@admin_router.put('/stores/{store_id}')
def update_store(
    store_id: int,
    payload: AdminLocalLifeStoreUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.update_store_for_admin(db, store_id, current_user, payload.model_dump())}


@admin_router.delete('/stores/{store_id}')
def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    LocalLifeServiceLayer.delete_store_for_admin(db, store_id, current_user)
    return {'code': 0, 'message': 'success', 'data': True}


@admin_router.get('/services')
def admin_services(
    merchant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.list_services_for_admin(db, current_user, merchant_id)}


@admin_router.post('/services')
def create_service(
    payload: AdminLocalLifeServiceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.create_service_for_admin(db, current_user, payload.model_dump())}


@admin_router.put('/services/{service_id}')
def update_service(
    service_id: int,
    payload: AdminLocalLifeServiceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.update_service_for_admin(db, service_id, current_user, payload.model_dump())}


@admin_router.delete('/services/{service_id}')
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    LocalLifeServiceLayer.delete_service_for_admin(db, service_id, current_user)
    return {'code': 0, 'message': 'success', 'data': True}


@admin_router.get('/orders')
def admin_orders(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.list_orders_for_admin(db, current_user)}


@admin_router.post('/orders/verify')
def admin_verify_order(
    payload: LocalLifeVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.verify_order(db, payload.verification_code, current_user)}


@admin_router.get('/commission-rules')
def admin_rules(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.list_commission_rules_for_admin(db, current_user)}


@admin_router.post('/commission-rules')
def create_rule(
    payload: AdminMerchantCommissionRuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.create_rule_for_admin(db, current_user, payload.model_dump())}


@admin_router.put('/commission-rules/{rule_id}')
def update_rule(
    rule_id: int,
    payload: AdminMerchantCommissionRuleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.update_rule_for_admin(db, rule_id, current_user, payload.model_dump())}


@admin_router.delete('/commission-rules/{rule_id}')
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    LocalLifeServiceLayer.delete_rule_for_admin(db, rule_id, current_user)
    return {'code': 0, 'message': 'success', 'data': True}


@admin_router.get('/device-revenues')
def admin_device_revenues(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.list_device_revenues_for_admin(db, current_user)}


@admin_router.get('/ad-revenues')
def admin_ad_revenues(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': LocalLifeServiceLayer.list_ad_revenues_for_admin(db, current_user)}
