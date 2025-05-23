from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
from contextlib import contextmanager
from typing import Generator
import random
from tenacity import retry, stop_after_attempt, wait_exponential

# Create engines for primary and replica
primary_engine = create_engine(settings.PRIMARY_DB_URL, pool_pre_ping=True)
replica_engine = create_engine(settings.REPLICA_DB_URL, pool_pre_ping=True)

# Session factories
PrimarySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=primary_engine)
ReplicaSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=replica_engine)

Base = declarative_base()

@contextmanager
def get_primary_db() -> Generator[Session, None, None]:
    """Get a database session for write operations (primary node)"""
    db = PrimarySessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_replica_db() -> Generator[Session, None, None]:
    """Get a database session for read operations (replica node)"""
    db = ReplicaSessionLocal()
    try:
        yield db
    finally:
        db.close()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def init_db() -> None:
    """Initialize database with retries"""
    Base.metadata.create_all(bind=primary_engine)

# Dependency functions for FastAPI
def get_primary_session() -> Generator[Session, None, None]:
    with get_primary_db() as session:
        yield session

def get_replica_session() -> Generator[Session, None, None]:
    with get_replica_db() as session:
        yield session 