ALTER TABLE product_zone_configs
    ADD COLUMN custom_commission_enabled TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_method VARCHAR(32) NOT NULL DEFAULT 'RATE',
    ADD COLUMN custom_commission_level1_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_level2_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_level3_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_level1_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_level2_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_level3_amount DECIMAL(18,2) NOT NULL DEFAULT 0;
