from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# SQLite requires check_same_thread=False for FastAPI concurrency
engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency Injection for API endpoints


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
