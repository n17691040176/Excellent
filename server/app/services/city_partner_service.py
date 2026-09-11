from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.payment_config import UNPAID_ORDER_EXPIRE_MINUTES
from app.models.city_partner import CityPartnerPurchase, CityPartnerRotationFlow, CityPartnerSeat
from app.models.commission import CommissionConfig, UserCommission
from app.models.enums import (
    CityPartnerRotationStatus,
    CityPartnerSeatStatus,
    CommissionMode,
    OrderStatus,
    OrderType,
    PayStatus,
)
from app.models.order import Order
from app.models.user import User
from app.services.commission_accounts import system_account
from app.services.commission_audit import record_rule_change, rule_snapshot
from app.utils.helpers import iso_datetime, now, quantize_amount


class CityPartnerService:
    """城市合伙人席位管理、竞价轮换及独立资金结算。"""

    @staticmethod
    def mobile_enabled(db: Session, *, lock: bool = False) -> bool:
        query = db.query(CommissionConfig).order_by(CommissionConfig.id.asc()).populate_existing()
        if lock:
            query = query.with_for_update()
        config = query.first()
        return config is not None and config.commission_mode == CommissionMode.CITY_PARTNER

    @staticmethod
    def assert_mobile_enabled(db: Session) -> None:
        if not CityPartnerService.mobile_enabled(db, lock=True):
            raise ConflictError('城市合伙人暂未开放')

    @staticmethod
    def _money(value: Decimal | int | float | str) -> Decimal:
        return quantize_amount(value)

    @staticmethod
    def _rate(value) -> Decimal:
        rate = Decimal(str(value))
        if not rate.is_finite() or not 0 <= rate <= 100:
            raise ConflictError('Price growth rate must be between 0 and 100')
        return rate.quantize(Decimal('0.0001'))

    @staticmethod
    def serialize_seat(db: Session, seat: CityPartnerSeat, *, admin=False, viewer_id=None) -> dict:
        user = db.get(User, seat.current_user_id) if seat.current_user_id else None
        previous_order = db.get(Order, seat.current_order_id) if seat.current_order_id else None
        return {
            'id': seat.id,
            'purchasable': seat.status == CityPartnerSeatStatus.ACTIVE and (viewer_id is None or seat.current_user_id != viewer_id) and (not previous_order or seat.current_price > previous_order.paid_amount),
            'is_current_holder': viewer_id is not None and seat.current_user_id == viewer_id,
            'province': seat.province,
            'city': seat.city,
            'current_user_id': seat.current_user_id,
            'current_user_nickname': user.nickname if user else None,
            'current_price': float(seat.current_price),
            'initial_price': float(seat.initial_price),
            'price_growth_rate': float(seat.price_growth_rate),
            'price_cap': float(seat.price_cap) if seat.price_cap is not None else None,
            'price_version': seat.price_version,
            'rule_version': seat.rule_version,
            **({'current_order_id': seat.current_order_id,
                'current_order_no': previous_order.order_no if previous_order else None} if admin else {}),
            'rotation_count': seat.rotation_count,
            'status': seat.status.value if hasattr(seat.status, 'value') else seat.status,
            'term_started_at': iso_datetime(seat.term_started_at),
            'created_at': iso_datetime(seat.created_at),
            'updated_at': iso_datetime(seat.updated_at),
        }

    @staticmethod
    def create_seat(
        db: Session,
        province: str,
        city: str,
        initial_price: Decimal,
        price_growth_rate: Decimal,
        price_cap: Decimal | None = None,
        operator_id: int | None = None,
        change_reason: str | None = None,
    ) -> CityPartnerSeat:
        province, city = province.strip(), city.strip()
        if not province or not city:
            raise ConflictError('Province and city are required')
        if (
            db.query(CityPartnerSeat.id)
            .filter(CityPartnerSeat.province == province, CityPartnerSeat.city == city)
            .first()
        ):
            raise ConflictError('City partner seat already exists')
        price = CityPartnerService._money(initial_price)
        cap = CityPartnerService._money(price_cap) if price_cap is not None else None
        if price <= 0 or (cap is not None and cap < price):
            raise ConflictError('Invalid seat price or cap')
        seat = CityPartnerSeat(
            province=province,
            city=city,
            initial_price=price,
            current_price=price,
            price_growth_rate=CityPartnerService._rate(price_growth_rate),
            price_cap=cap,
            price_version=0,
            rotation_count=0,
            status=CityPartnerSeatStatus.ACTIVE,
        )
        db.add(seat)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError('City partner seat already exists') from exc
        record_rule_change(db, 'SEAT', seat.id, seat.rule_version, {}, rule_snapshot(seat), operator_id, change_reason or '创建席位')
        db.commit()
        db.refresh(seat)
        return seat

    @staticmethod
    def update_seat(
        db: Session, seat_id: int, price_growth_rate: Decimal, price_cap: Decimal | None, status: str,
        operator_id: int | None = None, change_reason: str | None = None,
    ) -> CityPartnerSeat:
        seat = db.query(CityPartnerSeat).filter(CityPartnerSeat.id == seat_id).populate_existing().with_for_update().first()
        if not seat:
            raise NotFoundError('City partner seat not found')
        before = rule_snapshot(seat)
        cap = CityPartnerService._money(price_cap) if price_cap is not None else None
        if cap is not None and cap < CityPartnerService._money(seat.current_price):
            raise ConflictError('price_cap cannot be below current price')
        seat.price_growth_rate = CityPartnerService._rate(price_growth_rate)
        seat.price_cap = cap
        seat.status = CityPartnerSeatStatus(status)
        if all(before[key] == rule_snapshot(seat)[key] for key in ('price_growth_rate', 'price_cap', 'status')):
            return seat
        # Keep a live quote stable. A stalled quote, however, cannot reach the
        # next successful sale that normally recalculates it. Reopen it when
        # the administrator changes pricing to permit positive appreciation.
        previous_order = db.get(Order, seat.current_order_id) if seat.current_order_id else None
        pricing_changed = any(before[key] != rule_snapshot(seat)[key] for key in ('price_growth_rate', 'price_cap'))
        if previous_order and pricing_changed and seat.current_price <= previous_order.paid_amount:
            next_price = CityPartnerService._money(
                previous_order.paid_amount * (Decimal('1') + seat.price_growth_rate / Decimal('100'))
            )
            seat.current_price = min(next_price, cap) if cap is not None else next_price
        seat.rule_version = f'city-seat-{uuid4().hex}'
        seat.price_version += 1
        seat.updated_at = now()
        db.flush()
        record_rule_change(db, 'SEAT', seat.id, seat.rule_version, before, rule_snapshot(seat), operator_id, change_reason or '更新席位规则')
        db.commit()
        db.refresh(seat)
        return seat

    @staticmethod
    def list_seats(db: Session, province: str | None = None, city: str | None = None):
        query = db.query(CityPartnerSeat)
        if province:
            query = query.filter(CityPartnerSeat.province == province.strip())
        if city:
            query = query.filter(CityPartnerSeat.city == city.strip())
        return query.order_by(CityPartnerSeat.province.asc(), CityPartnerSeat.city.asc()).all()

    @staticmethod
    def _credit_user(db: Session, user_id: int, amount: Decimal) -> None:
        amount = CityPartnerService._money(amount)
        if amount <= 0:
            return
        summary = db.query(UserCommission).filter(UserCommission.user_id == user_id).populate_existing().with_for_update().first()
        if not summary:
            summary = UserCommission(user_id=user_id, updated_at=now())
            db.add(summary)
            db.flush()
        summary.available_amount = CityPartnerService._money(summary.available_amount) + amount
        summary.total_amount = CityPartnerService._money(summary.total_amount) + amount
        summary.updated_at = now()

    @staticmethod
    def create_purchase_order(db: Session, seat_id: int, buyer: User, price_version: int) -> Order:
        CityPartnerService.assert_mobile_enabled(db)
        seat = db.query(CityPartnerSeat).filter(CityPartnerSeat.id == seat_id).populate_existing().with_for_update().first()
        if not seat:
            raise NotFoundError('City partner seat not found')
        if seat.status != CityPartnerSeatStatus.ACTIVE or seat.price_version != price_version:
            raise ConflictError('Seat quote changed; refresh the seat before buying')
        if seat.current_user_id == buyer.id:
            raise ConflictError('Current city partner cannot replace themselves')
        previous_order = db.get(Order, seat.current_order_id) if seat.current_order_id else None
        if previous_order and seat.current_price <= previous_order.paid_amount:
            raise ConflictError('Seat has reached its price cap; rotation is unavailable')
        system_account(db, 'COMPANY')
        system_account(db, 'OPERATIONS')
        pending = db.query(Order).join(CityPartnerPurchase, CityPartnerPurchase.order_id == Order.id).filter(
            CityPartnerPurchase.seat_id == seat.id, CityPartnerPurchase.price_version == seat.price_version,
            Order.user_id == buyer.id, Order.pay_status == PayStatus.UNPAID,
            Order.order_status == OrderStatus.PENDING_PAYMENT,
            Order.created_at >= now() - timedelta(minutes=UNPAID_ORDER_EXPIRE_MINUTES),
        ).first()
        if pending:
            return pending
        order = Order(order_no=f'CP{uuid4().hex}', user_id=buyer.id, team_id=buyer.team_id,
                      order_type=OrderType.CITY_PARTNER_ORDER, source_ref_id=seat.id,
                      total_amount=seat.current_price, payable_amount=seat.current_price,
                      commission_mode=CommissionMode.CITY_PARTNER, province=seat.province, city=seat.city,
                      commission_rule_version=seat.rule_version)
        db.add(order)
        db.flush()
        db.add(CityPartnerPurchase(order_id=order.id, seat_id=seat.id, price_version=seat.price_version,
                                   quoted_price=seat.current_price))
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def assert_refundable(db: Session, order: Order) -> None:
        # Include legacy rotations, even when they used an ordinary merchandise order.
        if db.query(CityPartnerRotationFlow.id).filter(
            CityPartnerRotationFlow.order_id == order.id,
            CityPartnerRotationFlow.status == CityPartnerRotationStatus.SUCCESS,
        ).with_for_update().first():
            raise ConflictError('Successful city partner seat purchases do not support ordinary refunds')

    @staticmethod
    def purchase_or_rotate(
        db: Session, seat_id: int, buyer: User, order_id: int, *, commit: bool = True
    ) -> tuple[CityPartnerSeat, CityPartnerRotationFlow]:
        # Match payment/refund lock ordering: order, seat, then sorted commission accounts.
        order = db.query(Order).filter(Order.id == order_id, Order.user_id == buyer.id).with_for_update().first()
        if not order:
            raise NotFoundError('Purchase order not found')
        purchase = db.query(CityPartnerPurchase).filter(CityPartnerPurchase.order_id == order.id).populate_existing().with_for_update().first()
        if order.order_type != OrderType.CITY_PARTNER_ORDER or not purchase or purchase.seat_id != seat_id:
            raise ConflictError('A dedicated purchase order for this seat is required')
        if order.pay_status != PayStatus.PAID or order.order_status == OrderStatus.REFUND:
            raise ConflictError('Purchase order is not paid')
        from app.services.order_service import OrderService
        OrderService._ensure_no_active_external_refund(db, order.id)
        seat = db.query(CityPartnerSeat).filter(CityPartnerSeat.id == seat_id).populate_existing().with_for_update().first()
        if not seat:
            raise NotFoundError('City partner seat not found')
        existing = db.query(CityPartnerRotationFlow).filter(CityPartnerRotationFlow.order_id == order.id).with_for_update().first()
        if existing:
            if existing.seat_id != seat.id:
                raise ConflictError('Purchase order already processed')
            return seat, existing
        if seat.current_user_id == buyer.id:
            raise ConflictError('Current city partner cannot replace themselves; contact support for the paid order')
        if seat.status != CityPartnerSeatStatus.ACTIVE or purchase.price_version != seat.price_version:
            raise ConflictError('Seat quote changed; contact support for the paid order')
        price = CityPartnerService._money(seat.current_price)
        if CityPartnerService._money(order.paid_amount) != price or purchase.quoted_price != price:
            raise ConflictError('Purchase order amount does not match the seat quote')
        previous_user_id = seat.current_user_id
        # current_price is the incoming buyer price; recover outgoing principal from prior order.
        previous_order = db.get(Order, seat.current_order_id) if seat.current_order_id else None
        previous_price = CityPartnerService._money(previous_order.paid_amount if previous_order else seat.initial_price)
        appreciation = CityPartnerService._money(price - previous_price) if previous_user_id else Decimal('0.00')
        # New price is already locked in current_price; the next price is calculated only after success.
        parent_id = buyer.parent_id
        if previous_user_id is None:
            parent_amount = CityPartnerService._money(price * Decimal('0.10')) if parent_id else Decimal('0.00')
            company_amount = price - parent_amount
            refund = reward = ops = Decimal('0.00')
        else:
            if price <= previous_price:
                raise ConflictError('Current seat price must be greater than previous purchase price')
            refund = previous_price
            reward = CityPartnerService._money(appreciation * Decimal('0.40'))
            company_amount = CityPartnerService._money(appreciation * Decimal('0.30'))
            parent_amount = CityPartnerService._money(appreciation * Decimal('0.10')) if parent_id else Decimal('0.00')
            ops = CityPartnerService._money(appreciation * Decimal('0.20'))
            if not parent_id:
                company_amount += CityPartnerService._money(appreciation * Decimal('0.10'))
        # Assign rounding differences to the company so the complete payment is conserved.
        company_amount = price - refund - reward - parent_amount - ops
        company_id = system_account(db, 'COMPANY').id
        operations_id = system_account(db, 'OPERATIONS').id
        allocations = {}
        for user_id, amount in [(previous_user_id, refund + reward), (parent_id, parent_amount),
                                (company_id, company_amount), (operations_id, ops)]:
            if user_id and amount > 0:
                allocations[user_id] = allocations.get(user_id, Decimal('0.00')) + amount
        for user_id in sorted(allocations):
            CityPartnerService._credit_user(db, user_id, allocations[user_id])
        flow = CityPartnerRotationFlow(
            seat_id=seat.id,
            order_id=order.id,
            order_no=order.order_no,
            province=seat.province,
            city=seat.city,
            previous_user_id=previous_user_id,
            new_user_id=buyer.id,
            new_user_parent_id=parent_id,
            previous_price=previous_price,
            new_price=price,
            appreciation_amount=appreciation,
            principal_refund_amount=refund,
            appreciation_reward_amount=reward,
            company_amount=company_amount,
            parent_reward_amount=parent_amount,
            operations_amount=ops,
            price_version_before=seat.price_version,
            price_version_after=seat.price_version + 1,
            commission_rule_version=seat.rule_version,
            status=CityPartnerRotationStatus.SUCCESS,
            confirmed_at=now(),
            created_at=now(),
        )
        db.add(flow)
        seat.current_user_id = buyer.id
        seat.current_order_id = order.id
        seat.rotation_count += 1
        seat.price_version += 1
        seat.term_started_at = now()
        next_price = CityPartnerService._money(
            price * (Decimal('1.00') + CityPartnerService._rate(seat.price_growth_rate) / Decimal('100'))
        )
        if seat.price_cap is not None:
            next_price = min(next_price, CityPartnerService._money(seat.price_cap))
        seat.current_price = next_price
        seat.updated_at = now()
        order.city_partner_user_id = buyer.id
        order.commission_rule_version = seat.rule_version
        purchase.settled_at = now()
        purchase.settlement_error = None
        order.order_status = OrderStatus.COMPLETED
        order.confirmed_at = now()
        db.flush()
        if commit:
            db.commit()
            db.refresh(seat)
            db.refresh(flow)
        return seat, flow

    @staticmethod
    def serialize_flow(flow: CityPartnerRotationFlow) -> dict:
        return {
            k: (
                float(v)
                if isinstance(v, Decimal)
                else (iso_datetime(v) if isinstance(v, datetime) else (v.value if hasattr(v, 'value') else v))
            )
            for k, v in {
                'id': flow.id,
                'seat_id': flow.seat_id,
                'order_id': flow.order_id,
                'order_no': flow.order_no,
                'province': flow.province,
                'city': flow.city,
                'previous_user_id': flow.previous_user_id,
                'new_user_id': flow.new_user_id,
                'new_user_parent_id': flow.new_user_parent_id,
                'previous_price': flow.previous_price,
                'new_price': flow.new_price,
                'appreciation_amount': flow.appreciation_amount,
                'principal_refund_amount': flow.principal_refund_amount,
                'appreciation_reward_amount': flow.appreciation_reward_amount,
                'company_amount': flow.company_amount,
                'parent_reward_amount': flow.parent_reward_amount,
                'operations_amount': flow.operations_amount,
                'price_version_before': flow.price_version_before,
                'price_version_after': flow.price_version_after,
                'commission_rule_version': flow.commission_rule_version,
                'status': flow.status,
                'confirmed_at': flow.confirmed_at,
                'created_at': flow.created_at,
            }.items()
        }
