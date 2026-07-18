from sqlalchemy import inspect, text

from app.db.session import engine


def _column_names(table_name: str) -> set[str]:
    return {item['name'] for item in inspect(engine).get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    return {item['name'] for item in inspect(engine).get_indexes(table_name)}


def apply_schema_migrations() -> None:
    """Apply the small, idempotent schema additions required by this service.

    The project currently uses ``metadata.create_all`` instead of Alembic. Existing
    tables therefore need explicit ALTER statements when columns are introduced.
    """

    with engine.begin() as connection:
        user_columns = _column_names('users')
        if 'admin_role_id' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN admin_role_id BIGINT NULL'))

        user_indexes = _index_names('users')
        if 'ix_users_admin_role_id' not in user_indexes:
            connection.execute(text('CREATE INDEX ix_users_admin_role_id ON users (admin_role_id)'))

        withdraw_columns = _column_names('withdraw_requests')
        if 'paid_by' not in withdraw_columns:
            connection.execute(text('ALTER TABLE withdraw_requests ADD COLUMN paid_by BIGINT NULL'))
        if 'paid_at' not in withdraw_columns:
            connection.execute(text('ALTER TABLE withdraw_requests ADD COLUMN paid_at DATETIME NULL'))

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
