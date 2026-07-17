ALTER TABLE products
    ADD COLUMN category_id BIGINT NULL AFTER zone_type,
    ADD INDEX ix_products_category_id (category_id),
    ADD CONSTRAINT fk_products_category_id
        FOREIGN KEY (category_id) REFERENCES product_categories (id)
        ON DELETE RESTRICT;

ALTER TABLE products
    MODIFY COLUMN zone_type ENUM('REPURCHASE', 'SELF_OPERATED', 'HOT_SALE', 'LOCAL_LIFE')
    NOT NULL DEFAULT 'SELF_OPERATED';
