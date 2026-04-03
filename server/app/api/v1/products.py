from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole, ZoneType
from app.models.user import User
from app.schemas.product import (
    AdminProductAuditRequest,
    AdminProductCreateRequest,
    AdminProductStatusRequest,
    AdminProductUpdateRequest,
    ProductZoneConfigUpdateRequest,
)
from app.services.catalog_service import ProductService

app_router = APIRouter(prefix='/app')
admin_router = APIRouter(prefix='/admin')


@app_router.get('/home')
def home(_: User = Depends(get_current_user)):
    zones = [
        {'zone_code': 'REPURCHASE', 'zone_name': '复购区'},
        {'zone_code': 'SELF_OPERATED', 'zone_name': '自营商城'},
        {'zone_code': 'HOT_SALE', 'zone_name': '爆款区'},
        {'zone_code': 'LOCAL_LIFE', 'zone_name': '本地生活'},
    ]
    return {'code': 0, 'message': 'success', 'data': {'zones': zones, 'banners': [], 'notices': []}}


@app_router.get('/home/zones')
def home_zones(_: User = Depends(get_current_user)):
    return home(_)


@app_router.get('/zones/repurchase/products')
def repurchase_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone(db, ZoneType.REPURCHASE)}


@app_router.get('/zones/self-operated/products')
def self_operated_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone(db, ZoneType.SELF_OPERATED)}


@app_router.get('/zones/hot-sale/products')
def hot_sale_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone(db, ZoneType.HOT_SALE)}


@app_router.get('/zones/local-life/services')
def local_life_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone(db, ZoneType.LOCAL_LIFE)}


@app_router.get('/products/{product_id}')
def product_detail(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': ProductService.get_product(db, product_id)}


@admin_router.get('/zones/repurchase/products')
def admin_repurchase(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone_for_admin(db, ZoneType.REPURCHASE, current_user)}


@admin_router.get('/zones/self-operated/products')
def admin_self_operated(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone_for_admin(db, ZoneType.SELF_OPERATED, current_user)}


@admin_router.get('/zones/hot-sale/products')
def admin_hot_sale(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone_for_admin(db, ZoneType.HOT_SALE, current_user)}


@admin_router.get('/zones/local-life/services')
def admin_local_life(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone_for_admin(db, ZoneType.LOCAL_LIFE, current_user)}


@admin_router.post('/products')
def create_admin_product(
    payload: AdminProductCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.create_for_admin(db, current_user, payload.model_dump())}


@admin_router.put('/products/{product_id}')
def update_admin_product(
    product_id: int,
    payload: AdminProductUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.update_for_admin(db, product_id, current_user, payload.model_dump())}


@admin_router.patch('/products/{product_id}/submit-review')
def submit_admin_product_review(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.submit_review_for_admin(db, product_id, current_user)}


@admin_router.patch('/products/{product_id}/audit')
def audit_admin_product(
    product_id: int,
    payload: AdminProductAuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.audit_for_admin(db, product_id, current_user, payload.audit_status)}


@admin_router.patch('/products/{product_id}/status')
def update_admin_product_status(
    product_id: int,
    payload: AdminProductStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.update_status_for_admin(db, product_id, current_user, payload.status)}


@admin_router.delete('/products/{product_id}')
def delete_admin_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    ProductService.delete_for_admin(db, product_id, current_user)
    return {'code': 0, 'message': 'success', 'data': True}


@admin_router.get('/products/{product_id}/zone-config')
def admin_zone_config(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.get_zone_config_for_admin(db, product_id, current_user)}


@admin_router.put('/products/{product_id}/zone-config')
def update_admin_zone_config(
    product_id: int,
    payload: ProductZoneConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {
        'code': 0,
        'message': 'success',
        'data': ProductService.update_zone_config_for_admin(db, product_id, current_user, payload.model_dump()),
    }
