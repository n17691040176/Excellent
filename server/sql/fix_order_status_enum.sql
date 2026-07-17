-- Migration: Update order_status column to support new enum values
-- Date: 2026-06-23
-- Issue: Database order_status enum uses old values (CREATED, PAID, CONFIRMED, CLOSED, REFUNDED)
--        but code expects new values (PENDING_PAYMENT, PENDING_SHIP, SHIPPED, COMPLETED, PENDING_REVIEW)

-- First, check if there are existing orders and update them
UPDATE orders SET order_status = 'PENDING_PAYMENT' WHERE order_status = 'CREATED';
UPDATE orders SET order_status = 'PENDING_SHIP' WHERE order_status = 'PAID';
UPDATE orders SET order_status = 'COMPLETED' WHERE order_status = 'CONFIRMED';

-- Alter the column to VARCHAR to allow any status value
ALTER TABLE orders MODIFY COLUMN order_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_PAYMENT';

-- Note: If you want to use ENUM instead of VARCHAR:
-- ALTER TABLE orders MODIFY COLUMN order_status ENUM('PENDING_PAYMENT','PENDING_SHIP','SHIPPED','COMPLETED','PENDING_REVIEW') NOT NULL DEFAULT 'PENDING_PAYMENT';

-- Similarly update pay_status column if needed
-- ALTER TABLE orders MODIFY COLUMN pay_status ENUM('UNPAID','PAID') NOT NULL DEFAULT 'UNPAID';
