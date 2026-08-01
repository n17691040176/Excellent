from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, get_current_user_optional, require_roles
from app.api.v1.mobile_serializers import page_slice, serialize_product
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.models.enums import GlobalRole, ProductOwnerType, ProductStatus, ZoneType
from app.models.product import Product, ProductCategory
from app.models.user import User
from app.schemas.product import (
    AdminProductAuditRequest,
    AdminProductBatchMerchandiseRequest,
    AdminProductBatchStatusRequest,
    AdminProductCreateRequest,
    AdminProductStatusRequest,
    AdminProductUpdateRequest,
    ProductCategoryCreateRequest,
    ProductCategoryStatusRequest,
    ProductCategoryUpdateRequest,
    ProductZoneConfigUpdateRequest,
)
from app.services.catalog_service import ProductService
from app.services.cos_storage_service import CosStorageService
from app.utils.helpers import iso_datetime

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


@app_router.get('/products')
def list_products(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    rows = page_slice(ProductService.list_app_products(db, keyword, current_user), page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_product(db, item) for item in rows]}


@app_router.get('/categories')
def list_app_categories(db: Session = Depends(get_db)):
    rows = (
        db.query(ProductCategory)
        .filter(ProductCategory.status == 'active')
        .order_by(ProductCategory.sort_order.asc(), ProductCategory.id.asc())
        .all()
    )
    return {'code': 0, 'message': 'success', 'data': [_serialize_category(item) for item in rows]}


@app_router.get('/zones/repurchase/products')
def repurchase_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = ProductService.list_by_zone(db, ZoneType.REPURCHASE, current_user)
    return {'code': 0, 'message': 'success', 'data': [serialize_product(db, item) for item in rows]}


@app_router.get('/zones/self-operated/products')
def self_operated_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = ProductService.list_by_zone(db, ZoneType.SELF_OPERATED, current_user)
    return {'code': 0, 'message': 'success', 'data': [serialize_product(db, item) for item in rows]}


@app_router.get('/zones/hot-sale/products')
def hot_sale_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = ProductService.list_by_zone(db, ZoneType.HOT_SALE, current_user)
    return {'code': 0, 'message': 'success', 'data': [serialize_product(db, item) for item in rows]}


@app_router.get('/zones/local-life/services')
def local_life_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = ProductService.list_by_zone(db, ZoneType.LOCAL_LIFE, current_user)
    return {'code': 0, 'message': 'success', 'data': [serialize_product(db, item) for item in rows]}


