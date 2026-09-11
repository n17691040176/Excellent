"""Read-only local ledger checks; pipe into the isolated Docker server's Python."""
import json
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

assert settings.mysql_db == 'excellent_local_test'
queries = {
    'mixed_product_order_count': '''SELECT COUNT(DISTINCT a.order_id)
        FROM commission_flows a JOIN city_partner_commission_flows b ON a.order_id=b.order_id''',
    'city_mode_with_old_flows': '''SELECT COUNT(DISTINCT o.id) FROM orders o
        JOIN commission_flows f ON f.order_id=o.id WHERE o.commission_mode='CITY_PARTNER' ''',
    'city_mode_with_region_flows': '''SELECT COUNT(DISTINCT o.id) FROM orders o
        JOIN region_dividend_flows f ON f.order_id=o.id WHERE o.commission_mode='CITY_PARTNER' ''',
    'original_mode_with_city_flows': '''SELECT COUNT(DISTINCT o.id) FROM orders o
        JOIN city_partner_commission_flows f ON f.order_id=o.id WHERE o.commission_mode='ORIGINAL' ''',
    'duplicate_city_seats': '''SELECT COUNT(*) FROM (SELECT province, city FROM city_partner_seats
        GROUP BY province, city HAVING COUNT(*)>1) duplicates''',
    'negative_commission_balances': '''SELECT COUNT(*) FROM user_commissions
        WHERE frozen_amount<0 OR available_amount<0 OR total_amount<0''',
    'historical_self_rotations': '''SELECT COUNT(*) FROM city_partner_rotation_flows
        WHERE previous_user_id=new_user_id''',
}
with engine.connect() as connection:
    connection.execute(text('SET TRANSACTION READ ONLY'))
    results = {key: connection.execute(text(sql)).scalar_one() for key, sql in queries.items()}
    expected = defaultdict(Decimal)
    for table in ('commission_flows', 'city_partner_commission_flows'):
        rows = connection.execute(text(f'''SELECT beneficiary_user_id, SUM(commission_amount)
            FROM {table} WHERE status='FROZEN' AND beneficiary_user_id IS NOT NULL
            GROUP BY beneficiary_user_id'''))
        for user_id, amount in rows:
            expected[user_id] += amount
    actual = dict(connection.execute(text('SELECT user_id, frozen_amount FROM user_commissions')).all())
    results['frozen_balance_mismatches'] = [
        {'user_id': uid, 'expected': str(expected[uid]), 'actual': str(actual.get(uid, Decimal(0)))}
        for uid in sorted(set(expected) | set(actual))
        if expected[uid] != actual.get(uid, Decimal(0))
    ]
    connection.rollback()
print(json.dumps(results, indent=2))
assert not any(value for key, value in results.items() if key != 'historical_self_rotations'), results
