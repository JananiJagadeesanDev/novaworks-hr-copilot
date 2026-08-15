"""
embeddings.py — Thin factory wrapper for the Google embedding model.

Usage:
    from app.services.ai.embeddings import get_embeddings
    embeddings = get_embeddings()
"""

from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Return a cached GoogleGenerativeAIEmbeddings instance.

    Uses ``settings.EMBEDDING_MODEL`` (default: ``models/text-embedding-004``).
    The instance is created once per process lifetime.
    """
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        task_type="retrieval_document",
    )
