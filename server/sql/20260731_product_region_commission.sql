ALTER TABLE product_zone_configs
    ADD COLUMN custom_commission_level1_enabled TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_level2_enabled TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_county_agent_enabled TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_city_agent_enabled TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_county_agent_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_city_agent_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_county_agent_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    ADD COLUMN custom_commission_city_agent_amount DECIMAL(18,2) NOT NULL DEFAULT 0;

UPDATE product_zone_configs
SET custom_commission_level1_enabled = IF(
        custom_commission_level1_rate > 0 OR custom_commission_level1_amount > 0, 1, 0
    ),
    custom_commission_level2_enabled = IF(
        custom_commission_level2_rate > 0 OR custom_commission_level2_amount > 0, 1, 0
    );
