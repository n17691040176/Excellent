from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, inspect, text

from app.db.session import engine

EARNING_RULE_POOL_CLEANUP_KEY = '20260729_clear_earning_rule_pool'
SCHEMA_MIGRATION_LOCK_KEY = 'excellent_schema_migrations'

PAYMENT_REFUND_REQUIRED_COLUMNS = {
    'id',
    'order_id',
    'payment_transaction_id',
    'order_no',
    'channel',
    'original_amount',
    'refund_amount',
    'out_refund_no',
}

PAYMENT_REFUND_ADDITIVE_COLUMNS = {
    'status': "VARCHAR(32) NOT NULL DEFAULT 'PENDING'",
    'currency': "VARCHAR(8) NOT NULL DEFAULT 'CNY'",
    'idempotency_key': 'VARCHAR(128) NULL',
    'provider_refund_id': 'VARCHAR(128) NULL',
    'provider_trade_no': 'VARCHAR(128) NULL',
    'provider_status': 'VARCHAR(32) NULL',
    'reason': 'VARCHAR(80) NULL',
    'request_payload': 'JSON NULL',
    'response_payload': 'JSON NULL',
    'notify_payload': 'JSON NULL',
    'provider_notify_id': 'VARCHAR(128) NULL',
    'error_code': 'VARCHAR(64) NULL',
    'error_message': 'VARCHAR(255) NULL',
    'requested_by': 'BIGINT NULL',
    'requested_at': 'DATETIME NULL',
    'processed_at': 'DATETIME NULL',
    'success_at': 'DATETIME NULL',
    'last_synced_at': 'DATETIME NULL',
    'next_retry_at': 'DATETIME NULL',
    'attempt_count': 'INT NOT NULL DEFAULT 0',
    'created_at': 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
    'updated_at': (
        'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'
    ),
}

PAYMENT_REFUND_INDEXES = {
    'uk_payment_refunds_payment_transaction': (
        'CREATE UNIQUE INDEX uk_payment_refunds_payment_transaction '
        'ON payment_refunds (payment_transaction_id)'
    ),
    'uk_payment_refunds_out_refund_no': (
        'CREATE UNIQUE INDEX uk_payment_refunds_out_refund_no '
        'ON payment_refunds (out_refund_no)'
    ),
    'uk_payment_refunds_provider_refund_id': (
        'CREATE UNIQUE INDEX uk_payment_refunds_provider_refund_id '
        'ON payment_refunds (provider_refund_id)'
    ),
    'uk_payment_refunds_provider_notify_id': (
        'CREATE UNIQUE INDEX uk_payment_refunds_provider_notify_id '
        'ON payment_refunds (provider_notify_id)'
    ),
    'uk_payment_refunds_transaction_idempotency': (
        'CREATE UNIQUE INDEX uk_payment_refunds_transaction_idempotency '
        'ON payment_refunds (payment_transaction_id, idempotency_key)'
    ),
    'ix_payment_refunds_order_id': 'CREATE INDEX ix_payment_refunds_order_id ON payment_refunds (order_id)',
    'ix_payment_refunds_payment_transaction_id': (
        'CREATE INDEX ix_payment_refunds_payment_transaction_id '
        'ON payment_refunds (payment_transaction_id)'
    ),
    'ix_payment_refunds_order_no': 'CREATE INDEX ix_payment_refunds_order_no ON payment_refunds (order_no)',
    'ix_payment_refunds_channel': 'CREATE INDEX ix_payment_refunds_channel ON payment_refunds (channel)',
    'ix_payment_refunds_status': 'CREATE INDEX ix_payment_refunds_status ON payment_refunds (status)',
}

PAYMENT_REFUND_FOREIGN_KEYS = {
    ('order_id', 'orders', 'id'): (
        'ALTER TABLE payment_refunds '
        'ADD CONSTRAINT fk_payment_refunds_order_id '
        'FOREIGN KEY (order_id) REFERENCES orders (id)'
    ),
    ('payment_transaction_id', 'payment_transactions', 'id'): (
        'ALTER TABLE payment_refunds '
        'ADD CONSTRAINT fk_payment_refunds_payment_transaction_id '
        'FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions (id)'
    ),
}

