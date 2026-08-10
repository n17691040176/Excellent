from sqlalchemy import Connection, inspect, text

from app.db.session import engine

EARNING_RULE_POOL_CLEANUP_KEY = '20260729_clear_earning_rule_pool'


def _column_names(table_name: str) -> set[str]:
    return {item['name'] for item in inspect(engine).get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    return {item['name'] for item in inspect(engine).get_indexes(table_name)}


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

    with engine.begin() as connection:
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
