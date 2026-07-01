import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variable or fall back to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./data/amazon_autolister.db"

# SQLAlchemy 1.4+ / 2.0 requires postgresql:// instead of postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create data directory for SQLite if it doesn't exist
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# For SQLite, we need connect_args={"check_same_thread": False}
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:///") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Export Session as SessionLocal for API compatibility
Session = SessionLocal
