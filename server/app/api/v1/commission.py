from datetime import timedelta
from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.api.v1.mobile_serializers import page_slice, serialize_commission_flow, serialize_withdraw_request
from app.db.session import get_db
from app.models.enums import GlobalRole, WithdrawType
from app.models.user import User
from app.schemas.commission import (
    WithdrawConfigUpdateRequest,
    WithdrawCreateRequest,
    WithdrawRejectRequest,
    WithdrawReviewRequest,
)
from app.services.commission_service import CommissionService
from app.utils.helpers import now
from app.utils.spreadsheet import build_xlsx

app_router = APIRouter(prefix='/app')
admin_router = APIRouter(prefix='/admin')


@app_router.get('/commission/summary')
def commission_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = CommissionService.summary(db, current_user.id)
    data['withdrawable_amount'] = data.get('available_amount', 0)
    return {'code': 0, 'message': 'success', 'data': data}


@app_router.get('/commission/flows')
def commission_flows(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = page_slice(CommissionService.flows(db, current_user.id), page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_commission_flow(item) for item in rows]}


@app_router.post('/withdraws')
def create_withdraw(payload: WithdrawCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = CommissionService.create_withdraw(
        db,
        current_user.id,
        WithdrawType.COMMISSION,
        payload.amount,
        payload.bank_card_id,
        payload.remark,
    )
    return {'code': 0, 'message': 'success', 'data': serialize_withdraw_request(record)}


@app_router.get('/withdraws')
def my_withdraws(
    recent_days: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = CommissionService.list_withdraws(db, current_user.id)
    if recent_days and recent_days > 0:
        cutoff = now() - timedelta(days=recent_days)
        rows = [item for item in rows if item.created_at and item.created_at >= cutoff]
    return {'code': 0, 'message': 'success', 'data': [serialize_withdraw_request(item) for item in rows]}


@app_router.get('/withdraws/config')
def app_withdraw_config(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': CommissionService.withdraw_config(db)}


@admin_router.get('/commission/flows')
def admin_commission_flows(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    data = CommissionService.list_flows_page_for_admin(
        db,
        current_user,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.get('/commission/product-rules')
def admin_commission_product_rules(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    zone_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    data = CommissionService.list_product_rules_for_admin(
        db,
        current_user,
        keyword=keyword,
        zone_type=zone_type,
        page=page,
        page_size=page_size,
    )
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.get('/commission/users')
def admin_commission_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    data = CommissionService.list_user_commissions_page_for_admin(
        db,
        current_user,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.get('/withdraws')
def admin_withdraws(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    data = CommissionService.list_withdraws_for_admin(db, current_user, keyword, status, start_date, end_date, page, page_size)
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.get('/withdraws/export')
def export_admin_withdraws(
    keyword: str | None = Query(default=None),
    status: str | None = Query(default='APPROVED'),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    items = CommissionService.export_withdraws_for_admin(db, current_user, keyword, status, start_date, end_date)
    headers = [
        '提现单号', '用户ID', '用户昵称', '手机号', '团队', '持卡人', '银行名称', '开户支行',
        '银行卡号', '申请金额', '手续费率(%)', '手续费', '实际打款金额', '状态', '申请时间',
        '审核时间', '审核人ID', '审核备注',
    ]
    rows = [[
        item['source_no'], item['user_id'], item['user_nickname'], item['user_phone'], item['team_name'],
        item['bank_holder_name'], item['bank_name'], item['bank_branch_name'], item.get('bank_card_number', ''),
        f"{item['amount']:.2f}", f"{item['fee_rate']:.2f}", f"{item['fee_amount']:.2f}",
        f"{item['net_amount']:.2f}", item['status'], item['created_at'], item['reviewed_at'],
        item['reviewed_by'], item['review_remark'],
    ] for item in items]
    content = build_xlsx(headers, rows, '提现打款清单')
    filename = f'withdraws-{now().strftime("%Y%m%d-%H%M%S")}.xlsx'
    return StreamingResponse(
        BytesIO(content),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@admin_router.get('/commission/withdraw-config')
def admin_withdraw_config(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': CommissionService.withdraw_config(db)}


@admin_router.put('/commission/withdraw-config')
def update_admin_withdraw_config(
    payload: WithdrawConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    data = CommissionService.update_withdraw_config(db, payload.fee_rate, payload.min_amount, payload.max_amount, current_user.id)
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.patch('/withdraws/{withdraw_id}/approve')
def approve_withdraw(
    withdraw_id: int,
    payload: WithdrawReviewRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    record = CommissionService.approve_withdraw(db, withdraw_id, current_user, payload.remark if payload else None)
    return {'code': 0, 'message': 'success', 'data': serialize_withdraw_request(record)}


@admin_router.patch('/withdraws/{withdraw_id}/reject')
def reject_withdraw(
    withdraw_id: int,
    payload: WithdrawRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    record = CommissionService.reject_withdraw(db, withdraw_id, current_user, payload.remark)
    return {'code': 0, 'message': 'success', 'data': serialize_withdraw_request(record)}


@admin_router.patch('/withdraws/{withdraw_id}/pay')
def pay_withdraw(
    withdraw_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    record = CommissionService.pay_withdraw(db, withdraw_id, current_user)
    return {'code': 0, 'message': 'success', 'data': serialize_withdraw_request(record)}
