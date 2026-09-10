from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.city_partner import CityPartnerRotationFlow, CityPartnerSeat
from app.models.commission import UserCommission
from app.models.enums import CityPartnerRotationStatus, CityPartnerSeatStatus, PayStatus
from app.models.order import Order
from app.models.user import User
from app.utils.helpers import iso_datetime, now, quantize_amount


class CityPartnerService:
    """城市合伙人席位管理、竞价轮换及独立资金结算。"""

    @staticmethod
    def _money(value: Decimal | int | float | str) -> Decimal:
        return quantize_amount(value)

    @staticmethod
    def serialize_seat(db: Session, seat: CityPartnerSeat) -> dict:
        user = db.get(User, seat.current_user_id) if seat.current_user_id else None
        return {
            'id': seat.id,
            'province': seat.province,
            'city': seat.city,
            'current_user_id': seat.current_user_id,
            'current_user_nickname': user.nickname if user else None,
            'current_price': float(seat.current_price),
            'initial_price': float(seat.initial_price),
            'price_growth_rate': float(seat.price_growth_rate),
            'price_cap': float(seat.price_cap) if seat.price_cap is not None else None,
            'price_version': seat.price_version,
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
            price_growth_rate=CityPartnerService._money(price_growth_rate),
            price_cap=cap,
            price_version=0,
            rotation_count=0,
            status=CityPartnerSeatStatus.ACTIVE,
        )
        db.add(seat)
        db.commit()
        db.refresh(seat)
        return seat

    @staticmethod
    def update_seat(
        db: Session, seat_id: int, price_growth_rate: Decimal, price_cap: Decimal | None, status: str
    ) -> CityPartnerSeat:
        seat = db.query(CityPartnerSeat).filter(CityPartnerSeat.id == seat_id).with_for_update().first()
        if not seat:
            raise NotFoundError('City partner seat not found')
        cap = CityPartnerService._money(price_cap) if price_cap is not None else None
        if cap is not None and cap < CityPartnerService._money(seat.current_price):
            raise ConflictError('price_cap cannot be below current price')
        seat.price_growth_rate = CityPartnerService._money(price_growth_rate)
        seat.price_cap = cap
        seat.status = CityPartnerSeatStatus(status)
        seat.updated_at = now()
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
        summary = db.query(UserCommission).filter(UserCommission.user_id == user_id).with_for_update().first()
        if not summary:
            summary = UserCommission(user_id=user_id, updated_at=now())
            db.add(summary)
            db.flush()
        summary.available_amount = CityPartnerService._money(summary.available_amount) + amount
        summary.total_amount = CityPartnerService._money(summary.total_amount) + amount
        summary.updated_at = now()

    @staticmethod
    def _credit_system_account(db: Session, account_type: str, amount: Decimal) -> None:
        """Credit a designated internal user when one has been configured."""
        amount = CityPartnerService._money(amount)
        if amount <= 0:
            return
        account = db.query(User).filter(User.system_account_type == account_type).with_for_update().first()
        if account:
            CityPartnerService._credit_user(db, account.id, amount)

    @staticmethod
    def purchase_or_rotate(
        db: Session, seat_id: int, buyer: User, order_id: int
    ) -> tuple[CityPartnerSeat, CityPartnerRotationFlow]:
        # Row lock is the serialization point for same-city purchases. The order must be paid and owned by buyer.
        seat = db.query(CityPartnerSeat).filter(CityPartnerSeat.id == seat_id).with_for_update().first()
        if not seat:
            raise NotFoundError('City partner seat not found')
        if seat.status != CityPartnerSeatStatus.ACTIVE:
            raise ConflictError('City partner seat is inactive')
        order = db.query(Order).filter(Order.id == order_id, Order.user_id == buyer.id).with_for_update().first()
        if not order:
            raise NotFoundError('Purchase order not found')
        if order.pay_status != PayStatus.PAID:
            raise ConflictError('Purchase order is not paid')
        price = CityPartnerService._money(seat.current_price)
        if CityPartnerService._money(order.paid_amount or order.payable_amount) != price:
            raise ConflictError('Purchase order amount does not match current seat price')
        if (
            db.query(CityPartnerRotationFlow.id)
            .filter(CityPartnerRotationFlow.seat_id == seat.id, CityPartnerRotationFlow.order_id == order.id)
            .first()
        ):
            raise ConflictError('Purchase order already processed')
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
        if previous_user_id:
            CityPartnerService._credit_user(db, previous_user_id, refund + reward)
        if parent_id:
            CityPartnerService._credit_user(db, parent_id, parent_amount)
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
            commission_rule_version='city-partner-v1',
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
            price * (Decimal('1.00') + CityPartnerService._money(seat.price_growth_rate) / Decimal('100'))
        )
        if seat.price_cap is not None:
            next_price = min(next_price, CityPartnerService._money(seat.price_cap))
        seat.current_price = next_price
        seat.updated_at = now()
        order.city_partner_user_id = buyer.id
        db.flush()
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
                'status': flow.status,
                'confirmed_at': flow.confirmed_at,
                'created_at': flow.created_at,
            }.items()
        }
