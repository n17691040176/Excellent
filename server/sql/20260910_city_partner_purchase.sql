-- Dedicated seat payment metadata. Application startup also creates this table.
-- Normalize native ENUM deployments so CITY_PARTNER_ORDER is accepted. Existing values are preserved.
ALTER TABLE orders MODIFY COLUMN order_type VARCHAR(32) NOT NULL;

CREATE TABLE IF NOT EXISTS city_partner_purchases (
    order_id BIGINT PRIMARY KEY,
    seat_id BIGINT NOT NULL,
    price_version INT NOT NULL,
    quoted_price DECIMAL(18,2) NOT NULL,
    settlement_error VARCHAR(255) NULL,
    settled_at DATETIME NULL,
    KEY ix_city_partner_purchases_seat_id (seat_id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (seat_id) REFERENCES city_partner_seats(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Reconcile duplicate non-NULL account types before applying this constraint.
CREATE UNIQUE INDEX uq_users_system_account_type ON users (system_account_type);