@app_router.get('/products/{product_id}')
def product_detail(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = ProductService.get_product(db, product_id, current_user)
    if not product:
        raise NotFoundError('Product not found')
    return {'code': 0, 'message': 'success', 'data': serialize_product(db, product)}


@admin_router.get('/zones/repurchase/products')
def admin_repurchase(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone_for_admin(db, ZoneType.REPURCHASE, current_user)}


@admin_router.get('/zones/self-operated/products')
def admin_self_operated(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone_for_admin(db, ZoneType.SELF_OPERATED, current_user)}


@admin_router.get('/zones/hot-sale/products')
def admin_hot_sale(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone_for_admin(db, ZoneType.HOT_SALE, current_user)}


@admin_router.get('/zones/local-life/services')
def admin_local_life(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.list_by_zone_for_admin(db, ZoneType.LOCAL_LIFE, current_user)}


@admin_router.get('/products')
def admin_products(
    keyword: str | None = None,
    zone_type: ZoneType | None = None,
    status: ProductStatus | None = None,
    owner_type: ProductOwnerType | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {
        'code': 0,
        'message': 'success',
        'data': ProductService.list_for_admin(db, current_user, keyword, zone_type, status, owner_type),
    }


def _serialize_category(category: ProductCategory, product_count: int = 0) -> dict:
    return {
        'id': category.id,
        'name': category.name,
        'slug': category.slug,
        'sort_order': category.sort_order,
        'status': category.status,
        'product_count': product_count,
        'created_at': iso_datetime(category.created_at),
        'updated_at': iso_datetime(category.updated_at),
    }


def _ensure_category(db: Session, category_id: int) -> ProductCategory:
    category = db.get(ProductCategory, category_id)
    if not category:
        raise NotFoundError('Category not found')
    return category


def _validate_category_payload(name: str | None = None, slug: str | None = None, status: str | None = None) -> None:
    if name is not None and not name.strip():
        raise ConflictError('Category name required')
    if slug is not None and not slug.strip():
        raise ConflictError('Category slug required')
    if status is not None and status not in {'active', 'disabled'}:
        raise ConflictError('Category status must be active or disabled')


@admin_router.get('/categories')
def admin_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    rows = db.query(ProductCategory).order_by(ProductCategory.sort_order.asc(), ProductCategory.id.asc()).all()
    product_counts = dict(
        db.query(Product.category_id, func.count(Product.id))
        .filter(Product.category_id.is_not(None))
        .group_by(Product.category_id)
        .all()
    )
    return {
        'code': 0,
        'message': 'success',
        'data': [_serialize_category(item, int(product_counts.get(item.id, 0))) for item in rows],
    }


@admin_router.post('/categories')
def create_admin_category(
    payload: ProductCategoryCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    _validate_category_payload(payload.name, payload.slug, payload.status)
    slug = payload.slug.strip()
    exists = db.query(ProductCategory).filter(ProductCategory.slug == slug).first()
    if exists:
        raise ConflictError('Category slug already exists')
    category = ProductCategory(
        name=payload.name.strip(),
        slug=slug,
        sort_order=payload.sort_order,
        status=payload.status,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return {'code': 0, 'message': 'success', 'data': _serialize_category(category)}


@admin_router.put('/categories/{category_id}')
def update_admin_category(
    category_id: int,
    payload: ProductCategoryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    category = _ensure_category(db, category_id)
    _validate_category_payload(payload.name, None, payload.status)
    if payload.name is not None:
        category.name = payload.name.strip()
    if payload.sort_order is not None:
        category.sort_order = payload.sort_order
    if payload.status is not None:
        category.status = payload.status
    db.commit()
    db.refresh(category)
    return {'code': 0, 'message': 'success', 'data': _serialize_category(category)}


@admin_router.patch('/categories/{category_id}/status')
def update_admin_category_status(
    category_id: int,
    payload: ProductCategoryStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    category = _ensure_category(db, category_id)
    _validate_category_payload(status=payload.status)
    category.status = payload.status
    db.commit()
    db.refresh(category)
    return {'code': 0, 'message': 'success', 'data': _serialize_category(category)}


@admin_router.delete('/categories/{category_id}')
def delete_admin_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    category = _ensure_category(db, category_id)
    product_count = db.query(func.count(Product.id)).filter(Product.category_id == category.id).scalar() or 0
    if product_count:
        raise ConflictError('Category contains products and cannot be deleted')
    db.delete(category)
    db.commit()
    return {'code': 0, 'message': 'success', 'data': True}


@admin_router.get('/products/import-template')
def admin_product_import_template(_: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return Response(
        content=ProductService.build_import_template_csv(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=product-import-template.csv'},
    )


@admin_router.post('/products')
def create_admin_product(
    payload: AdminProductCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': ProductService.create_for_admin(db, current_user, payload.model_dump())}


@admin_router.post('/products/upload-image')
async def upload_admin_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    del current_user
    try:
        content = await file.read(settings.tencent_cos_max_upload_size + 1)
        result = CosStorageService.upload_product_image(file.filename or '', file.content_type or '', content)
        return {'code': 0, 'message': 'success', 'data': result}
    finally:
        await file.close()


@admin_router.patch('/products/batch-merchandise')
def batch_admin_product_merchandise(
    payload: AdminProductBatchMerchandiseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {
        'code': 0,
        'message': 'success',
        'data': ProductService.batch_update_merchandise_for_admin(db, current_user, payload.model_dump()),
    }


@admin_router.patch('/products/batch-status')
def batch_admin_product_status(
    payload: AdminProductBatchStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {
        'code': 0,
        'message': 'success',
        'data': ProductService.batch_update_status_for_admin(db, current_user, payload.model_dump()),
    }


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
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
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


@admin_router.post('/products/import')
async def import_admin_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    try:
        content = await file.read()
        return {
            'code': 0,
            'message': 'success',
            'data': ProductService.import_products_for_admin(db, current_user, file.filename or '', content),
        }
    finally:
        await file.close()


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
