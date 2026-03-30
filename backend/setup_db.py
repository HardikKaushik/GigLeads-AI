"""Create all database tables from SQLAlchemy models.

Use this instead of Alembic for fresh deployments (e.g., Render).
It's idempotent — safe to run multiple times.
"""

import os
import sys

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.database import engine, Base
from backend.db import models  # noqa: F401 — registers all models

def setup():
    print(f"Creating tables on: {engine.url}")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("All tables created successfully.")

    # Add any missing enum values (for pipeline_status)
    from sqlalchemy import text
    with engine.connect() as conn:
        extra_values = ["finding_jobs", "generating_cover_letters"]
        for val in extra_values:
            try:
                conn.execute(text(f"ALTER TYPE pipeline_status ADD VALUE IF NOT EXISTS '{val}'"))
            except Exception:
                pass  # Already exists
        conn.commit()
    print("Enum values verified.")

if __name__ == "__main__":
    setup()
