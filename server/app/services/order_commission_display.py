from sqlalchemy import case, or_

from app.models.enums import CommissionMode, OrderStatus, OrderType, PayStatus
from app.models.order import Order
from app.utils.helpers import iso_datetime


def order_commission_mode(order: Order) -> str:
    if order.order_type == OrderType.CITY_PARTNER_ORDER:
        return CommissionMode.CITY_PARTNER.value
    if order.mode_locked_at or order.paid_at or order.pay_status in (PayStatus.PAID, PayStatus.REFUNDED):
        return order.commission_mode.value
    return 'UNLOCKED'


def order_commission_mode_expression():
    # Match the display rules before pagination, including legacy paid orders.
    return case(
        (Order.order_type == OrderType.CITY_PARTNER_ORDER, 'CITY_PARTNER'),
        (or_(Order.mode_locked_at.is_not(None), Order.paid_at.is_not(None),
             Order.pay_status.in_([PayStatus.PAID, PayStatus.REFUNDED])), Order.commission_mode),
        else_='UNLOCKED',
    )


def order_commission_fields(order: Order) -> dict:
    mode = order_commission_mode(order)
    label = {'ORIGINAL': '原分润', 'CITY_PARTNER': '新分润', 'UNLOCKED': '待锁定'}[mode]
    if mode == 'UNLOCKED' and order.order_status == OrderStatus.REFUND:
        label = '未锁定'
    return {
        'commission_mode': mode,
        'commission_mode_text': label,
        'commission_rule_version': order.commission_rule_version if mode != 'UNLOCKED' else None,
        'mode_locked_at': iso_datetime(order.mode_locked_at),
    }
