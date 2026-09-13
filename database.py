import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Railway provides DATABASE_URL for PostgreSQL.
# Locally, fall back to SQLite.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./locations.db"
)


# Railway/PostgreSQL may provide the older postgres:// format.
# SQLAlchemy expects postgresql://.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


# SQLite needs this special connection argument.
# PostgreSQL does not.
connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False
    }


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()