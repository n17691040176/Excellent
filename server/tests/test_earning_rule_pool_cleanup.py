from sqlalchemy import create_engine, text

from app.db.migrations import EARNING_RULE_POOL_CLEANUP_KEY, _clear_legacy_earning_rule_pool


def test_cleanup_clears_existing_rules_only_once():
    test_engine = create_engine('sqlite+pysqlite:///:memory:')

    with test_engine.begin() as connection:
        connection.execute(text('CREATE TABLE earning_rules (id INTEGER PRIMARY KEY, rule_code VARCHAR(64))'))
        connection.execute(
            text(
                'CREATE TABLE commission_configs ('
                'id INTEGER PRIMARY KEY, level1_rate NUMERIC, level2_rate NUMERIC, is_active BOOLEAN'
                ')'
            )
        )
        connection.execute(
            text(
                'CREATE TABLE product_zone_configs ('
                'id INTEGER PRIMARY KEY, custom_commission_enabled BOOLEAN, '
                'custom_commission_level1_rate NUMERIC'
                ')'
            )
        )
        connection.execute(
            text("INSERT INTO earning_rules (id, rule_code) VALUES (1, 'OLD_RULE'), (2, 'OLD_RULE_2')")
        )
        connection.execute(
            text('INSERT INTO commission_configs (id, level1_rate, level2_rate, is_active) VALUES (1, 5, 2, 1)')
        )
        connection.execute(
            text(
                'INSERT INTO product_zone_configs '
                '(id, custom_commission_enabled, custom_commission_level1_rate) VALUES (1, 1, 12.5)'
            )
        )

        _clear_legacy_earning_rule_pool(connection)

        assert connection.execute(text('SELECT COUNT(*) FROM earning_rules')).scalar_one() == 0
        assert connection.execute(
            text('SELECT level1_rate, level2_rate, is_active FROM commission_configs')
        ).one() == (0, 0, 0)
        assert connection.execute(
            text('SELECT custom_commission_enabled, custom_commission_level1_rate FROM product_zone_configs')
        ).one() == (1, 12.5)
        assert connection.execute(
            text('SELECT COUNT(*) FROM app_data_migrations WHERE migration_key = :migration_key'),
            {'migration_key': EARNING_RULE_POOL_CLEANUP_KEY},
        ).scalar_one() == 1

        connection.execute(text("INSERT INTO earning_rules (id, rule_code) VALUES (3, 'NEW_MANUAL_RULE')"))
        _clear_legacy_earning_rule_pool(connection)

        assert connection.execute(text('SELECT rule_code FROM earning_rules')).scalar_one() == 'NEW_MANUAL_RULE'
