from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={'init_command': "SET time_zone = '+00:00'"},
    pool_pre_ping=True,
    pool_size=settings.mysql_pool_size,
    max_overflow=settings.mysql_max_overflow,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
