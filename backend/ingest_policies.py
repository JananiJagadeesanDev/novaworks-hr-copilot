"""
ingest_policies.py — One-shot CLI script to embed HR policies into Qdrant.

Run from the backend/ directory:
    py ingest_policies.py

This is idempotent: existing Qdrant collection is deleted and rebuilt each run,
so the vector index always reflects the current state of the hr_policies table.
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest_policies")

# Register all SQLAlchemy models before importing anything else
import app.db.base_import  # noqa: F401, E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.services.ai.vector_store import build_policy_index  # noqa: E402


def main() -> None:
    logger.info("=== NovaWorks Policy Ingestion Script ===")

    # Ensure all tables exist (safe no-op if already created by seed/alembic)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        count = build_policy_index(db)
        if count == 0:
            logger.warning(
                "No policies were indexed. Make sure the database is seeded "
                "(`py seed.py`) and hr_policies rows are marked is_active=True."
            )
            sys.exit(1)
        else:
            logger.info("✓ Successfully indexed %d policy chunks into Qdrant.", count)
            logger.info("  Collection : %s", "hr_policies")
            logger.info("  Vector store : ./qdrant_data/")
            logger.info("Ready for RAG queries.")
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
