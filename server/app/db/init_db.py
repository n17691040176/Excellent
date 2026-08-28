from app.db.base import Base
from app.db.migrations import _schema_migration_lock
from app.db.session import engine
from app.models import *  # noqa: F401,F403


def init_db() -> None:
    with engine.begin() as connection, _schema_migration_lock(connection):
        Base.metadata.create_all(bind=connection)


if __name__ == '__main__':
    init_db()
