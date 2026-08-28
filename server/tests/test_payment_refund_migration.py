from unittest.mock import MagicMock, patch

import pytest

from app.db import migrations


def _executed_sql(connection: MagicMock) -> list[str]:
    return [str(call.args[0]) for call in connection.execute.call_args_list]


def test_refund_schema_upgrade_adds_missing_optional_columns_and_indexes():
    connection = MagicMock()

    with (
        patch.object(
            migrations,
            '_column_names',
            return_value=set(migrations.PAYMENT_REFUND_REQUIRED_COLUMNS),
        ),
        patch.object(migrations, '_index_names', return_value=set()),
        patch.object(migrations, '_foreign_key_signatures', return_value=set()),
    ):
        migrations._ensure_payment_refund_schema(connection)

    statements = _executed_sql(connection)
    assert statements[0].startswith('CREATE TABLE IF NOT EXISTS payment_refunds')
    for column_name in migrations.PAYMENT_REFUND_ADDITIVE_COLUMNS:
        assert any(
            statement.startswith(f'ALTER TABLE payment_refunds ADD COLUMN {column_name} ')
            for statement in statements
        )
    for index_name in migrations.PAYMENT_REFUND_INDEXES:
        assert any(index_name in statement for statement in statements)
    for statement in migrations.PAYMENT_REFUND_FOREIGN_KEYS.values():
        assert statement in statements


def test_refund_schema_enforces_one_full_refund_per_payment_transaction():
    assert (
        'UNIQUE KEY uk_payment_refunds_payment_transaction (payment_transaction_id)'
        in migrations.PAYMENT_REFUNDS_CREATE_SQL
    )
    assert (
        migrations.PAYMENT_REFUND_INDEXES['uk_payment_refunds_payment_transaction']
        == 'CREATE UNIQUE INDEX uk_payment_refunds_payment_transaction '
        'ON payment_refunds (payment_transaction_id)'
    )


def test_refund_schema_upgrade_is_noop_after_idempotent_create_when_complete():
    connection = MagicMock()
    all_columns = (
        set(migrations.PAYMENT_REFUND_REQUIRED_COLUMNS)
        | set(migrations.PAYMENT_REFUND_ADDITIVE_COLUMNS)
    )

    with (
        patch.object(migrations, '_column_names', return_value=all_columns),
        patch.object(
            migrations,
            '_index_names',
            return_value=set(migrations.PAYMENT_REFUND_INDEXES),
        ),
        patch.object(
            migrations,
            '_foreign_key_signatures',
            return_value=set(migrations.PAYMENT_REFUND_FOREIGN_KEYS),
        ),
    ):
        migrations._ensure_payment_refund_schema(connection)

    assert _executed_sql(connection) == [migrations.PAYMENT_REFUNDS_CREATE_SQL]


def test_refund_schema_upgrade_rejects_unrecoverable_existing_table():
    connection = MagicMock()

    with (
        patch.object(migrations, '_column_names', return_value={'id'}),
        pytest.raises(RuntimeError, match='missing required columns'),
    ):
        migrations._ensure_payment_refund_schema(connection)


def test_mysql_schema_migration_lock_is_acquired_and_released():
    connection = MagicMock()
    connection.dialect.name = 'mysql'
    connection.execute.return_value.scalar.return_value = 1

    with migrations._schema_migration_lock(connection):
        pass

    statements = _executed_sql(connection)
    assert statements == [
        'SELECT GET_LOCK(:lock_key, 30)',
        'SELECT RELEASE_LOCK(:lock_key)',
    ]