PAYMENT_REFUNDS_CREATE_SQL = (
    'CREATE TABLE IF NOT EXISTS payment_refunds ('
    'id BIGINT PRIMARY KEY AUTO_INCREMENT, '
    'order_id BIGINT NOT NULL, '
    'payment_transaction_id BIGINT NOT NULL, '
    'order_no VARCHAR(64) NOT NULL, '
    'channel VARCHAR(32) NOT NULL, '
    'status VARCHAR(32) NOT NULL DEFAULT \'PENDING\', '
    'currency VARCHAR(8) NOT NULL DEFAULT \'CNY\', '
    'original_amount DECIMAL(18,2) NOT NULL, '
    'refund_amount DECIMAL(18,2) NOT NULL, '
    'out_refund_no VARCHAR(64) NOT NULL, '
    'idempotency_key VARCHAR(128) NULL, '
    'provider_refund_id VARCHAR(128) NULL, '
    'provider_trade_no VARCHAR(128) NULL, '
    'provider_status VARCHAR(32) NULL, '
    'reason VARCHAR(80) NULL, '
    'request_payload JSON NULL, '
    'response_payload JSON NULL, '
    'notify_payload JSON NULL, '
    'provider_notify_id VARCHAR(128) NULL, '
    'error_code VARCHAR(64) NULL, '
    'error_message VARCHAR(255) NULL, '
    'requested_by BIGINT NULL, '
    'requested_at DATETIME NULL, '
    'processed_at DATETIME NULL, '
    'success_at DATETIME NULL, '
    'last_synced_at DATETIME NULL, '
    'next_retry_at DATETIME NULL, '
    'attempt_count INT NOT NULL DEFAULT 0, '
    'created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, '
    'updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, '
    'UNIQUE KEY uk_payment_refunds_payment_transaction (payment_transaction_id), '
    'UNIQUE KEY uk_payment_refunds_out_refund_no (out_refund_no), '
    'UNIQUE KEY uk_payment_refunds_provider_refund_id (provider_refund_id), '
    'UNIQUE KEY uk_payment_refunds_provider_notify_id (provider_notify_id), '
    'UNIQUE KEY uk_payment_refunds_transaction_idempotency '
    '(payment_transaction_id, idempotency_key), '
    'KEY ix_payment_refunds_order_id (order_id), '
    'KEY ix_payment_refunds_payment_transaction_id (payment_transaction_id), '
    'KEY ix_payment_refunds_order_no (order_no), '
    'KEY ix_payment_refunds_channel (channel), '
    'KEY ix_payment_refunds_status (status), '
    'CONSTRAINT fk_payment_refunds_order_id FOREIGN KEY (order_id) REFERENCES orders (id), '
    'CONSTRAINT fk_payment_refunds_payment_transaction_id '
    'FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions (id)'
    ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
)


@contextmanager
def _schema_migration_lock(connection: Connection) -> Iterator[None]:
    """Serialize inspect-then-ALTER migrations across MySQL app replicas."""

    if connection.dialect.name != 'mysql':
        yield
        return

    acquired = connection.execute(
        text('SELECT GET_LOCK(:lock_key, 30)'),
        {'lock_key': SCHEMA_MIGRATION_LOCK_KEY},
    ).scalar()
    if acquired != 1:
        raise RuntimeError('Could not acquire the database schema migration lock')
    try:
        yield
    finally:
        connection.execute(
            text('SELECT RELEASE_LOCK(:lock_key)'),
            {'lock_key': SCHEMA_MIGRATION_LOCK_KEY},
        )


