import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Primary PostgreSQL URL, with local SQLite fallback for seamless execution
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/caterpillar_rental")
SQLITE_URL = "sqlite:///./rental_tracking.db"

try:
    # Attempt Postgres connection first if available, else fallback to SQLite
    engine = create_engine(POSTGRES_URL, connect_args={"connect_timeout": 2} if "postgresql" in POSTGRES_URL else {})
    # Test connection
    with engine.connect() as conn:
        pass
    print("Using PostgreSQL Database")
except Exception as e:
    print(f"PostgreSQL connection fallback to SQLite: {e}")
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    print("Using SQLite Database")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
