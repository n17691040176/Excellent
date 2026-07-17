"""最简单的数据库连接测试"""
import sys

sys.path.insert(0, '.')

from sqlalchemy import create_engine, text

# 使用正确的凭据
DATABASE_URL = 'mysql+pymysql://excellent:excellent123@127.0.0.1:3306/excellent_app?charset=utf8mb4'
print("Connecting to: mysql+pymysql://excellent:***@127.0.0.1:3306/excellent_app")

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("[OK] Database connected successfully!")
        print(f"Result: {result.fetchone()}")
except Exception as e:
    print(f"[ERROR] Database connection failed: {e}")
