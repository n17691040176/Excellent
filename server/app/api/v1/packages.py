from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.api.v1.mobile_serializers import page_slice, serialize_order, serialize_package, serialize_product
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.package import (
    AdminPackageCreateRequest,
    AdminPackageStatusRequest,
    AdminPackageUpdateRequest,
    PackageOrderRequest,
)
from app.services.catalog_service import PackageService, ProductService

app_router = APIRouter(prefix='/app/packages')
admin_router = APIRouter(prefix='/admin/packages')


@app_router.get('')
def list_packages(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = page_slice(ProductService.list_app_products(db, current_user=current_user), page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_product(db, item) for item in rows]}


@app_router.get('/my-qualifications')
def my_qualifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': PackageService.my_qualifications(db, current_user.id)}


@app_router.get('/{package_id}')
def get_package(package_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    raw_product = ProductService.get_product(db, package_id)
    if raw_product:
        product = ProductService.get_product(db, package_id, current_user)
        if not product:
            raise NotFoundError('Product not found')
        return {'code': 0, 'message': 'success', 'data': serialize_product(db, product)}

    try:
        package = PackageService.get_package(db, package_id)
    except NotFoundError as exc:
        raise NotFoundError('Product not found') from exc
    return {'code': 0, 'message': 'success', 'data': serialize_package(package)}


@app_router.post('/{package_id}/orders')
def create_package_order(
    package_id: int,
    payload: PackageOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = PackageService.create_package_order(db, current_user.id, package_id, payload.use_ai_coupon_amount)
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, order)}


@admin_router.get('')
def admin_list_packages(db: Session = Depends(get_db), _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': PackageService.list_packages_for_admin(db)}


@admin_router.post('')
def admin_create_package(
    payload: AdminPackageCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': PackageService.create_for_admin(db, payload.model_dump())}


@admin_router.put('/{package_id}')
def admin_update_package(
    package_id: int,
    payload: AdminPackageUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': PackageService.update_for_admin(db, package_id, payload.model_dump())}


@admin_router.patch('/{package_id}/status')
def admin_update_package_status(
    package_id: int,
    payload: AdminPackageStatusRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': PackageService.update_status_for_admin(db, package_id, payload.status)}


@admin_router.delete('/{package_id}')
def admin_delete_package(
    package_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    PackageService.delete_for_admin(db, package_id)
    return {'code': 0, 'message': 'success', 'data': True}
