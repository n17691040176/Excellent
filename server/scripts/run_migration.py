#!/usr/bin/env python3
"""
Run migration to fix order_status enum in database
"""
import sys

sys.path.insert(0, '/app')

from sqlalchemy import text

from app.db.session import SessionLocal


def run_migration():
    db = SessionLocal()
    try:
        # Update existing orders first
        db.execute(text("UPDATE orders SET order_status = 'PENDING_PAYMENT' WHERE order_status = 'CREATED'"))
        db.execute(text("UPDATE orders SET order_status = 'PENDING_SHIP' WHERE order_status = 'PAID'"))
        db.execute(text("UPDATE orders SET order_status = 'COMPLETED' WHERE order_status = 'CONFIRMED'"))
        db.commit()
        print("Updated existing order statuses")

        # Alter the column
        db.execute(text("ALTER TABLE orders MODIFY COLUMN order_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_PAYMENT'"))
        db.commit()
        print("Altered order_status column to VARCHAR(32)")

        # Verify
        result = db.execute(text("SHOW COLUMNS FROM orders LIKE 'order_status'"))
        for row in result:
            print(f"New column definition: {row}")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
