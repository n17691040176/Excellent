"""Compare old-mode ledgers against preserved Git calculators on isolated ORM data.

This compares the commission and region dividend implementations, not the entire
historical application/runtime. Run from server with server/tests on PYTHONPATH.
"""
from contextlib import contextmanager
from pathlib import Path
import subprocess

import pytest

from test_city_partner import db as db_fixture
from test_commission_mode_isolation import make_scenario, ledger_state
from app.models.commission import CommissionConfig
from app.models.enums import CommissionMode, OrderStatus, PayStatus
from app.services.commission_service import CommissionService
from app.services.region_dividend_service import RegionDividendService

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '79c012b'


@pytest.fixture(scope='module')
def baseline_services():
    services = []
    for filename, name in [('commission_service.py', 'CommissionService'), ('region_dividend_service.py', 'RegionDividendService')]:
        source = subprocess.check_output(['git', 'show', f'{BASELINE}:server/app/services/{filename}'],
                                         cwd=ROOT, text=True, encoding='utf-8')
        namespace = {'__name__': f'baseline_{filename[:-3]}'}
        exec(compile(source, f'{BASELINE}/{filename}', 'exec'), namespace)
        services.append(namespace[name])
    return services


def run_lifecycle(commission, region, method, quantity, repurchase, depth):
    with contextmanager(db_fixture.__wrapped__)() as db:
        buyer, _, _, order, _ = make_scenario(db, method, quantity=quantity, repurchase=repurchase, depth=depth)
        order.commission_mode = CommissionMode.ORIGINAL
        order.pay_status = PayStatus.PAID
        order.order_status = OrderStatus.PENDING_SHIP
        db.commit()
        commission.freeze_for_order(db, order, buyer)
        db.commit()
        frozen = ledger_state(db)
        # A global switch must not affect existing ORIGINAL flows.
        db.query(CommissionConfig).first().commission_mode = CommissionMode.CITY_PARTNER
        order.order_status = OrderStatus.COMPLETED
        db.commit()
        commission.settle_for_order(db, order.id)
        region.process_order_dividend(db, order, {'province': '陕西省', 'city': '西安市', 'district': '雁塔区'})
        settled = ledger_state(db)
        commission.cancel_for_order(db, order.id)
        region.reverse_order_dividend(db, order)
        db.commit()
        return {'frozen': frozen, 'settled': settled, 'reversed': ledger_state(db)}


@pytest.mark.parametrize('method', ['FIXED_AMOUNT', 'RATE', 'GENERIC'])
@pytest.mark.parametrize('quantity', [1, 2])
@pytest.mark.parametrize('repurchase', [False, True])
@pytest.mark.parametrize('depth', [0, 8])
def test_original_ledgers_match_preserved_baseline(baseline_services, method, quantity, repurchase, depth):
    baseline = run_lifecycle(*baseline_services, method, quantity, repurchase, depth)
    current = run_lifecycle(CommissionService, RegionDividendService, method, quantity, repurchase, depth)
    # Preserve the original allocation rules exactly. The original generic
    # path overwrote a parent's unflushed direct balance with its team reward;
    # retaining that historical aggregate bug is not a compatibility goal.
    for phase in current:
        for key in ('old_flows', 'region_flows', 'assets'):
            assert current[phase][key] == baseline[phase][key]
        expected = {}
        for _, uid, _, amount, status in current[phase]['old_flows']:
            balances = expected.setdefault(uid, [0, 0, 0])
            if status.value == 'FROZEN':
                balances[0] += amount
                balances[2] += amount
            if status.value == 'SETTLED':
                balances[1] += amount
                balances[2] += amount
        for uid, frozen, available, total in current[phase]['commissions']:
            assert [frozen, available, total] == expected.get(uid, [0, 0, 0])
    if method != 'GENERIC' or not depth:
        assert current == baseline
