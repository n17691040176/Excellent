"""Rehearse legacy-schema upgrades in a fresh database on local Docker only."""
import importlib
import json
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
url = make_url(os.environ['MIGRATION_LOCAL_ROOT_URL'])
assert url.host in {'localhost', '127.0.0.1'} and url.port == 13306 and url.database == 'mysql'
database = 'excellent_migration_' + uuid4().hex[:10] + '_test'
assert re.fullmatch(r'excellent_migration_[a-f0-9]+_test', database)
legacy = subprocess.check_output(['git', 'show', '79c012b:server/sql/schema.sql'], cwd=root).decode('utf-8-sig')
legacy = '\n'.join(line for line in legacy.splitlines() if not line.startswith(('CREATE DATABASE ', 'USE ')))
assert 'excellent_app' not in legacy
admin_engine = create_engine(url)
with admin_engine.begin() as connection:
    connection.execute(text(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci'))
engine = create_engine(url.set(database=database))
with engine.begin() as connection:
    for statement in legacy.split(';'):
        if statement.strip():
            connection.exec_driver_sql(statement)
    connection.exec_driver_sql("INSERT INTO users (id, password_hash, nickname, invite_code) VALUES (1, '!', 'migration-fixture', 'migration-fixture')")
    connection.exec_driver_sql("INSERT INTO user_asset_accounts (user_id, asset_type, total_amount, available_amount, frozen_amount, consumed_amount, withdrawn_amount, updated_at) VALUES (1, 'VOUCHER', 100, 100, 0, 0, 0, NOW()), (1, 'BALANCE', 200, 180, 0, 20, 0, NOW())")
    connection.exec_driver_sql("INSERT INTO user_commissions (user_id, total_amount, available_amount, frozen_amount, withdrawn_amount, updated_at) VALUES (1, 50, 30, 20, 0, NOW())")

def snapshot():
    with engine.connect() as connection:
        return {
            'assets': [list(row) for row in connection.execute(text('SELECT user_id, asset_type, total_amount, available_amount, frozen_amount, consumed_amount, withdrawn_amount FROM user_asset_accounts ORDER BY id'))],
            'commissions': [list(row) for row in connection.execute(text('SELECT user_id, total_amount, available_amount, frozen_amount, withdrawn_amount FROM user_commissions ORDER BY id'))],
        }

before = snapshot()
init = importlib.import_module('app.db.init_db')
migrations = importlib.import_module('app.db.migrations')
init.engine = engine
migrations.engine = engine
for _ in range(2):
    init.init_db()
    migrations.apply_schema_migrations()
    assert snapshot() == before
tables = inspect(engine).get_table_names()
assert {'city_partner_seats', 'city_partner_commission_flows', 'city_partner_purchases'} <= set(tables)
assert {'commission_mode', 'mode_locked_at', 'commission_rule_version'} <= {column['name'] for column in inspect(engine).get_columns('orders')}
result = {'database': database, 'legacy_commit': '79c012b', 'migration_runs': 2,
          'sample_balances_preserved': True, 'new_schema_present': True, 'table_count': len(tables)}
(root / 'logs/local-test/migration-rehearsal.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
engine.dispose()
admin_engine.dispose()
