from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Retrieve database URL from settings
DATABASE_URL = settings.DATABASE_URL

# Render / Neon sometimes provide 'postgres://' which SQLAlchemy requires to be 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure engine safely: check_same_thread is strictly for SQLite and will crash PostgreSQL
if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency Injection for API endpoints


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
