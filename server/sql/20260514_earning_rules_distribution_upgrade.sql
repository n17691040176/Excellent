ALTER TABLE earning_rules
    ADD COLUMN product_id BIGINT NULL AFTER rule_type,
    ADD COLUMN member_level VARCHAR(32) NULL AFTER product_id,
    ADD COLUMN commission_level INT NULL AFTER member_level;

ALTER TABLE earning_rules
    ADD INDEX idx_earning_rules_product_id (product_id),
    ADD INDEX idx_earning_rules_member_level (member_level),
    ADD INDEX idx_earning_rules_commission_level (commission_level);
