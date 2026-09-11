"""Create labelled orders and a beneficiary only in the explicit local test DB.

Run from server with PYTHONPATH=server;server/tests and CITY_PARTNER_MYSQL_TEST_URL.
"""
import json
import os
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from test_city_partner import product_order
from app.core.security import hash_password
from app.models.commission import CommissionConfig, UserCommission
from app.models.enums import CommissionMode, MemberLevel
from app.models.user import User
from app.services.order_service import OrderService
from app.utils.helpers import now

url = make_url(os.environ['CITY_PARTNER_MYSQL_TEST_URL'])
assert url.host in {'127.0.0.1', 'localhost'} and url.database == 'excellent_local_test'
engine = create_engine(url)
with Session(engine, autoflush=False, expire_on_commit=False) as db:
    config = db.query(CommissionConfig).first()
    original_mode = config.commission_mode
    original_version = config.commission_rule_version
    suffix = uuid4().hex[:10]
    parent = User(phone='199' + str(time.time_ns())[-8:], nickname='order-mode-beneficiary-' + suffix,
                  invite_code=uuid4().hex, member_level=MemberLevel.DEALER, password_hash=hash_password('LocalTest123'))
    db.add(parent)
    db.flush()
    buyer = User(nickname='order-mode-buyer-' + suffix, invite_code=uuid4().hex, parent_id=parent.id, password_hash='!')
    db.add(buyer)
    db.add(UserCommission(user_id=parent.id, updated_at=now()))
    db.commit()
    ids = {}
    try:
        for mode in [CommissionMode.ORIGINAL, CommissionMode.CITY_PARTNER]:
            config.commission_mode = mode
            config.commission_rule_version = f'{mode.value.lower()}-browser-{suffix}'
            db.commit()
            product, rule, order = product_order(db, buyer)
            product.product_name = 'order-mode-browser-' + suffix
            order.order_no = f'ORDERMODE-{mode.value}-{suffix}'
            rule.custom_commission_enabled = True
            rule.custom_commission_method = 'FIXED_AMOUNT'
            rule.custom_commission_level2_enabled = True
            rule.custom_commission_level2_amount = 8
            db.commit()
            OrderService._mark_paid(db, order, external_paid_amount=order.total_amount)
            ids[mode.value] = order.id
        _, _, pending = product_order(db, buyer)
        pending.order_no = 'ORDERMODE-UNLOCKED-' + suffix
        db.commit()
        ids['UNLOCKED'] = pending.id
    finally:
        db.rollback()
        config = db.query(CommissionConfig).first()
        config.commission_mode = original_mode
        config.commission_rule_version = original_version
        db.commit()
    result = {'phone': parent.phone, 'order_ids': ids, 'keyword': suffix}
    target = Path('../logs/local-test/order-mode-fixture.json')
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
engine.dispose()
