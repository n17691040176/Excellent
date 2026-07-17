"""区域代理API"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.region_dividend_service import RegionDividendService

router = APIRouter(prefix='/region-agents', tags=['区域代理'])


@router.post('/apply')
def apply_region_agent(
    province: str = Query(..., description='省份'),
    city: str = Query(..., description='城市'),
    district: str = Query('', description='区县'),
    agent_type: str = Query('COUNTY_AGENT', description='代理类型: COUNTY_AGENT, CITY_AGENT'),
    resource_proof_url: str | None = Query(None, description='一手资源证明URL'),
    agreement_url: str | None = Query(None, description='协议URL'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户申请区域代理"""
    agent = RegionDividendService.apply_region_agent(
        db=db,
        user_id=current_user.id,
        province=province,
        city=city,
        district=district,
        agent_type=agent_type,
        resource_proof_url=resource_proof_url,
        agreement_url=agreement_url,
    )
    return {'code': 0, 'message': '区域代理申请已提交', 'data': {
        'id': agent.id,
        'status': agent.status,
    }}


@router.get('/my')
def get_my_region_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我的区域代理申请"""
    summary = RegionDividendService.get_agent_summary(db, current_user.id)
    return {'code': 0, 'message': 'success', 'data': summary}


@router.get('/dividends')
def get_my_dividends(
    status: str | None = Query(None, description='状态: FROZEN, SETTLED, EXPIRED'),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我的区域分红记录"""
    flows = RegionDividendService.get_agent_dividends(db, current_user.id, status, limit)
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
    } for f in flows]
    return {'code': 0, 'message': 'success', 'data': data}
