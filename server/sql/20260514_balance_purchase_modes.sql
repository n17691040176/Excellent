ALTER TABLE product_zone_configs
    ADD COLUMN balance_only_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER cash_only_enabled,
    ADD COLUMN balance_points_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER balance_only_enabled;
