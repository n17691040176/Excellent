"""后台会员区域代理与订单奖励管理接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.region_agent import RegionAgent
from app.models.region_dividend import RegionDividendFlow
from app.models.user import User
from app.schemas.region_agent import RegionAgentAuditRequest, RegionAgentRewardConfigRequest
from app.services.admin_scope import AdminScopeService
from app.services.region_dividend_service import RegionDividendService

router = APIRouter(prefix='/admin/region-agents', tags=['后台区域代理管理'])


def _scope_user_query(query, current_user: User):
    if not AdminScopeService.has_global_scope(current_user):
        query = query.filter(User.team_id == AdminScopeService.require_team_id(current_user))
    return query


def _ensure_agent_visible(db: Session, current_user: User, agent_id: int) -> None:
    query = _scope_user_query(
        db.query(RegionAgent.id).join(User, User.id == RegionAgent.user_id), current_user
    )
    if not query.filter(RegionAgent.id == agent_id).first():
        raise NotFoundError('区域代理不存在')


@router.get('/list')
def list_region_agents(
    status: str | None = Query(None),
    agent_type: str | None = Query(None),
    province: str | None = Query(None),
    city: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    query = _scope_user_query(
        db.query(RegionAgent, User).join(User, User.id == RegionAgent.user_id), current_user
    )
    if status:
        query = query.filter(RegionAgent.status == status)
    if agent_type:
        query = query.filter(RegionAgent.agent_type == agent_type)
    if province:
        query = query.filter(RegionAgent.province.like(f'%{province.strip()}%'))
    if city:
        query = query.filter(RegionAgent.city.like(f'%{city.strip()}%'))
    if keyword and keyword.strip():
        like_value = f'%{keyword.strip()}%'
        query = query.filter(or_(
            RegionAgent.province.like(like_value),
            RegionAgent.city.like(like_value),
            RegionAgent.district.like(like_value),
            User.nickname.like(like_value),
            User.phone.like(like_value),
        ))

    total = query.count()
    rows = query.order_by(RegionAgent.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {'code': 0, 'message': 'success', 'data': {
        'items': [RegionDividendService.serialize_agent(agent, user) for agent, user in rows],
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
    _ensure_agent_visible(db, current_user, agent_id)
    agent = RegionDividendService.audit_region_agent(
        db=db,
        agent_id=agent_id,
        admin_user_id=current_user.id,
        approved=payload.approved,
        remark=payload.remark,
        dividend_rate=payload.dividend_rate,
    )
    user = db.get(User, agent.user_id)
    return {
        'code': 0,
        'message': '审核成功' if payload.approved else '已拒绝',
        'data': RegionDividendService.serialize_agent(agent, user),
    }


@router.patch('/{agent_id}/reward-config')
def update_region_reward_config(
    agent_id: int,
    payload: RegionAgentRewardConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    _ensure_agent_visible(db, current_user, agent_id)
    agent = RegionDividendService.update_reward_config(db, agent_id, payload.dividend_rate)
    user = db.get(User, agent.user_id)
    return {
        'code': 0,
        'message': '区域订单奖励比例已更新',
        'data': RegionDividendService.serialize_agent(agent, user),
    }


@router.get('/summary')
def get_region_agent_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    agent_query = _scope_user_query(
        db.query(RegionAgent).join(User, User.id == RegionAgent.user_id), current_user
    )
    dividend_query = _scope_user_query(
        db.query(RegionDividendFlow).join(User, User.id == RegionDividendFlow.agent_user_id), current_user
    ).filter(RegionDividendFlow.status == 'SETTLED')
    return {'code': 0, 'message': 'success', 'data': {
        'total_agents': agent_query.filter(RegionAgent.status == 'APPROVED').count(),
        'pending_count': agent_query.filter(RegionAgent.status == 'PENDING').count(),
        'total_dividend_records': dividend_query.count(),
        'total_dividend_amount': float(
            dividend_query.with_entities(func.sum(RegionDividendFlow.dividend_amount)).scalar() or 0
        ),
    }}


@router.get('/dividends')
def list_region_dividends(
    status: str | None = Query(None),
    agent_type: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    query = _scope_user_query(
        db.query(RegionDividendFlow, User).join(User, User.id == RegionDividendFlow.agent_user_id),
        current_user,
    )
    if status:
        query = query.filter(RegionDividendFlow.status == status)
    if agent_type:
        query = query.filter(RegionDividendFlow.agent_type == agent_type)
    if keyword and keyword.strip():
        like_value = f'%{keyword.strip()}%'
        query = query.filter(or_(
            RegionDividendFlow.order_no.like(like_value),
            RegionDividendFlow.province.like(like_value),
            RegionDividendFlow.city.like(like_value),
            RegionDividendFlow.district.like(like_value),
            User.nickname.like(like_value),
            User.phone.like(like_value),
        ))

    total = query.count()
    rows = query.order_by(RegionDividendFlow.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        'id': flow.id,
        'order_id': flow.order_id,
        'order_no': flow.order_no,
        'agent_id': flow.agent_id,
        'agent_user_id': flow.agent_user_id,
        'agent_nickname': user.nickname,
        'agent_phone': user.phone,
        'member_level': user.member_level.value,
        'member_level_name': user.member_level.label,
        'agent_type': flow.agent_type,
        'province': flow.province,
        'city': flow.city,
        'district': flow.district,
        'order_amount': float(flow.order_amount),
        'dividend_rate': float(flow.dividend_rate),
        'dividend_amount': float(flow.dividend_amount),
        'status': flow.status,
        'settled_at': flow.settled_at.isoformat() if flow.settled_at else None,
        'created_at': flow.created_at.isoformat() if flow.created_at else None,
    } for flow, user in rows]
    return {'code': 0, 'message': 'success', 'data': {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
    }}