def _column_names(table_name: str) -> set[str]:
    return {item['name'] for item in inspect(engine).get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    return {item['name'] for item in inspect(engine).get_indexes(table_name)}


def _foreign_key_signatures(table_name: str) -> set[tuple[str, str, str]]:
    signatures: set[tuple[str, str, str]] = set()
    for item in inspect(engine).get_foreign_keys(table_name):
        constrained_columns = item.get('constrained_columns') or []
        referred_columns = item.get('referred_columns') or []
        referred_table = str(item.get('referred_table') or '')
        if len(constrained_columns) == 1 and len(referred_columns) == 1 and referred_table:
            signatures.add(
                (str(constrained_columns[0]), referred_table, str(referred_columns[0]))
            )
    return signatures


def _ensure_payment_refund_schema(connection: Connection) -> None:
    """Create or upgrade the durable refund ledger without losing old rows."""

    # ``init_db`` normally creates this table first, but the migration must
    # also be safe when multiple replicas start against an older database.
    connection.execute(text(PAYMENT_REFUNDS_CREATE_SQL))

    columns = _column_names('payment_refunds')
    missing_required = PAYMENT_REFUND_REQUIRED_COLUMNS - columns
    if missing_required:
        names = ', '.join(sorted(missing_required))
        raise RuntimeError(
            'Existing payment_refunds table is missing required columns that '
            f'cannot be reconstructed safely: {names}'
        )

    for column_name, column_type in PAYMENT_REFUND_ADDITIVE_COLUMNS.items():
        if column_name not in columns:
            connection.execute(
                text(f'ALTER TABLE payment_refunds ADD COLUMN {column_name} {column_type}')
            )

    index_names = _index_names('payment_refunds')
    for index_name, statement in PAYMENT_REFUND_INDEXES.items():
        if index_name not in index_names:
            connection.execute(text(statement))

    foreign_keys = _foreign_key_signatures('payment_refunds')
    for signature, statement in PAYMENT_REFUND_FOREIGN_KEYS.items():
        if signature not in foreign_keys:
            connection.execute(text(statement))


def _clear_legacy_earning_rule_pool(connection: Connection) -> None:
    """Delete the old shared rule pool once without touching product rules."""

    connection.execute(
        text(
            'CREATE TABLE IF NOT EXISTS app_data_migrations ('
            'migration_key VARCHAR(128) PRIMARY KEY, '
            'applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP'
            ')'
        )
    )
    already_applied = connection.execute(
        text('SELECT migration_key FROM app_data_migrations WHERE migration_key = :migration_key'),
        {'migration_key': EARNING_RULE_POOL_CLEANUP_KEY},
    ).first()
    if already_applied:
        return

    connection.execute(text('DELETE FROM earning_rules'))
    connection.execute(
        text('UPDATE commission_configs SET level1_rate = 0, level2_rate = 0, is_active = 0')
    )
    connection.execute(
        text(
            'INSERT INTO app_data_migrations (migration_key, applied_at) '
            'VALUES (:migration_key, CURRENT_TIMESTAMP)'
        ),
        {'migration_key': EARNING_RULE_POOL_CLEANUP_KEY},
    )


def apply_schema_migrations() -> None:
    """Apply the small, idempotent schema additions required by this service.

    The project currently uses ``metadata.create_all`` instead of Alembic. Existing
    tables therefore need explicit ALTER statements when columns are introduced.
    """

    with engine.begin() as connection, _schema_migration_lock(connection):
        user_columns = _column_names('users')
        if 'member_level' not in user_columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN member_level VARCHAR(32) NOT NULL DEFAULT 'NORMAL_MEMBER'")
            )
            if 'business_identity' in user_columns:
                connection.execute(
                    text(
                        "UPDATE users SET member_level = CASE business_identity "
                        "WHEN 'DEALER' THEN 'DEALER' "
                        "WHEN 'COUNTY_AGENT' THEN 'COUNTY_AGENT' "
                        "WHEN 'CITY_AGENT' THEN 'CITY_AGENT' "
                        "ELSE 'NORMAL_MEMBER' END"
                    )
                )
        if 'business_identity' in user_columns:
            connection.execute(text('ALTER TABLE users DROP COLUMN business_identity'))
        if 'admin_role_id' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN admin_role_id BIGINT NULL'))

        user_indexes = _index_names('users')
        if 'ix_users_member_level' not in user_indexes:
            connection.execute(text('CREATE INDEX ix_users_member_level ON users (member_level)'))
        if 'ix_users_admin_role_id' not in user_indexes:
            connection.execute(text('CREATE INDEX ix_users_admin_role_id ON users (admin_role_id)'))

        dividend_indexes = _index_names('region_dividend_flows')
        if 'uq_region_dividend_order_agent' not in dividend_indexes:
            duplicate_group = connection.execute(
                text(
                    'SELECT order_id, agent_id FROM region_dividend_flows '
                    'GROUP BY order_id, agent_id HAVING COUNT(*) > 1 LIMIT 1'
                )
            ).first()
            if not duplicate_group:
                connection.execute(
                    text(
                        'CREATE UNIQUE INDEX uq_region_dividend_order_agent '
                        'ON region_dividend_flows (order_id, agent_id)'
                    )
                )

        withdraw_columns = _column_names('withdraw_requests')
        withdraw_column_definitions = {
            'paid_by': 'BIGINT NULL',
            'paid_at': 'DATETIME NULL',
            'fee_rate': 'DECIMAL(5,2) NOT NULL DEFAULT 0',
            'fee_amount': 'DECIMAL(18,2) NOT NULL DEFAULT 0',
            'net_amount': 'DECIMAL(18,2) NOT NULL DEFAULT 0',
            'bank_card_id': 'BIGINT NULL',
            'bank_holder_name': 'VARCHAR(64) NULL',
            'bank_name': 'VARCHAR(128) NULL',
            'bank_branch_name': 'VARCHAR(255) NULL',
            'bank_card_number_encrypted': 'TEXT NULL',
            'bank_card_last_four': 'VARCHAR(4) NULL',
            'review_remark': 'VARCHAR(500) NULL',
        }
        for column_name, column_type in withdraw_column_definitions.items():
            if column_name not in withdraw_columns:
                connection.execute(text(f'ALTER TABLE withdraw_requests ADD COLUMN {column_name} {column_type}'))
        connection.execute(text('UPDATE withdraw_requests SET net_amount = amount WHERE net_amount = 0'))

        commission_config_columns = _column_names('commission_configs')
        commission_config_definitions = {
            'withdraw_fee_rate': 'DECIMAL(5,2) NOT NULL DEFAULT 0',
            'withdraw_min_amount': 'DECIMAL(18,2) NOT NULL DEFAULT 1',
            'withdraw_max_amount': 'DECIMAL(18,2) NOT NULL DEFAULT 50000',
        }
        for column_name, column_type in commission_config_definitions.items():
            if column_name not in commission_config_columns:
                connection.execute(text(f'ALTER TABLE commission_configs ADD COLUMN {column_name} {column_type}'))

        zone_config_columns = _column_names('product_zone_configs')
        payment_columns_added = False
        if 'alipay_purchase_enabled' not in zone_config_columns:
            connection.execute(
                text(
                    'ALTER TABLE product_zone_configs '
                    'ADD COLUMN alipay_purchase_enabled TINYINT(1) NOT NULL DEFAULT 1 '
                    'AFTER balance_purchase_enabled'
                )
            )
            payment_columns_added = True
        if 'wechat_purchase_enabled' not in zone_config_columns:
            connection.execute(
                text(
                    'ALTER TABLE product_zone_configs '
                    'ADD COLUMN wechat_purchase_enabled TINYINT(1) NOT NULL DEFAULT 0 '
                    'AFTER alipay_purchase_enabled'
                )
            )
            payment_columns_added = True
        if payment_columns_added:
            connection.execute(
                text(
                    'UPDATE product_zone_configs '
                    'SET balance_purchase_enabled = 1, balance_only_enabled = 1, cash_only_enabled = 1'
                )
            )

        payment_transaction_columns = _column_names('payment_transactions')
        if 'refunded_amount' not in payment_transaction_columns:
            connection.execute(
                text(
                    'ALTER TABLE payment_transactions '
                    'ADD COLUMN refunded_amount DECIMAL(18,2) NOT NULL DEFAULT 0 '
                    'AFTER failed_reason'
                )
            )

        _ensure_payment_refund_schema(connection)

        commission_columns = {
            'custom_commission_enabled': "TINYINT(1) NOT NULL DEFAULT 0",
            'custom_commission_method': "VARCHAR(32) NOT NULL DEFAULT 'RATE'",
            'custom_commission_level1_enabled': 'TINYINT(1) NOT NULL DEFAULT 0',
            'custom_commission_level2_enabled': 'TINYINT(1) NOT NULL DEFAULT 0',
            'custom_commission_county_agent_enabled': 'TINYINT(1) NOT NULL DEFAULT 0',
            'custom_commission_city_agent_enabled': 'TINYINT(1) NOT NULL DEFAULT 0',
            'custom_commission_level1_rate': 'DECIMAL(5,2) NOT NULL DEFAULT 0',
            'custom_commission_level2_rate': 'DECIMAL(5,2) NOT NULL DEFAULT 0',
            'custom_commission_county_agent_rate': 'DECIMAL(5,2) NOT NULL DEFAULT 0',
            'custom_commission_city_agent_rate': 'DECIMAL(5,2) NOT NULL DEFAULT 0',
            'custom_commission_level1_amount': 'DECIMAL(18,2) NOT NULL DEFAULT 0',
            'custom_commission_level2_amount': 'DECIMAL(18,2) NOT NULL DEFAULT 0',
            'custom_commission_county_agent_amount': 'DECIMAL(18,2) NOT NULL DEFAULT 0',
            'custom_commission_city_agent_amount': 'DECIMAL(18,2) NOT NULL DEFAULT 0',
        }
        added_commission_columns: set[str] = set()
        for column_name, column_type in commission_columns.items():
            if column_name not in zone_config_columns:
                connection.execute(
                    text(f'ALTER TABLE product_zone_configs ADD COLUMN {column_name} {column_type}')
                )
                added_commission_columns.add(column_name)

        if 'custom_commission_level1_enabled' in added_commission_columns:
            connection.execute(text(
                'UPDATE product_zone_configs SET custom_commission_level1_enabled = 1 '
                'WHERE custom_commission_level1_rate > 0 OR custom_commission_level1_amount > 0'
            ))
        if 'custom_commission_level2_enabled' in added_commission_columns:
            connection.execute(text(
                'UPDATE product_zone_configs SET custom_commission_level2_enabled = 1 '
                'WHERE custom_commission_level2_rate > 0 OR custom_commission_level2_amount > 0'
            ))

        _clear_legacy_earning_rule_pool(connection)
