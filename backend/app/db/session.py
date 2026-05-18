from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BASE_DIR = Path(__file__).resolve().parents[2]
SQLITE_PATH = BASE_DIR / "filing_counter.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{SQLITE_PATH.as_posix()}")

engine_kwargs: dict = {
    "pool_pre_ping": True,
}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
