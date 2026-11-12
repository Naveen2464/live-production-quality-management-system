import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try connecting to PostgreSQL, fallback to SQLite if configured and PostgreSQL unreachable
engine = None
try:
    pg_engine = create_engine(
        settings.sync_database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
    # Quick probe
    with pg_engine.connect() as conn:
        logger.info("Connected successfully to PostgreSQL database.")
    engine = pg_engine
except Exception as e:
    if settings.USE_SQLITE_FALLBACK:
        logger.warning(f"PostgreSQL connection failed ({e}). Falling back to SQLite: {settings.SQLITE_DB_PATH}")
        engine = create_engine(
            settings.SQLITE_DB_PATH,
            connect_args={"check_same_thread": False}
        )
    else:
        raise e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for obtaining database sessions per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

