"""区域分红服务 - 处理订单完成后的区域代理分红"""
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.asset import UserAssetLedger
from app.models.enums import AssetDirection, AssetType
from app.models.order import Order
from app.models.region_agent import RegionAgent
from app.models.region_dividend import RegionDividendFlow
from app.utils.helpers import now, quantize_amount


class RegionDividendService:
    """区域订单分红服务"""

    # 默认分红比例（可在后台配置）
    DEFAULT_COUNTY_AGENT_RATE = Decimal('1.00')   # 区县代理默认1%
    DEFAULT_CITY_AGENT_RATE = Decimal('0.50')     # 市代理默认0.5%

    @staticmethod
    def process_order_dividend(db: Session, order: Order, address: dict) -> None:
        """
        订单确认完成后处理区域分红

        Args:
            db: 数据库会话
            order: 订单对象
            address: 收货地址信息，包含 province, city, district
        """
        province = address.get('province', '').strip()
        city = address.get('city', '').strip()

        if not province and not city:
            return

        # 订单实付金额（用于计算分红基数）
        order_amount = float(order.paid_amount or order.payable_amount or 0)
        if order_amount <= 0:
            return

        # 区县代理分红（精确匹配区）
        RegionDividendService._process_county_agent_dividend(
            db, order, address, order_amount
        )

        # 市代理分红（精确匹配市，但范围更广）
        RegionDividendService._process_city_agent_dividend(
            db, order, address, order_amount
        )

        db.commit()

    @staticmethod
    def _process_county_agent_dividend(
        db: Session,
        order: Order,
        address: dict,
        order_amount: float
    ) -> None:
        """处理区县代理分红 - 订单收货地址所在区的区县代理获得分红"""
        province = address.get('province', '').strip()
        city = address.get('city', '').strip()
        district = address.get('district', '').strip()

        if not district:
            return

        # 查询有效的区县代理（精确匹配区）
        agents = db.query(RegionAgent).filter(
            RegionAgent.district == district,
            RegionAgent.status == 'APPROVED',
            RegionAgent.agreement_signed.is_(True),
            or_(
                RegionAgent.effective_at.is_(None),
                RegionAgent.effective_at <= now()
            ),
            or_(
                RegionAgent.expired_at.is_(None),
                RegionAgent.expired_at > now()
            )
        ).all()

        if not agents:
            return

        # 获取分红比例（使用配置的比例或默认比例）
        rate = Decimal(str(agents[0].dividend_rate or RegionDividendService.DEFAULT_COUNTY_AGENT_RATE))
        # 比例是百分比形式，如 1% = 1.00，需要除以100
        actual_rate = rate / Decimal('100')
        dividend_amount = quantize_amount(order_amount * float(actual_rate))

        if dividend_amount <= 0:
            return

        agent = agents[0]

        # 创建分红流水
        flow = RegionDividendFlow(
            order_id=order.id,
            order_no=order.order_no,
            agent_id=agent.id,
            agent_user_id=agent.user_id,
            agent_type='COUNTY_AGENT',
            province=province,
            city=city,
            district=district,
            order_amount=order_amount,
            dividend_rate=float(actual_rate * 100),  # 存为百分比形式
            dividend_amount=float(dividend_amount),
            status='SETTLED',
            settled_at=now(),
            remark=f'区县代理分红：{district}'
        )
        db.add(flow)

        # 直接发放到用户余额（订单完成后立即分红）
        RegionDividendService._credit_to_user_balance(
            db, agent.user_id, float(dividend_amount), order, agent.id
        )

        # 更新代理统计
        agent.total_orders += 1
        agent.total_dividend = float(
            quantize_amount(agent.total_dividend or 0) + dividend_amount
        )

    @staticmethod
    def _process_city_agent_dividend(
        db: Session,
        order: Order,
        address: dict,
        order_amount: float
    ) -> None:
        """处理市代理分红 - 订单收货地址所在市的市代理获得分红"""
        province = address.get('province', '').strip()
        city = address.get('city', '').strip()

        if not city:
            return

        # 查询有效的市代理（精确匹配市）
        agents = db.query(RegionAgent).filter(
            RegionAgent.city == city,
            RegionAgent.agent_type == 'CITY_AGENT',
            RegionAgent.status == 'APPROVED',
            RegionAgent.agreement_signed.is_(True),
            or_(
                RegionAgent.effective_at.is_(None),
                RegionAgent.effective_at <= now()
            ),
            or_(
                RegionAgent.expired_at.is_(None),
                RegionAgent.expired_at > now()
            )
        ).all()

        if not agents:
            return

        # 获取分红比例
        rate = Decimal(str(agents[0].dividend_rate or RegionDividendService.DEFAULT_CITY_AGENT_RATE))
        actual_rate = rate / Decimal('100')
        dividend_amount = quantize_amount(order_amount * float(actual_rate))

        if dividend_amount <= 0:
            return

        agent = agents[0]

        # 创建分红流水
        flow = RegionDividendFlow(
            order_id=order.id,
            order_no=order.order_no,
            agent_id=agent.id,
            agent_user_id=agent.user_id,
            agent_type='CITY_AGENT',
            province=province,
            city=city,
            district='',
            order_amount=order_amount,
            dividend_rate=float(actual_rate * 100),
            dividend_amount=float(dividend_amount),
            status='SETTLED',
            settled_at=now(),
            remark=f'市代理分红：{city}'
        )
        db.add(flow)

        # 直接发放到用户余额
        RegionDividendService._credit_to_user_balance(
            db, agent.user_id, float(dividend_amount), order, agent.id
        )

        # 更新代理统计
        agent.total_orders += 1
        agent.total_dividend = float(
            quantize_amount(agent.total_dividend or 0) + dividend_amount
        )

    @staticmethod
    def _credit_to_user_balance(
        db: Session,
        user_id: int,
        amount: float,
        order: Order,
        region_agent_id: int
    ) -> None:
        """将分红金额发放到用户余额"""
        quantized = quantize_amount(amount)
        if quantized <= 0:
            return

        from app.models.asset import UserAssetAccount

        # 获取或创建用户资产账户
        account = db.query(UserAssetAccount).filter(
            UserAssetAccount.user_id == user_id,
            UserAssetAccount.asset_type == AssetType.BALANCE
        ).first()

        if account:
            account.available_amount = quantize_amount(
                account.available_amount + quantized
            )
            account.updated_at = now()
        else:
            account = UserAssetAccount(
                user_id=user_id,
                asset_type=AssetType.BALANCE,
                total_amount=quantized,
                available_amount=quantized,
                frozen_amount=Decimal('0'),
            )
            db.add(account)

        # 记录资产流水
        ledger = UserAssetLedger(
            user_id=user_id,
            asset_type=AssetType.BALANCE,
            direction=AssetDirection.INCOME,
            change_amount=quantized,
            before_amount=quantize_amount(account.available_amount - quantized if account else 0),
            after_amount=quantized,
            business_type='REGION_DIVIDEND',
            source_id=order.id,
            source_no=order.order_no,
            remark=f'区域代理订单分红，订单号：{order.order_no}'
        )
        db.add(ledger)

    @staticmethod
    def get_agent_dividends(
        db: Session,
        user_id: int,
        status: str | None = None,
        limit: int = 50
    ) -> list[RegionDividendFlow]:
        """获取用户的区域分红记录"""
        query = db.query(RegionDividendFlow).filter(
            RegionDividendFlow.agent_user_id == user_id
        )
        if status:
            query = query.filter(RegionDividendFlow.status == status)
        return query.order_by(RegionDividendFlow.id.desc()).limit(limit).all()

    @staticmethod
    def get_agent_summary(db: Session, user_id: int) -> dict:
        """获取用户区域代理分红汇总"""
        agents = db.query(RegionAgent).filter(
            RegionAgent.user_id == user_id,
            RegionAgent.status == 'APPROVED'
        ).all()

        total_dividend = Decimal('0')
        total_orders = 0
        agent_info = []

        for agent in agents:
            total_dividend += Decimal(str(agent.total_dividend or 0))
            total_orders += (agent.total_orders or 0)
            agent_info.append({
                'id': agent.id,
                'agent_type': agent.agent_type,
                'province': agent.province,
                'city': agent.city,
                'district': agent.district,
                'dividend_rate': agent.dividend_rate,
                'total_orders': agent.total_orders,
                'total_dividend': float(agent.total_dividend or 0),
                'effective_at': agent.effective_at,
                'expired_at': agent.expired_at,
            })

        return {
            'total_dividend': float(total_dividend),
            'total_orders': total_orders,
            'agents': agent_info
        }

    @staticmethod
    def apply_region_agent(
        db: Session,
        user_id: int,
        province: str,
        city: str,
        district: str,
        agent_type: str,
        resource_proof_url: str | None = None,
        agreement_url: str | None = None
    ) -> RegionAgent:
        """用户申请区域代理"""
        # 检查是否已有申请中的代理
        existing = db.query(RegionAgent).filter(
            RegionAgent.user_id == user_id,
            RegionAgent.province == province,
            RegionAgent.city == city,
            RegionAgent.district == district,
            RegionAgent.status.in_(['PENDING', 'APPROVED'])
        ).first()

        if existing:
            from app.core.exceptions import ConflictError
            raise ConflictError('该区域代理申请已存在')

        # 设置默认分红比例
        if agent_type == 'CITY_AGENT':
            default_rate = RegionDividendService.DEFAULT_CITY_AGENT_RATE
        else:
            default_rate = RegionDividendService.DEFAULT_COUNTY_AGENT_RATE

        agent = RegionAgent(
            user_id=user_id,
            province=province,
            city=city,
            district=district,
            agent_type=agent_type,
            status='PENDING',
            resource_proof_url=resource_proof_url,
            agreement_url=agreement_url,
            dividend_rate=float(default_rate),
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def audit_region_agent(
        db: Session,
        agent_id: int,
        admin_user_id: int,
        approved: bool,
        remark: str | None = None,
        dividend_rate: float | None = None
    ) -> RegionAgent:
        """后台审核区域代理申请"""
        agent = db.get(RegionAgent, agent_id)
        if not agent:
            from app.core.exceptions import NotFoundError
            raise NotFoundError('区域代理申请不存在')

        if agent.status != 'PENDING':
            from app.core.exceptions import ConflictError
            raise ConflictError('该申请已审核过')

        if approved:
            agent.status = 'APPROVED'
            agent.effective_at = now()
            # 默认1年有效期
            from datetime import timedelta
            agent.expired_at = now() + timedelta(days=365)
            if dividend_rate is not None:
                agent.dividend_rate = dividend_rate
        else:
            agent.status = 'REJECTED'

        agent.audited_by = admin_user_id
        agent.audited_at = now()
        agent.audit_remark = remark
        db.commit()
        db.refresh(agent)
        return agent
