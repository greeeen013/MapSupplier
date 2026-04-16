from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Absolute path so the DB is found regardless of working directory
_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "suppliers.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
