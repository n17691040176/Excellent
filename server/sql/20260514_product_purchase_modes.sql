ALTER TABLE product_zone_configs
    ADD COLUMN points_only_enabled TINYINT(1) NOT NULL DEFAULT 0 AFTER balance_purchase_enabled,
    ADD COLUMN points_cash_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER points_only_enabled,
    ADD COLUMN cash_only_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER points_cash_enabled;
