"""
Vector store abstraction layer

Provides unified interface for vector storage backends.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector stores"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector store"""
        pass

    @abstractmethod
    async def add_document(
        self,
        doc_id: str,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document"""
        pass

    @abstractmethod
    async def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> None:
        """Add document chunks with embeddings"""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        session_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Semantic similarity search"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> int:
        """Delete all data for a session"""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        pass


class VectorStoreBuilder:
    """Builder for creating vector stores from config"""

    @staticmethod
    def create(
        backend: str = "sqlite_vec",
        db_path: str = "./data/memory.db",
        embedding_dim: int = 768,
        **kwargs
    ) -> VectorStore:
        """Create vector store instance (simple interface)

        Args:
            backend: Backend type ("sqlite_vec" or "apsw")
            db_path: Database path
            embedding_dim: Embedding vector dimensions
            **kwargs: Additional parameters

        Returns:
            VectorStore instance
        """
        if backend == "sqlite_vec":
            from .sqlite_vec import SQLiteVecStore
            return SQLiteVecStore(
                db_path=db_path,
                embedding_dim=embedding_dim,
            )
        elif backend == "apsw":
            from .sqlite_vec import APSWVecStore
            return APSWVecStore(
                db_path=db_path,
                embedding_dim=embedding_dim,
            )
        else:
            raise ValueError(f"Unknown vector store backend: {backend}")

    @staticmethod
    def from_config(
        store_type: str,
        config: Dict[str, Any],
    ) -> VectorStore:
        """Create vector store from configuration

        Args:
            store_type: Type of vector store ("sqlite_vec")
            config: Configuration dict

        Returns:
            VectorStore instance
        """
        if store_type == "sqlite_vec":
            from .sqlite_vec import SQLiteVecStore
            return SQLiteVecStore(
                db_path=config.get("db_path", "./data/memory.db"),
                embedding_dim=config.get("embedding_dim", 1536),
            )
        else:
            raise ValueError(f"Unsupported vector store type: {store_type}")
