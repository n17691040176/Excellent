-- Clear the legacy shared earning-rule pool once.
-- Product-specific commission settings are stored in product_zone_configs and
-- are intentionally not affected by this migration.
CREATE TABLE IF NOT EXISTS app_data_migrations (
    migration_key VARCHAR(128) PRIMARY KEY,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DELETE FROM earning_rules
WHERE NOT EXISTS (
    SELECT 1
    FROM app_data_migrations
    WHERE migration_key = '20260729_clear_earning_rule_pool'
);

UPDATE commission_configs
SET level1_rate = 0,
    level2_rate = 0,
    is_active = 0
WHERE NOT EXISTS (
    SELECT 1
    FROM app_data_migrations
    WHERE migration_key = '20260729_clear_earning_rule_pool'
);

INSERT IGNORE INTO app_data_migrations (migration_key, applied_at)
VALUES ('20260729_clear_earning_rule_pool', CURRENT_TIMESTAMP);
