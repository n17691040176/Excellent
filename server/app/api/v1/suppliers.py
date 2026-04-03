from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.supplier import (
    ProductQualificationApplyRequest,
    ProductQualificationAuditRequest,
    SupplierAgreementCreateRequest,
    SupplierApplyRequest,
)
from app.services.supplier_service import SupplierService

app_router = APIRouter(prefix='/app')
admin_router = APIRouter(prefix='/admin')


@app_router.post('/suppliers/apply')
def apply_supplier(payload: SupplierApplyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    supplier = SupplierService.apply_supplier(db, current_user, payload.model_dump())
    return {'code': 0, 'message': 'success', 'data': supplier}


@app_router.get('/suppliers/my')
def my_suppliers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': SupplierService.my_suppliers(db, current_user.id)}


@app_router.post('/suppliers/{supplier_id}/agreements')
def add_agreement(
    supplier_id: int,
    payload: SupplierAgreementCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    agreement = SupplierService.add_agreement(db, supplier_id, payload.agreement_type, payload.file_url)
    return {'code': 0, 'message': 'success', 'data': agreement}


@app_router.get('/product-qualifications/my')
def my_qualifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': SupplierService.list_my_qualifications(db, current_user.id)}


@app_router.post('/product-qualifications')
def apply_qualification(
    payload: ProductQualificationApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = SupplierService.apply_product_qualification(db, current_user, payload.model_dump())
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.get('/suppliers')
def admin_suppliers(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': SupplierService.list_for_admin(db, current_user)}


@admin_router.get('/product-qualifications')
def admin_qualifications(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': SupplierService.list_qualifications_for_admin(db, current_user)}


@admin_router.get('/product-qualification-ledgers')
def admin_qualification_ledgers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': SupplierService.list_qualification_ledgers_for_admin(db, current_user)}


@admin_router.patch('/product-qualifications/{qualification_id}/audit')
def audit_qualification(
    qualification_id: int,
    payload: ProductQualificationAuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    data = SupplierService.audit_product_qualification(
        db,
        qualification_id,
        current_user,
        payload.audit_status,
        payload.audit_remark,
    )
    return {'code': 0, 'message': 'success', 'data': data}
