"""
vector_store.py — Qdrant-backed vector store for HR policy embeddings.

Responsibilities:
  - Manage a singleton embedded QdrantClient (no external server needed).
  - build_policy_index(db): load active HR policies from DB, chunk them,
    embed via Google text-embedding-004, and upsert into Qdrant.
  - get_policy_retriever(): return a LangChain VectorStoreRetriever for RAG.

Qdrant is run in embedded / local mode (data persisted to QDRANT_PATH on disk).
Re-running build_policy_index is idempotent: it recreates the collection from
scratch each time so the index always reflects the latest DB state.
"""

import logging
from functools import lru_cache
from typing import Optional

from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.hr_policy import HRPolicy
from app.services.ai.embeddings import get_embeddings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Qdrant client singleton
# ---------------------------------------------------------------------------
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Return a process-level QdrantClient (Qdrant Cloud if URL is provided, else embedded disk)."""
    global _qdrant_client
    if _qdrant_client is None:
        if settings.QDRANT_URL:
            _qdrant_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
            logger.info("QdrantClient initialised (cloud/remote URL=%s)", settings.QDRANT_URL)
        else:
            _qdrant_client = QdrantClient(path=settings.QDRANT_PATH)
            logger.info("QdrantClient initialised in embedded mode (path=%s)", settings.QDRANT_PATH)
    return _qdrant_client


# ---------------------------------------------------------------------------
# Vector dimensions for Google gemini-embedding-2 (3072 dims)
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 3072


# ---------------------------------------------------------------------------
# Chunking helper
# ---------------------------------------------------------------------------
def _chunk_policies(policies: list[HRPolicy]) -> tuple[list[str], list[dict]]:
    """Chunk policy content and return (texts, metadatas) parallel lists."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    texts: list[str] = []
    metadatas: list[dict] = []

    for policy in policies:
        chunks = splitter.split_text(policy.content)
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append(
                {
                    "policy_id": policy.id,
                    "title": policy.title,
                    "category": policy.category,
                }
            )

    return texts, metadatas


# ---------------------------------------------------------------------------
# Public: build index
# ---------------------------------------------------------------------------
def build_policy_index(db: Session) -> int:
    """Load all active HRPolicy rows, embed them, and upsert into Qdrant.

    Returns the number of vectors stored.
    This is idempotent: the collection is recreated from scratch each call.
    """
    policies = db.query(HRPolicy).filter(HRPolicy.is_active.is_(True)).all()
    if not policies:
        logger.warning("No active HR policies found — index will be empty.")
        return 0

    logger.info("Ingesting %d active HR policies into Qdrant ...", len(policies))
    texts, metadatas = _chunk_policies(policies)

    client = get_qdrant_client()

    # Recreate collection so index always matches the current DB state
    if client.collection_exists(settings.POLICY_COLLECTION):
        client.delete_collection(settings.POLICY_COLLECTION)
        logger.info("Deleted existing Qdrant collection '%s'", settings.POLICY_COLLECTION)

    client.create_collection(
        collection_name=settings.POLICY_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    logger.info("Created Qdrant collection '%s'", settings.POLICY_COLLECTION)

    # Embed and upsert via LangChain helper
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=settings.POLICY_COLLECTION,
        embedding=get_embeddings(),
    )
    vector_store.add_texts(texts=texts, metadatas=metadatas)

    logger.info("Upserted %d chunks into '%s'", len(texts), settings.POLICY_COLLECTION)
    return len(texts)


# ---------------------------------------------------------------------------
# Public: retriever
# ---------------------------------------------------------------------------
def get_policy_retriever(k: int = 4):
    """Return a LangChain retriever over the existing Qdrant policy collection.

    Args:
        k: Number of top chunks to retrieve per query.

    Raises:
        RuntimeError: If the policy collection has not been built yet.
    """
    client = get_qdrant_client()

    if not client.collection_exists(settings.POLICY_COLLECTION):
        raise RuntimeError(
            f"Qdrant collection '{settings.POLICY_COLLECTION}' does not exist. "
            "Run build_policy_index() or `py ingest_policies.py` first."
        )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=settings.POLICY_COLLECTION,
        embedding=get_embeddings(),
    )

    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )
