import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.base import Base  # noqa
from app.db.session import engine  # noqa

# import models so SQLAlchemy metadata knows them
from app.models import *  # noqa

Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
