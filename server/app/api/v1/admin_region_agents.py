"""后台区域代理管理API"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.region_agent import RegionAgent
from app.models.user import User
from app.schemas.region_agent import RegionAgentAuditRequest
from app.services.region_dividend_service import RegionDividendService

router = APIRouter(prefix='/admin/region-agents', tags=['后台区域代理管理'])


@router.get('/list')
def list_region_agents(
    status: str | None = Query(None, description='状态筛选'),
    agent_type: str | None = Query(None, description='代理类型'),
    province: str | None = Query(None, description='省份'),
    city: str | None = Query(None, description='城市'),
    keyword: str | None = Query(None, description='关键词搜索'),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    """后台获取区域代理申请列表"""
    query = db.query(RegionAgent)

    if status:
        query = query.filter(RegionAgent.status == status)
    if agent_type:
        query = query.filter(RegionAgent.agent_type == agent_type)
    if province:
        query = query.filter(RegionAgent.province.like(f'%{province}%'))
    if city:
        query = query.filter(RegionAgent.city.like(f'%{city}%'))
    if keyword:
        query = query.filter(
            or_(
                RegionAgent.province.like(f'%{keyword}%'),
                RegionAgent.city.like(f'%{keyword}%'),
                RegionAgent.district.like(f'%{keyword}%'),
            )
        )

    total = query.count()
    items = query.order_by(RegionAgent.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    data = [{
        'id': a.id,
        'user_id': a.user_id,
        'province': a.province,
        'city': a.city,
        'district': a.district,
        'agent_type': a.agent_type,
        'status': a.status,
        'dividend_rate': a.dividend_rate,
        'total_orders': a.total_orders,
        'total_dividend': float(a.total_dividend or 0),
        'effective_at': a.effective_at.isoformat() if a.effective_at else None,
        'expired_at': a.expired_at.isoformat() if a.expired_at else None,
        'agreement_signed': a.agreement_signed,
        'resource_proof_url': a.resource_proof_url,
        'audit_remark': a.audit_remark,
        'audited_at': a.audited_at.isoformat() if a.audited_at else None,
        'created_at': a.created_at.isoformat(),
    } for a in items]

    return {'code': 0, 'message': 'success', 'data': {
        'items': data,
        'total': total,
        'page': page,
        'page_size': page_size,
    }}


@router.post('/audit/{agent_id}')
def audit_region_agent(
    agent_id: int,
    payload: RegionAgentAuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    """后台审核区域代理申请"""
    agent = RegionDividendService.audit_region_agent(
        db=db,
        agent_id=agent_id,
        admin_user_id=current_user.id,
        approved=payload.approved,
        remark=payload.remark,
        dividend_rate=payload.dividend_rate,
    )
    return {'code': 0, 'message': '审核成功' if payload.approved else '已拒绝', 'data': {
        'id': agent.id,
        'status': agent.status,
    }}


@router.get('/summary')
def get_region_agent_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    """获取区域代理统计汇总"""
    total_agents = db.query(RegionAgent).filter(RegionAgent.status == 'APPROVED').count()
    pending_count = db.query(RegionAgent).filter(RegionAgent.status == 'PENDING').count()

    from app.models.region_dividend import RegionDividendFlow
    total_dividend = db.query(RegionDividendFlow).filter(
        RegionDividendFlow.status == 'SETTLED'
    ).count()

    from sqlalchemy import func
    total_dividend_amount = db.query(func.sum(RegionDividendFlow.dividend_amount)).filter(
        RegionDividendFlow.status == 'SETTLED'
    ).scalar() or 0

    return {'code': 0, 'message': 'success', 'data': {
        'total_agents': total_agents,
        'pending_count': pending_count,
        'total_dividend_records': total_dividend,
        'total_dividend_amount': float(total_dividend_amount),
    }}


@router.get('/dividends')
def list_region_dividends(
    status: str | None = Query(None, description='状态筛选'),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    """获取区域分红记录列表"""
    from app.models.region_dividend import RegionDividendFlow

    query = db.query(RegionDividendFlow)
    if status:
        query = query.filter(RegionDividendFlow.status == status)

    items = query.order_by(RegionDividendFlow.id.desc()).limit(limit).all()

    data = [{
        'id': f.id,
        'order_no': f.order_no,
        'agent_type': f.agent_type,
        'province': f.province,
        'city': f.city,
        'district': f.district,
        'order_amount': float(f.order_amount),
        'dividend_rate': float(f.dividend_rate),
        'dividend_amount': float(f.dividend_amount),
        'status': f.status,
        'settled_at': f.settled_at.isoformat() if f.settled_at else None,
        'created_at': f.created_at.isoformat(),
    } for f in items]

    return {'code': 0, 'message': 'success', 'data': data}
