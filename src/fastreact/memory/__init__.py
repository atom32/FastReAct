"""
Memory module

Provides long-term memory retrieval using vector search, BM25 keyword search, and hybrid search.
"""

from .embeddings import (
    EmbeddingProvider,
    OpenAIEmbedding,
    LocalEmbedding,
    ModelScopeEmbedding,
    EmbeddingCache,
    EmbeddingGenerator,
    EmbeddingBuilder,
    create_model_change_callback,
)
from .vector_store import VectorStore, VectorStoreBuilder
from .sqlite_vec import SQLiteVecStore, APSWVecStore
from .retriever import MemoryRetriever, RetrieverBuilder
from .bm25 import BM25Index, BM25Retriever
from .fusion import ReciprocalRankFusion, WeightedFusion, HybridRetriever

__all__ = [
    "EmbeddingProvider",
    "OpenAIEmbedding",
    "LocalEmbedding",
    "ModelScopeEmbedding",
    "EmbeddingCache",
    "EmbeddingGenerator",
    "EmbeddingBuilder",
    "create_model_change_callback",
    "VectorStore",
    "VectorStoreBuilder",
    "SQLiteVecStore",
    "APSWVecStore",
    "MemoryRetriever",
    "RetrieverBuilder",
    "BM25Index",
    "BM25Retriever",
    "ReciprocalRankFusion",
    "WeightedFusion",
    "HybridRetriever",
]
