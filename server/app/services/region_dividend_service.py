"""后台区域代理配置、区域订单奖励计算与发放。"""

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.asset import UserAssetAccount, UserAssetLedger
from app.models.enums import AssetDirection, AssetType, MemberLevel
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductZoneConfig
from app.models.region_agent import RegionAgent
from app.models.region_dividend import RegionDividendFlow
from app.models.user import User
from app.utils.helpers import iso_datetime, now, quantize_amount, utc_naive


class RegionDividendService:
    """按订单收货区域向已生效的区代理和市代理发放余额奖励。"""

    AGENT_MEMBER_LEVEL = {
        'COUNTY_AGENT': MemberLevel.COUNTY_AGENT,
        'CITY_AGENT': MemberLevel.CITY_AGENT,
    }

    @staticmethod
    def process_order_dividend(db: Session, order: Order, address: dict) -> list[RegionDividendFlow]:
        province = str(address.get('province') or '').strip()
        city = str(address.get('city') or '').strip()
        district = str(address.get('district') or '').strip()
        if not province or not city:
            return []

        # Serialize concurrent completion/payment callbacks for the same order.
        db.query(Order.id).filter(Order.id == order.id).with_for_update().first()

        rewards = RegionDividendService._product_region_rewards(db, order.id)
        if not any(item['amount'] > 0 for item in rewards.values()):
            return []

        awarded: list[RegionDividendFlow] = []
        county_agent = RegionDividendService._active_agent(
            db,
            agent_type='COUNTY_AGENT',
            province=province,
            city=city,
            district=district,
        ) if district else None
        county_reward = rewards['COUNTY_AGENT']
        if county_agent and county_reward['amount'] > 0:
            flow = RegionDividendService._allocate_reward(
                db,
                order,
                county_agent,
                county_reward['base_amount'],
                county_reward['amount'],
                county_reward['product_count'],
                province,
                city,
                district,
            )
            if flow:
                awarded.append(flow)

        city_agent = RegionDividendService._active_agent(
            db,
            agent_type='CITY_AGENT',
            province=province,
            city=city,
            district='',
        )
        city_reward = rewards['CITY_AGENT']
        if city_agent and city_reward['amount'] > 0:
            flow = RegionDividendService._allocate_reward(
                db,
                order,
                city_agent,
                city_reward['base_amount'],
                city_reward['amount'],
                city_reward['product_count'],
                province,
                city,
                district,
            )
            if flow:
                awarded.append(flow)

        if awarded:
            db.commit()
        return awarded

    @staticmethod
    def _active_agent(
        db: Session,
        *,
        agent_type: str,
        province: str,
        city: str,
        district: str,
    ) -> RegionAgent | None:
        query = db.query(RegionAgent).filter(
            RegionAgent.agent_type == agent_type,
            RegionAgent.province == province,
            RegionAgent.city == city,
            RegionAgent.status == 'APPROVED',
            RegionAgent.agreement_signed.is_(True),
            or_(RegionAgent.effective_at.is_(None), RegionAgent.effective_at <= now()),
            or_(RegionAgent.expired_at.is_(None), RegionAgent.expired_at > now()),
        )
        if agent_type == 'COUNTY_AGENT':
            query = query.filter(RegionAgent.district == district)
        return query.order_by(RegionAgent.id.asc()).first()

    @staticmethod
    def _allocate_reward(
        db: Session,
        order: Order,
        agent: RegionAgent,
        base_amount: Decimal,
        reward_amount: Decimal,
        product_count: int,
        province: str,
        city: str,
        district: str,
    ) -> RegionDividendFlow | None:
        existed = db.query(RegionDividendFlow.id).filter(
            RegionDividendFlow.order_id == order.id,
            RegionDividendFlow.agent_id == agent.id,
        ).first()
        if existed:
            return None

        reward_amount = quantize_amount(reward_amount)
        if reward_amount <= 0:
            return None

        reward_district = district if agent.agent_type == 'COUNTY_AGENT' else ''
        flow = RegionDividendFlow(
            order_id=order.id,
            order_no=order.order_no,
            agent_id=agent.id,
            agent_user_id=agent.user_id,
            agent_type=agent.agent_type,
            province=province,
            city=city,
            district=reward_district,
            order_amount=quantize_amount(base_amount),
            dividend_rate=Decimal('0'),
            dividend_amount=reward_amount,
            status='SETTLED',
            settled_at=now(),
            remark=(
                f'商品专属{"区代" if agent.agent_type == "COUNTY_AGENT" else "市代"}分润'
                f'（{product_count}种商品）'
            ),
        )
        db.add(flow)
        RegionDividendService._credit_to_user_balance(db, agent.user_id, reward_amount, order)

        agent.total_orders = int(agent.total_orders or 0) + 1
        agent.total_dividend = float(
            quantize_amount(Decimal(str(agent.total_dividend or 0)) + reward_amount)
        )
        return flow

    @staticmethod
    def _product_region_rewards(db: Session, order_id: int) -> dict[str, dict]:
        result = {
            'COUNTY_AGENT': {
                'base_amount': Decimal('0.00'),
                'amount': Decimal('0.00'),
                'product_ids': set(),
                'product_count': 0,
            },
            'CITY_AGENT': {
                'base_amount': Decimal('0.00'),
                'amount': Decimal('0.00'),
                'product_ids': set(),
                'product_count': 0,
            },
        }
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        if not items:
            return result
        product_ids = {item.product_id for item in items}
        products = {
            product.id: product
            for product in db.query(Product).filter(Product.id.in_(product_ids)).all()
        }
        configs = {
            config.product_id: config
            for config in db.query(ProductZoneConfig).filter(
                ProductZoneConfig.product_id.in_(product_ids),
                ProductZoneConfig.custom_commission_enabled.is_(True),
            ).all()
        }
        role_mapping = {
            'COUNTY_AGENT': 'county_agent',
            'CITY_AGENT': 'city_agent',
        }
        for item in items:
            product = products.get(item.product_id)
            config = configs.get(item.product_id)
            if not product or not config:
                continue
            quantity = Decimal(str(item.quantity or 0))
            unit_price = Decimal(str(item.unit_price or 0))
            cost_price = Decimal(str(product.cost_price or 0))
            profit = quantize_amount(max(Decimal('0'), unit_price - cost_price) * quantity)
            method = str(config.custom_commission_method or 'RATE').upper()
            for agent_type, role in role_mapping.items():
                if not bool(getattr(config, f'custom_commission_{role}_enabled', False)):
                    continue
                if method == 'FIXED_AMOUNT':
                    unit_amount = Decimal(str(
                        getattr(config, f'custom_commission_{role}_amount', 0) or 0
                    ))
                    reward = quantize_amount(unit_amount * quantity)
                else:
                    percentage = Decimal(str(
                        getattr(config, f'custom_commission_{role}_rate', 0) or 0
                    ))
                    reward = quantize_amount(profit * percentage / Decimal('100'))
                if reward <= 0:
                    continue
                result[agent_type]['base_amount'] += profit
                result[agent_type]['amount'] += reward
                result[agent_type]['product_ids'].add(item.product_id)
        for data in result.values():
            data['base_amount'] = quantize_amount(data['base_amount'])
            data['amount'] = quantize_amount(data['amount'])
            data['product_count'] = len(data.pop('product_ids'))
        return result

    @staticmethod
    def _credit_to_user_balance(db: Session, user_id: int, amount: Decimal, order: Order) -> None:
        quantized = quantize_amount(amount)
        if quantized <= 0:
            return

        account = db.query(UserAssetAccount).filter(
            UserAssetAccount.user_id == user_id,
            UserAssetAccount.asset_type == AssetType.BALANCE,
        ).with_for_update().first()
        current_time = now()
        if account:
            before_amount = quantize_amount(account.available_amount or 0)
            after_amount = quantize_amount(before_amount + quantized)
            account.total_amount = quantize_amount((account.total_amount or 0) + quantized)
            account.available_amount = after_amount
            account.updated_at = current_time
        else:
            before_amount = Decimal('0.00')
            after_amount = quantized
            account = UserAssetAccount(
                user_id=user_id,
                asset_type=AssetType.BALANCE,
                total_amount=quantized,
                available_amount=quantized,
                frozen_amount=Decimal('0.00'),
                consumed_amount=Decimal('0.00'),
                withdrawn_amount=Decimal('0.00'),
                updated_at=current_time,
            )
            db.add(account)

        db.add(UserAssetLedger(
            user_id=user_id,
            asset_type=AssetType.BALANCE,
            direction=AssetDirection.INCOME,
            change_amount=quantized,
            before_amount=before_amount,
            after_amount=after_amount,
            business_type='REGION_DIVIDEND',
            source_id=order.id,
            source_no=order.order_no,
            remark=f'区域代理订单奖励，订单号：{order.order_no}',
            created_at=current_time,
        ))

    @staticmethod
    def reverse_order_dividend(db: Session, order: Order) -> None:
        flows = db.query(RegionDividendFlow).filter(
            RegionDividendFlow.order_id == order.id,
            RegionDividendFlow.status == 'SETTLED',
        ).all()
        for flow in flows:
            amount = quantize_amount(flow.dividend_amount)
            account = db.query(UserAssetAccount).filter(
                UserAssetAccount.user_id == flow.agent_user_id,
                UserAssetAccount.asset_type == AssetType.BALANCE,
            ).with_for_update().first()
            if not account or quantize_amount(account.available_amount) < amount:
                raise ConflictError('区域订单奖励余额不足，无法完成退款')

            before_amount = quantize_amount(account.available_amount)
            after_amount = quantize_amount(before_amount - amount)
            account.available_amount = after_amount
            account.total_amount = max(
                quantize_amount(account.total_amount) - amount, Decimal('0.00')
            )
            account.updated_at = now()
            db.add(UserAssetLedger(
                user_id=flow.agent_user_id,
                asset_type=AssetType.BALANCE,
                direction=AssetDirection.EXPENSE,
                change_amount=amount,
                before_amount=before_amount,
                after_amount=after_amount,
                business_type='REGION_DIVIDEND_REVERSAL',
                source_id=order.id,
                source_no=order.order_no,
                remark=f'订单退款，收回区域代理奖励：{order.order_no}',
                created_at=now(),
            ))
            flow.status = 'EXPIRED'
            flow.remark = '订单退款，奖励已收回'
            agent = db.get(RegionAgent, flow.agent_id)
            if agent:
                agent.total_orders = max(int(agent.total_orders or 0) - 1, 0)
                agent.total_dividend = float(max(
                    quantize_amount(Decimal(str(agent.total_dividend or 0)) - amount), Decimal('0.00')
                ))
        db.flush()

    @staticmethod
    def serialize_agent(agent: RegionAgent, user: User | None = None) -> dict:
        return {
            'id': agent.id,
            'user_id': agent.user_id,
            'user_nickname': user.nickname if user else None,
            'user_phone': user.phone if user else None,
            'member_level': user.member_level.value if user else None,
            'member_level_name': user.member_level.label if user else None,
            'province': agent.province,
            'city': agent.city,
            'district': agent.district,
            'agent_type': agent.agent_type,
            'status': agent.status,
            'total_orders': int(agent.total_orders or 0),
            'total_dividend': float(agent.total_dividend or 0),
            'effective_at': iso_datetime(agent.effective_at),
            'expired_at': iso_datetime(agent.expired_at),
            'agreement_signed': bool(agent.agreement_signed),
            'agreement_url': agent.agreement_url,
            'resource_proof_url': agent.resource_proof_url,
            'audit_remark': agent.audit_remark,
            'audited_at': iso_datetime(agent.audited_at),
            'created_at': iso_datetime(agent.created_at),
        }

    @staticmethod
    def create_agent(
        db: Session,
        user_id: int,
        admin_user_id: int,
        province: str,
        city: str,
        district: str,
        agent_type: str,
        effective_at=None,
        expired_at=None,
        remark: str | None = None,
    ) -> RegionAgent:
        effective_at = utc_naive(effective_at)
        expired_at = utc_naive(expired_at)
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError('代理用户不存在')
        clean_type, clean_province, clean_city, clean_district = RegionDividendService._normalize_agent_fields(
            agent_type, province, city, district
        )
        RegionDividendService._ensure_member_level_matches(user, clean_type)
        RegionDividendService._ensure_area_available(
            db,
            clean_type,
            clean_province,
            clean_city,
            clean_district,
        )
        if effective_at and expired_at and expired_at <= effective_at:
            raise ConflictError('失效时间必须晚于生效时间')

        agent = db.query(RegionAgent).filter(
            RegionAgent.user_id == user_id,
            RegionAgent.province == clean_province,
            RegionAgent.city == clean_city,
            RegionAgent.district == clean_district,
        ).first()
        if not agent:
            agent = RegionAgent(user_id=user_id)
            db.add(agent)
        agent.province = clean_province
        agent.city = clean_city
        agent.district = clean_district
        agent.agent_type = clean_type
        agent.status = 'APPROVED'
        agent.agreement_signed = True
        agent.dividend_rate = 0
        agent.effective_at = effective_at or now()
        agent.expired_at = expired_at
        agent.audited_by = admin_user_id
        agent.audited_at = now()
        agent.audit_remark = remark
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def update_agent(
        db: Session,
        agent_id: int,
        admin_user_id: int,
        province: str,
        city: str,
        district: str,
        agent_type: str,
        effective_at=None,
        expired_at=None,
        remark: str | None = None,
    ) -> RegionAgent:
        effective_at = utc_naive(effective_at)
        expired_at = utc_naive(expired_at)
        agent = db.get(RegionAgent, agent_id)
        if not agent:
            raise NotFoundError('区域代理不存在')
        clean_type, clean_province, clean_city, clean_district = RegionDividendService._normalize_agent_fields(
            agent_type, province, city, district
        )
        user = db.get(User, agent.user_id)
        if not user:
            raise NotFoundError('代理用户不存在')
        RegionDividendService._ensure_member_level_matches(user, clean_type)
        if effective_at and expired_at and expired_at <= effective_at:
            raise ConflictError('失效时间必须晚于生效时间')
        RegionDividendService._ensure_area_available(
            db,
            clean_type,
            clean_province,
            clean_city,
            clean_district,
            exclude_agent_id=agent.id,
        )
        duplicate = db.query(RegionAgent.id).filter(
            RegionAgent.id != agent.id,
            RegionAgent.user_id == agent.user_id,
            RegionAgent.province == clean_province,
            RegionAgent.city == clean_city,
            RegionAgent.district == clean_district,
        ).first()
        if duplicate:
            raise ConflictError('该用户在此区域已有代理配置')
        agent.agent_type = clean_type
        agent.province = clean_province
        agent.city = clean_city
        agent.district = clean_district
        agent.dividend_rate = 0
        agent.status = 'APPROVED'
        agent.agreement_signed = True
        agent.effective_at = effective_at or agent.effective_at or now()
        agent.expired_at = expired_at
        agent.audited_by = admin_user_id
        agent.audited_at = now()
        agent.audit_remark = remark
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def disable_agent(db: Session, agent_id: int, admin_user_id: int) -> RegionAgent:
        agent = db.get(RegionAgent, agent_id)
        if not agent:
            raise NotFoundError('区域代理不存在')
        agent.status = 'EXPIRED'
        agent.agreement_signed = False
        agent.expired_at = now()
        agent.audited_by = admin_user_id
        agent.audited_at = now()
        agent.audit_remark = '后台取消区域代理配置'
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def _normalize_agent_fields(
        agent_type: str,
        province: str,
        city: str,
        district: str,
    ) -> tuple[str, str, str, str]:
        clean_type = str(agent_type or '').strip().upper()
        if clean_type not in RegionDividendService.AGENT_MEMBER_LEVEL:
            raise ConflictError('代理类型仅支持区代理或市代理')
        clean_province = str(province or '').strip()
        clean_city = str(city or '').strip()
        clean_district = str(district or '').strip() if clean_type == 'COUNTY_AGENT' else ''
        if not clean_province or not clean_city:
            raise ConflictError('省份和城市不能为空')
        if clean_type == 'COUNTY_AGENT' and not clean_district:
            raise ConflictError('区代理必须选择区县')
        return clean_type, clean_province, clean_city, clean_district

    @staticmethod
    def _ensure_member_level_matches(user: User, agent_type: str) -> None:
        expected_level = RegionDividendService.AGENT_MEMBER_LEVEL[agent_type]
        if user.member_level != expected_level:
            raise ConflictError(f'仅可选择会员等级为{expected_level.label}的用户')

    @staticmethod
    def _ensure_area_available(
        db: Session,
        agent_type: str,
        province: str,
        city: str,
        district: str,
        exclude_agent_id: int | None = None,
    ) -> None:
        query = db.query(RegionAgent.id).filter(
            RegionAgent.agent_type == agent_type,
            RegionAgent.province == province,
            RegionAgent.city == city,
            RegionAgent.status == 'APPROVED',
            or_(RegionAgent.expired_at.is_(None), RegionAgent.expired_at > now()),
        )
        if exclude_agent_id is not None:
            query = query.filter(RegionAgent.id != exclude_agent_id)
        if agent_type == 'COUNTY_AGENT':
            query = query.filter(RegionAgent.district == district)
        if query.first():
            raise ConflictError('该区域已有生效代理')
