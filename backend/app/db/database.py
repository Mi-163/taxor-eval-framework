from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Retrieve database URL from settings
DATABASE_URL = settings.DATABASE_URL

# Render / Neon sometimes provide 'postgres://' which SQLAlchemy requires to be 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure engine safely: handle SQLite and PostgreSQL separately
if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # 1. sslmode=require enforces secure connection for Neon
    # 2. poolclass=NullPool prevents SQLAlchemy from crashing when using Neon's -pooler URL
    engine = create_engine(
        DATABASE_URL,
        connect_args={"sslmode": "require"},
        poolclass=NullPool
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
