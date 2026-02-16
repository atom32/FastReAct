"""
Memory Retriever

Retrieves relevant historical conversations using semantic search.
Supports hybrid search (BM25 + Semantic) for improved accuracy.
"""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

from .vector_store import VectorStore
from ..context.token_counter import TokenCounter

# Avoid circular import
if TYPE_CHECKING:
    from .bm25 import BM25Retriever
    from .fusion import HybridRetriever
    from ..context import HybridSearchConfig

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """Retrieves relevant historical conversations

    Uses vector similarity search to find relevant past conversations.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_generator,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        top_k: int = 3,
        min_similarity: float = 0.7,
        hybrid_config: Optional["HybridSearchConfig"] = None,
    ):
        """Initialize memory retriever

        Args:
            vector_store: Vector store instance
            embedding_generator: EmbeddingGenerator instance
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Token overlap between chunks
            top_k: Number of results to retrieve
            min_similarity: Minimum similarity threshold
            hybrid_config: Optional hybrid search configuration
        """
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.hybrid_config = hybrid_config

        # Initialize BM25 retriever if hybrid search is enabled
        self.bm25_retriever: Optional["BM25Retriever"] = None
        if hybrid_config and hybrid_config.enabled:
            from .bm25 import BM25Retriever

            self.bm25_retriever = BM25Retriever(
                k1=hybrid_config.bm25_k1,
                b=hybrid_config.bm25_b,
                language=hybrid_config.bm25_language,
                top_k=top_k * 2,  # Get more candidates for fusion
                min_score=0.0,  # Don't filter yet
            )
            logger.info(f"Hybrid search enabled: {hybrid_config.fusion_method}, alpha={hybrid_config.alpha}")

        # Initialize TokenCounter for reuse (performance optimization)
        self._token_counter = TokenCounter(model="gpt-4")

    async def initialize(self) -> None:
        """Initialize the retriever"""
        await self.vector_store.initialize()

        # Initialize BM25 retriever if hybrid search is enabled
        if self.bm25_retriever:
            await self.bm25_retriever.initialize()
            logger.info("BM25 retriever initialized for hybrid search")

    async def index_session(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
    ) -> None:
        """Index a session's messages for retrieval

        Args:
            session_id: Session ID
            messages: List of messages to index
        """
        if not messages:
            return

        # Combine messages into document
        content = self._format_messages(messages)

        # Create document
        doc_id = f"{session_id}_doc"
        await self.vector_store.add_document(
            doc_id=doc_id,
            session_id=session_id,
            content=content,
            metadata={"message_count": len(messages)},
        )

        # Split into chunks
        chunks = self._split_into_chunks(
            doc_id=doc_id,
            session_id=session_id,
            content=content,
        )

        # Generate embeddings for chunks
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings = await self.embedding_generator.generate_batch(chunk_texts)

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        # Store chunks in vector store
        await self.vector_store.add_chunks(chunks)

        # Index to BM25 if hybrid search is enabled
        if self.bm25_retriever:
            bm25_docs = [
                {"doc_id": chunk["id"], "content": chunk["content"]}
                for chunk in chunks
            ]
            await self.bm25_retriever.index_documents(bm25_docs)
            logger.info(f"Indexed {len(bm25_docs)} chunks to BM25")

        logger.info(f"Indexed {len(messages)} messages as {len(chunks)} chunks")

    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into text

        Args:
            messages: List of messages

        Returns:
            Formatted text
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"[{role.upper()}]: {content}")
        return "\n\n".join(lines)

    def _split_into_chunks(
        self,
        doc_id: str,
        session_id: str,
        content: str,
    ) -> List[Dict[str, Any]]:
        """Split content into chunks

        Args:
            doc_id: Document ID
            session_id: Session ID
            content: Content to split

        Returns:
            List of chunk dicts
        """
        # Use TokenCounter to estimate chunk sizes (reused instance for performance)
        counter = self._token_counter

        chunks = []
        current_chunk = []
        current_tokens = 0

        # Split by paragraphs first
        paragraphs = content.split("\n\n")

        for para_index, para in enumerate(paragraphs):
            para_tokens = counter.count_tokens(para)

            # Check if paragraph alone exceeds chunk_size
            if para_tokens > self.chunk_size:
                # Split long paragraph
                sentences = para.split(". ")
                for sent in sentences:
                    if not sent:
                        continue
                    sent_tokens = counter.count_tokens(sent)

                    if current_tokens + sent_tokens > self.chunk_size and current_chunk:
                        # Save current chunk
                        chunks.append(self._create_chunk(
                            chunks, current_chunk, doc_id, session_id
                        ))
                        current_chunk = []
                        current_tokens = 0

                    current_chunk.append(sent)
                    current_tokens += sent_tokens
            else:
                # Check if adding paragraph exceeds chunk size
                if current_tokens + para_tokens > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append(self._create_chunk(
                        chunks, current_chunk, doc_id, session_id
                    ))
                    current_chunk = []
                    current_tokens = 0

                current_chunk.append(para)
                current_tokens += para_tokens

        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                chunks, current_chunk, doc_id, session_id
            ))

        return chunks

    def _create_chunk(
        self,
        existing_chunks: List[Dict[str, Any]],
        content_parts: List[str],
        doc_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """Create a chunk dict

        Args:
            existing_chunks: Existing chunks list (to get index)
            content_parts: Content parts for this chunk
            doc_id: Document ID
            session_id: Session ID

        Returns:
            Chunk dict
        """
        chunk_index = len(existing_chunks)
        content = "\n\n".join(content_parts)

        return {
            "id": f"{doc_id}_chunk_{chunk_index}",
            "doc_id": doc_id,
            "session_id": session_id,
            "chunk_index": chunk_index,
            "content": content,
            "metadata": {
                "created_at": datetime.now().isoformat(),
            },
        }

    async def retrieve(
        self,
        query: str,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant historical conversations

        Args:
            query: Query text
            session_id: Optional session ID filter

        Returns:
            List of relevant chunks with metadata
        """
        # Hybrid search mode
        if self.bm25_retriever and self.hybrid_config and self.hybrid_config.enabled:
            return await self._hybrid_retrieve(query, session_id)

        # Semantic-only mode (default)
        return await self._semantic_retrieve(query, session_id)

    async def _semantic_retrieve(
        self,
        query: str,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve using semantic search only

        Args:
            query: Query text
            session_id: Optional session ID filter

        Returns:
            List of relevant chunks with metadata
        """
        # Generate query embedding
        query_embedding = await self.embedding_generator.generate(query)

        # Search vector store
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            session_id=session_id,
            top_k=self.top_k,
            min_similarity=self.min_similarity,
        )

        logger.info(f"Retrieved {len(results)} relevant chunks (semantic search)")

        return results

    async def _hybrid_retrieve(
        self,
        query: str,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve using hybrid search (BM25 + Semantic)

        Args:
            query: Query text
            session_id: Optional session ID filter

        Returns:
            List of relevant chunks with metadata
        """
        from .fusion import HybridRetriever

        # Create hybrid retriever
        hybrid = HybridRetriever(
            bm25_retriever=self.bm25_retriever,
            semantic_retriever=self,
            fusion_method=self.hybrid_config.fusion_method,
            alpha=self.hybrid_config.alpha,
            rrf_k=self.hybrid_config.rrf_k,
        )

        # Retrieve using hybrid search
        results = await hybrid.retrieve(
            query=query,
            session_id=session_id,
            top_k=self.top_k,
            min_score=self.hybrid_config.min_score,
        )

        logger.info(f"Retrieved {len(results)} relevant chunks (hybrid search: {self.hybrid_config.fusion_method})")

        return results

    async def retrieve_as_context(
        self,
        query: str,
        session_id: Optional[str] = None,
    ) -> str:
        """Retrieve relevant history and format as context

        Args:
            query: Query text
            session_id: Optional session ID filter

        Returns:
            Formatted context string
        """
        results = await self.retrieve(query, session_id)

        if not results:
            return ""

        # Format results as context
        lines = [
            "[Relevant information from previous conversations]:",
        ]

        for i, result in enumerate(results, 1):
            similarity = result.get("similarity", 0)
            content = result.get("content", "")
            lines.append(f"\n{i}. [Similarity: {similarity:.2f}] {content}")

        return "\n".join(lines)

    async def close(self) -> None:
        """Close resources"""
        await self.embedding_generator.close()
        # BM25 doesn't need explicit closing, but we can add it if needed in the future


class RetrieverBuilder:
    """Builder for creating MemoryRetriever from config"""

    @staticmethod
    def from_config(
        vector_store: VectorStore,
        embedding_generator,
        memory_config: Dict[str, Any],
        hybrid_config: Optional["HybridSearchConfig"] = None,
    ) -> MemoryRetriever:
        """Create MemoryRetriever from configuration

        Args:
            vector_store: Vector store instance
            embedding_generator: EmbeddingGenerator instance
            memory_config: Memory configuration dict
            hybrid_config: Optional hybrid search configuration

        Returns:
            MemoryRetriever instance
        """
        return MemoryRetriever(
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            chunk_size=memory_config.get("chunk_size", 500),
            chunk_overlap=memory_config.get("chunk_overlap", 50),
            top_k=memory_config.get("top_k", 3),
            min_similarity=memory_config.get("min_similarity", 0.7),
            hybrid_config=hybrid_config,
        )
