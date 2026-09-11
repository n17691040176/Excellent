"""Run through stdin in the local Docker server; retains labeled test records."""
import json
from decimal import Decimal as D
from uuid import uuid4

import app.main  # Registers ORM models.
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.commission import CommissionConfig
from app.models.city_partner import CityPartnerCommissionFlow
from app.models.enums import CommissionMode, OrderStatus, OrderType, PaymentChannel, PayStatus, ProductType, ProductOwnerType, ZoneType
from app.models.order import Order, OrderItem
from app.models.payment import PaymentTransaction
from app.models.product import Product, ProductZoneConfig
from app.models.user import User
from app.services.city_partner_service import CityPartnerService as Seats
from app.services.commission_service import CommissionService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.utils.helpers import now

assert settings.mysql_db == 'excellent_local_test' and settings.payment_mock_external_payment is True
with SessionLocal() as db:
    assert db.query(CommissionConfig).first().commission_mode == CommissionMode.CITY_PARTNER
    buyer = db.query(User).filter_by(phone='19900134224').one()
    suffix = uuid4().hex[:12]
    product = Product(product_name=f'recovery-smoke-{suffix}', product_type=ProductType.PHYSICAL,
                      owner_type=ProductOwnerType.SELF_OPERATED, zone_type=ZoneType.SELF_OPERATED,
                      sale_price=D('2000'), cost_price=D('1000'), stock=99, requires_shipping=True)
    db.add(product)
    db.flush()
    db.add(ProductZoneConfig(product_id=product.id, zone_type=product.zone_type,
                             city_partner_commission_enabled=True, city_partner_amount=D('100'),
                             city_partner_direct_reward_amount=D('400'), city_partner_upline_initial_amount=D('200')))
    order = Order(order_no=f'RECOVERY-{suffix}', user_id=buyer.id,
                  order_type=OrderType.SELF_OPERATED_ORDER, total_amount=D('1600'), payable_amount=D('1600'))
    db.add(order)
    db.flush()
    db.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.product_name,
                     quantity=1, unit_price=D('1600'), total_amount=D('1600'), created_at=now()))
    tx = PaymentTransaction(order_id=order.id, order_no=order.order_no, channel=PaymentChannel.ALIPAY,
                            amount=D('1600'), out_trade_no=f'RECOVERY-PAY-{suffix}')
    db.add(tx)
    db.commit()
    PaymentService.confirm_paid_order(db, tx, {'mocked': True}, f'recovery-trade-{suffix}')
    assert order.pay_status == PayStatus.PAID and order.order_status == OrderStatus.PENDING_SHIP
    assert db.query(CityPartnerCommissionFlow).filter_by(order_id=order.id).count() == 0
    assert order.id in [item['order_id'] for item in CommissionService.list_failed_settlements(db)['items']]
    city = Seats.create_seat(db, '测试省', f'报价恢复-{suffix}', D('1000'), D('20'), D('1100'))
    other = User(nickname=f'recovery-holder-{suffix}', invite_code=uuid4().hex, password_hash='!')
    db.add(other)
    db.commit()
    for holder in (buyer, other):
        purchase = Seats.create_purchase_order(db, city.id, holder, city.price_version)
        OrderService._mark_paid(db, purchase)
    assert not Seats.serialize_seat(db, city)['purchasable']
    Seats.update_seat(db, city.id, D('20'), D('2000'), 'ACTIVE', change_reason='本地回归：封顶恢复')
    assert city.current_price == D('1320') and Seats.serialize_seat(db, city)['purchasable']
    print(json.dumps({'order_id': order.id, 'order_no': order.order_no, 'seat_id': city.id,
                      'reopened_price': str(city.current_price), 'failed_payment_recorded': True}))
