ALTER TABLE product_zone_configs
    ADD COLUMN alipay_purchase_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER balance_purchase_enabled,
    ADD COLUMN wechat_purchase_enabled TINYINT(1) NOT NULL DEFAULT 0 AFTER alipay_purchase_enabled;

UPDATE product_zone_configs
SET balance_purchase_enabled = 1,
    balance_only_enabled = 1,
    cash_only_enabled = 1;
