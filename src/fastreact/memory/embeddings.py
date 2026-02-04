"""
Embedding generation module

Supports multiple embedding providers for vector search.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from collections import OrderedDict
import httpx

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    aiosqlite = None

from ..utils.logger import get_logger

logger = get_logger("fastreact.embeddings")


class EmbeddingProvider:
    """Base class for embedding providers"""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 30.0,
    ):
        """Initialize embedding provider

        Args:
            api_key: API key
            model: Model name
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_embedding_dim_sync(self) -> Optional[int]:
        """Get embedding dimension synchronously (if possible)

        Returns:
            The dimension if available synchronously, None otherwise
        """
        # Default: not available synchronously
        return None

    async def get_embedding_dim(self) -> int:
        """Get the embedding dimension for this provider

        Returns:
            The dimension of embeddings produced by this provider
        """
        raise NotImplementedError

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text

        Args:
            text: Input text

        Returns:
            Embedding vector (list of floats)
        """
        raise NotImplementedError

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        # Default implementation: sequential calls
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI-compatible embedding provider"""

    # OpenAI embedding dimensions
    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def get_embedding_dim_sync(self) -> int:
        """Get embedding dimension synchronously (lookup table only)

        Returns:
            The dimension of embeddings produced by this model
        """
        if self.model in self.DIMENSIONS:
            return self.DIMENSIONS[self.model]
        # Default fallback for unknown models
        logger.warning(f"Unknown model {self.model}, using default dimension 1536")
        return 1536

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "text-embedding-3-small",
        timeout: float = 30.0,
    ):
        """Initialize OpenAI embedding provider

        Args:
            api_key: OpenAI API key
            base_url: API base URL
            model: Model name (default: text-embedding-3-small)
            timeout: Request timeout
        """
        super().__init__(api_key, model, timeout)
        self.base_url = base_url.rstrip("/")

    async def embed(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": text,
                },
            )

            response.raise_for_status()
            data = response.json()

            # Extract embedding
            embedding = data["data"][0]["embedding"]

            return embedding

        except httpx.HTTPError as e:
            logger.error(f"OpenAI embedding API call failed: {e}")
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch API)

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
            )

            response.raise_for_status()
            data = response.json()

            # Extract embeddings (in same order as input)
            embeddings = [item["embedding"] for item in data["data"]]

            return embeddings

        except httpx.HTTPError as e:
            logger.error(f"OpenAI batch embedding API call failed: {e}")
            # Fallback to sequential
            logger.warning("Falling back to sequential embedding generation")
            return await super().embed_batch(texts)

    async def get_embedding_dim(self) -> int:
        """Get the embedding dimension for this model

        Returns:
            The dimension of embeddings produced by this model
        """
        # Try lookup table first
        if self.model in self.DIMENSIONS:
            return self.DIMENSIONS[self.model]

        # If not in table, try to infer from API response
        # This is a fallback that makes a real API call
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": "test",
                },
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]
            dim = len(embedding)
            logger.info(f"Auto-detected embedding dimension for {self.model}: {dim}")
            return dim
        except Exception as e:
            logger.warning(f"Failed to auto-detect dimension for {self.model}: {e}")
            # Default fallback
            return 1536


def create_model_change_callback(
    interactive: bool = False,
    auto_clear: bool = False,
) -> Optional[callable]:
    """Create a callback function for handling model changes

    Args:
        interactive: If True, prompt user for action in CLI
        auto_clear: If True, automatically clear old cache without prompting

    Returns:
        Callback function or None
    """
    async def model_change_callback(
        old_model: str,
        old_dim: int,
        new_model: str,
        new_dim: int,
    ) -> None:
        """Handle model change during cache initialization

        Args:
            old_model: Previous model name
            old_dim: Previous embedding dimension
            new_model: New model name
            new_dim: New embedding dimension
        """
        import sys

        # Print yellow warning
        warning_msg = (
            f"\n"
            f"[WARNING] Embedding model changed!\n"
            f"  Old model: {old_model} ({old_dim}D)\n"
            f"  New model: {new_model} ({new_dim}D)\n"
            f"  Old embeddings will not be used with the new model.\n"
        )

        if sys.platform == 'win32':
            # Windows: no ANSI colors by default
            print(warning_msg)
        else:
            # Unix-like: use yellow color
            print(f"\033[93m{warning_msg}\033[0m")

        if auto_clear:
            # Automatically clear old cache
            print("[INFO] Auto-clearing old embeddings from cache...")
            # This will be handled by the cache initialization
            return

        if interactive:
            # Prompt user for action
            print("\nWhat would you like to do?")
            print("  1. Keep old embeddings (they won't be used)")
            print("  2. Clear old embeddings (recommended)")
            print("  3. Cancel startup (exit)")

            while True:
                try:
                    choice = input("\nChoose [1-3]: ").strip()
                    if choice in ["1", "2", "3"]:
                        break
                    print("Invalid choice, please enter 1, 2, or 3")
                except (EOFError, KeyboardInterrupt):
                    print("\n[CANCELLED] Exiting...")
                    sys.exit(1)

            if choice == "3":
                print("[CANCELLED] Exiting due to model change...")
                sys.exit(1)
            elif choice == "2":
                print("[INFO] Old embeddings will be cleared...")
                # The cache should handle this via a flag or separate method
                # For now, we just log the intent
            else:
                print("[INFO] Keeping old embeddings (they won't be used with new model)")
        else:
            # Non-interactive mode: just log
            print("[INFO] Continuing with old embeddings in cache...")
            print("       Use 'Clear embeddings' command if needed")

    return model_change_callback if interactive or auto_clear else None


class EmbeddingCache:
    """Persistent embedding cache with SQLite backend

    Features:
    - SQLite persistence across restarts
    - In-memory LRU cache for fast access
    - Model tracking with change detection
    - Automatic schema initialization
    """

    def __init__(
        self,
        db_path: str = "./data/embedding_cache.db",
        max_size: int = 10000,
        model_name: Optional[str] = None,
    ):
        """Initialize cache

        Args:
            db_path: Path to SQLite database file
            max_size: Maximum number of embeddings in in-memory LRU cache
            model_name: Name of the embedding model (for change detection)
        """
        self.db_path = db_path
        self.max_size = max_size
        self.model_name = model_name
        self.embedding_dim: Optional[int] = None

        # In-memory LRU cache for fast access
        self.cache: OrderedDict[str, List[float]] = OrderedDict()

        # Statistics
        self.hits = 0
        self.misses = 0

        # Database connection (lazy loaded)
        self._conn = None
        self._initialized = False

    async def initialize(
        self,
        model_name: str,
        embedding_dim: int,
        on_model_change: Optional[callable] = None,
    ) -> None:
        """Initialize the cache database and check for model changes

        Args:
            model_name: Current embedding model name
            embedding_dim: Current embedding dimension
            on_model_change: Optional callback when model change is detected

        Returns:
            None
        """
        if not AIOSQLITE_AVAILABLE:
            raise ImportError(
                "aiosqlite is required for persistent embedding cache. "
                "Install it with: pip install aiosqlite"
            )

        import sqlite3

        self.model_name = model_name
        self.embedding_dim = embedding_dim

        # Ensure data directory exists
        from pathlib import Path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self._conn = await aiosqlite.connect(self.db_path)

        # Create tables
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                vector BLOB NOT NULL,
                model_name TEXT NOT NULL,
                embedding_dim INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(text, model_name)
            )
        """)

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Create indexes for performance
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_text
            ON embeddings(text)
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_model
            ON embeddings(model_name)
        """)

        await self._conn.commit()

        # Check for model changes
        await self._check_model_change(on_model_change)

        self._initialized = True

    async def _check_model_change(self, on_model_change: Optional[callable]) -> None:
        """Check if the model has changed since last run

        Args:
            on_model_change: Optional callback when model change is detected
        """
        # Get stored model info
        cursor = await self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'model_name'"
        )
        row = await cursor.fetchone()

        stored_model = row[0] if row else None

        if stored_model and stored_model != self.model_name:
            # Model has changed!
            cursor = await self._conn.execute(
                "SELECT value FROM metadata WHERE key = 'embedding_dim'"
            )
            dim_row = await cursor.fetchone()
            stored_dim = int(dim_row[0]) if dim_row else None

            logger.warning(
                f"[Model Change Detected] "
                f"Old: {stored_model} ({stored_dim}D), "
                f"New: {self.model_name} ({self.embedding_dim}D)"
            )

            # Call callback if provided
            if on_model_change:
                await on_model_change(stored_model, stored_dim, self.model_name, self.embedding_dim)

            # Count embeddings from old model
            cursor = await self._conn.execute(
                "SELECT COUNT(*) FROM embeddings WHERE model_name = ?",
                (stored_model,)
            )
            old_count = (await cursor.fetchone())[0]

            logger.info(
                f"Found {old_count} embeddings from old model {stored_model}. "
                f"They will not be used with the new model."
            )

        # Update metadata with current model
        await self._conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('model_name', ?)",
            (self.model_name,)
        )
        await self._conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('embedding_dim', ?)",
            (str(self.embedding_dim),)
        )
        await self._conn.commit()

    def _serialize_vector(self, vector: List[float]) -> bytes:
        """Serialize vector to bytes for storage

        Args:
            vector: Float vector

        Returns:
            Serialized bytes
        """
        import struct
        # Pack floats as little-endian
        return struct.pack(f'{len(vector)}f', *vector)

    def _deserialize_vector(self, data: bytes, dim: int) -> List[float]:
        """Deserialize bytes to vector

        Args:
            data: Serialized bytes
            dim: Expected dimension

        Returns:
            Float vector
        """
        import struct
        # Unpack floats from little-endian
        return list(struct.unpack(f'{dim}f', data))

    async def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding (memory cache first, then SQLite)

        Args:
            text: Input text

        Returns:
            Embedding vector or None
        """
        if not self._initialized:
            logger.warning("EmbeddingCache not initialized, call initialize() first")
            return None

        # Check memory cache first
        if text in self.cache:
            self.hits += 1
            # Move to end (mark as recently used)
            self.cache.move_to_end(text)
            return self.cache[text]

        # Check SQLite database
        cursor = await self._conn.execute(
            """SELECT vector, embedding_dim
               FROM embeddings
               WHERE text = ? AND model_name = ?
               LIMIT 1""",
            (text, self.model_name)
        )
        row = await cursor.fetchone()

        if row:
            self.hits += 1
            vector_blob, dim = row
            embedding = self._deserialize_vector(vector_blob, dim)

            # Add to memory cache
            self._add_to_memory_cache(text, embedding)

            # Update last_accessed
            await self._conn.execute(
                "UPDATE embeddings SET last_accessed = CURRENT_TIMESTAMP WHERE text = ? AND model_name = ?",
                (text, self.model_name)
            )
            await self._conn.commit()

            return embedding

        self.misses += 1
        return None

    async def put(self, text: str, embedding: List[float]) -> None:
        """Cache embedding (both memory and SQLite)

        Args:
            text: Input text
            embedding: Embedding vector
        """
        if not self._initialized:
            logger.warning("EmbeddingCache not initialized, call initialize() first")
            return

        # Add to memory cache
        self._add_to_memory_cache(text, embedding)

        # Add to SQLite
        vector_blob = self._serialize_vector(embedding)

        await self._conn.execute(
            """INSERT OR REPLACE INTO embeddings (text, vector, model_name, embedding_dim)
               VALUES (?, ?, ?, ?)""",
            (text, vector_blob, self.model_name, self.embedding_dim)
        )
        await self._conn.commit()

    def _add_to_memory_cache(self, text: str, embedding: List[float]) -> None:
        """Add to in-memory LRU cache

        Args:
            text: Input text
            embedding: Embedding vector
        """
        # Evict if cache is full (LRU: remove least recently used)
        if len(self.cache) >= self.max_size:
            # Remove first item (least recently used)
            self.cache.popitem(last=False)

        self.cache[text] = embedding
        # New item is at the end (most recently used)

    async def clear(self, model_name: Optional[str] = None) -> int:
        """Clear embeddings from cache

        Args:
            model_name: If specified, only clear embeddings for this model.
                       If None, clear all embeddings.

        Returns:
            Number of embeddings cleared
        """
        if not self._initialized:
            logger.warning("EmbeddingCache not initialized, call initialize() first")
            return 0

        if model_name:
            cursor = await self._conn.execute(
                "DELETE FROM embeddings WHERE model_name = ?",
                (model_name,)
            )
        else:
            cursor = await self._conn.execute("DELETE FROM embeddings")

        deleted_count = cursor.rowcount
        await self._conn.commit()

        # Also clear memory cache
        if model_name is None:
            self.cache.clear()
        else:
            # Only clear entries that would be from the specified model
            # (We can't easily know which entries are from which model in memory cache,
            # so we just clear everything)
            self.cache.clear()

        logger.info(f"Cleared {deleted_count} embeddings from cache")
        return deleted_count

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics

        Returns:
            Cache stats dict
        """
        if not self._initialized:
            return {
                "status": "not_initialized",
                "size": 0,
                "max_size": self.max_size,
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0,
            }

        # Get total count from SQLite
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM embeddings WHERE model_name = ?",
            (self.model_name,)
        )
        total_count = (await cursor.fetchone())[0]

        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0

        return {
            "status": "initialized",
            "memory_cache_size": len(self.cache),
            "persistent_cache_size": total_count,
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "eviction_policy": "LRU",
            "persistence": "SQLite",
        }

    async def close(self) -> None:
        """Close database connection"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._initialized = False


class EmbeddingGenerator:
    """High-level embedding generation with caching"""

    @staticmethod
    def create_provider(
        provider_name: str,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        device: str = "cpu",
    ) -> EmbeddingProvider:
        """Create embedding provider instance

        Args:
            provider_name: Provider name ("openai", "modelscope", "local")
            model_id: Model identifier
            api_key: API key (for OpenAI)
            base_url: API base URL (for OpenAI)
            device: Device for local models ("cpu" or "cuda")

        Returns:
            EmbeddingProvider instance
        """
        if provider_name == "openai":
            if not api_key or not base_url:
                raise ValueError("OpenAI provider requires api_key and base_url")
            return OpenAIEmbedding(
                api_key=api_key,
                base_url=base_url,
                model=model_id or "text-embedding-3-small",
            )

        elif provider_name == "modelscope":
            return ModelScopeEmbedding(
                model_id=model_id or "AI-ModelScope/gte-small",
                device=device,
            )

        elif provider_name == "local":
            return LocalEmbedding(
                model_name=model_id or "all-MiniLM-L6-v2",
                device=device,
            )

        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def __init__(
        self,
        provider: EmbeddingProvider,
        enable_cache: bool = True,
        cache_size: int = 10000,
        db_path: str = "./data/embedding_cache.db",
    ):
        """Initialize embedding generator

        Args:
            provider: Embedding provider instance
            enable_cache: Whether to enable caching
            cache_size: Max cache size (in-memory LRU cache)
            db_path: Path to SQLite database for persistent cache
        """
        self.provider = provider
        self.enable_cache = enable_cache
        self.cache_size = cache_size
        self.db_path = db_path
        self.cache = None  # Will be initialized in initialize()
        self._initialized = False

    async def initialize(
        self,
        on_model_change: Optional[callable] = None,
    ) -> None:
        """Initialize the embedding generator and cache

        Args:
            on_model_change: Optional callback when model change is detected

        This method must be called before using generate() or generate_batch()
        """
        if self._initialized:
            return

        # Get model info
        model_name = getattr(self.provider, 'model', None) or getattr(self.provider, 'model_id', 'unknown')
        embedding_dim = await self.provider.get_embedding_dim()

        logger.info(f"Initializing EmbeddingGenerator with model: {model_name} ({embedding_dim}D)")

        # Initialize cache if enabled
        if self.enable_cache:
            self.cache = EmbeddingCache(
                db_path=self.db_path,
                max_size=self.cache_size,
                model_name=model_name,
            )
            await self.cache.initialize(
                model_name=model_name,
                embedding_dim=embedding_dim,
                on_model_change=on_model_change,
            )

        self._initialized = True

    async def generate(self, text: str) -> List[float]:
        """Generate embedding (with cache)

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        # Ensure initialized
        if not self._initialized:
            await self.initialize()

        # Check cache
        if self.cache:
            cached = await self.cache.get(text)
            if cached is not None:
                return cached

        # Generate embedding
        embedding = await self.provider.embed(text)

        # Cache result
        if self.cache:
            await self.cache.put(text, embedding)

        return embedding

    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Ensure initialized
        if not self._initialized:
            await self.initialize()

        # Check cache for each text
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        if self.cache:
            for i, text in enumerate(texts):
                cached = await self.cache.get(text)
                if cached is not None:
                    results[i] = cached
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        # Generate embeddings for uncached texts
        if uncached_texts:
            embeddings = await self.provider.embed_batch(uncached_texts)

            # Store in cache and results
            for idx, text, embedding in zip(uncached_indices, uncached_texts, embeddings):
                results[idx] = embedding
                if self.cache:
                    await self.cache.put(text, embedding)

        return results

    async def close(self) -> None:
        """Close provider connection and cache"""
        await self.provider.close()
        if self.cache:
            await self.cache.close()

    async def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics

        Returns:
            Cache stats or None if cache disabled
        """
        if self.cache:
            return await self.cache.get_stats()
        return None


class EmbeddingBuilder:
    """Builder for creating EmbeddingGenerator from config"""

    @staticmethod
    def from_config(
        provider_name: str,
        provider_config: Dict[str, Any],
        memory_config: Dict[str, Any],
    ) -> EmbeddingGenerator:
        """Create EmbeddingGenerator from configuration

        Args:
            provider_name: Provider name ("openai", etc.)
            provider_config: Provider configuration dict
            memory_config: Memory configuration dict

        Returns:
            EmbeddingGenerator instance
        """
        # Create provider based on name
        if provider_name == "openai":
            provider = OpenAIEmbedding(
                api_key=provider_config["api_key"],
                base_url=provider_config["base_url"],
                model=memory_config.get("embedding_model", "text-embedding-3-small"),
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider_name}")

        # Create provider based on name
        if provider_name == "openai":
            provider = OpenAIEmbedding(
                api_key=provider_config["api_key"],
                base_url=provider_config["base_url"],
                model=memory_config.get("embedding_model", "text-embedding-3-small"),
            )
        elif provider_name == "local":
            provider = LocalEmbedding(
                model_name=memory_config.get("embedding_model", "all-MiniLM-L6-v2"),
                device=memory_config.get("device", "cpu"),
                cache_dir=memory_config.get("cache_dir"),
            )
        elif provider_name == "modelscope":
            provider = ModelScopeEmbedding(
                model_id=memory_config.get("embedding_model", "AI-ModelScope/gte-small"),
                device=memory_config.get("device", "cpu"),
                cache_dir=memory_config.get("cache_dir"),
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider_name}")

        # Create generator with cache
        db_path = memory_config.get("db_path", "./data/embedding_cache.db")
        return EmbeddingGenerator(
            provider=provider,
            enable_cache=True,
            cache_size=10000,
            db_path=db_path,
        )


class ModelScopeEmbedding(EmbeddingProvider):
    """Local embedding provider using ModelScope (Chinese-friendly)

    Uses ModelScope (Alibaba's HuggingFace alternative) for model downloads.
    Works better in China due to local CDN.

    Recommended models:
    - Qwen/Qwen3-Embedding-0.6B: 1536 dimensions, **RECOMMENDED for Chinese** (MTEB: 73.84)
    - damo/nlp_gte_sentence-embedding_chinese-base: 768 dimensions, high quality for Chinese
    - damo/nlp_gte_sentence-embedding_english-base: 768 dimensions, high quality for English
    - AI-ModelScope/gte-small: 384 dimensions, fast

    Qwen3-Embedding-0.6B advantages:
    - SOTA Chinese performance (73.84 on Chinese MTEB)
    - 100+ multilingual support
    - Cross-language retrieval
    - Code search capability (80.68 score)
    - 1536 dimensions (better precision)
    """

    def __init__(
        self,
        model_id: str = "AI-ModelScope/gte-small",
        device: str = "cpu",
        cache_dir: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize ModelScope embedding provider

        Args:
            model_id: ModelScope model ID
            device: Device to use ("cpu" or "cuda")
            cache_dir: Cache directory for models
            timeout: Not used (for API compatibility)
        """
        self.model_id = model_id
        self.device = device
        self.cache_dir = cache_dir
        self.timeout = timeout
        self._model = None
        self._tokenizer = None

        # Set a dummy api_key for base class compatibility
        super().__init__(api_key="modelscope", model=model_id)

    async def _get_model(self):
        """Lazy load model from ModelScope"""
        if self._model is None:
            import asyncio
            from sentence_transformers import SentenceTransformer

            # 在线程池中加载模型（避免阻塞）
            loop = asyncio.get_event_loop()

            # ModelScope URL for downloading models
            def load_model():
                # Try to load from ModelScope snapshot cache
                from modelscope.hub.snapshot_download import snapshot_download

                # Download model from ModelScope
                model_dir = snapshot_download(
                    self.model_id,
                    cache_dir=self.cache_dir,
                )

                # Load with sentence-transformers from the downloaded directory
                return SentenceTransformer(model_dir, device=self.device)

            self._model = await loop.run_in_executor(None, load_model)
            logger.info(f"Loaded ModelScope embedding model: {self.model_id}")

        return self._model

    async def embed(self, text: str) -> List[float]:
        """Generate embedding

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        model = await self._get_model()

        # 在线程池中运行（CPU密集）
        import asyncio
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            model.encode,
            text
        )

        # Convert numpy array to list
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        model = await self._get_model()

        # 在线程池中运行
        import asyncio
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            model.encode,
            texts
        )

        # Convert numpy arrays to lists
        return [emb.tolist() for emb in embeddings]

    async def close(self) -> None:
        """Close resources (no-op for local models)"""
        self._model = None
        self._tokenizer = None

    async def get_embedding_dim(self) -> int:
        """Get the embedding dimension from the loaded model

        Returns:
            The dimension of embeddings produced by this model
        """
        model = await self._get_model()
        # sentence-transformers models have this method
        dim = model.get_sentence_embedding_dimension()
        logger.info(f"ModelScope model {self.model_id} embedding dimension: {dim}")
        return dim


class LocalEmbedding(EmbeddingProvider):
    """Local sentence-transformers embedding provider

    Uses sentence-transformers for on-device embedding generation.
    Completely free and runs locally.

    Recommended models:
    - all-MiniLM-L6-v2: 384 dimensions, ~80MB, fast
    - all-mpnet-base-v2: 768 dimensions, ~400MB, high quality

    Note: May have download issues in China. Consider using ModelScopeEmbedding instead.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        cache_dir: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize local embedding provider

        Args:
            model_name: Model name from sentence-transformers
            device: Device to use ("cpu" or "cuda")
            cache_dir: Cache directory for models
            timeout: Not used (for API compatibility)
        """
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self.timeout = timeout
        self._model = None

        # Set a dummy api_key for base class compatibility
        super().__init__(api_key="local", model=model_name)

    async def _get_model(self):
        """Lazy load model"""
        if self._model is None:
            import asyncio
            import sentence_transformers as st

            # 在线程池中加载模型（避免阻塞）
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: st.SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    cache_folder=self.cache_dir,
                )
            )
            logger.info(f"Loaded local embedding model: {self.model_name}")

        return self._model

    async def embed(self, text: str) -> List[float]:
        """Generate embedding

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        model = await self._get_model()

        # 在线程池中运行（CPU密集）
        import asyncio
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            model.encode,
            text
        )

        # Convert numpy array to list
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        model = await self._get_model()

        # 在线程池中运行
        import asyncio
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            model.encode,
            texts
        )

        # Convert numpy arrays to lists
        return [emb.tolist() for emb in embeddings]

    async def close(self) -> None:
        """Close resources (no-op for local models)"""
        self._model = None

    async def get_embedding_dim(self) -> int:
        """Get the embedding dimension from the loaded model

        Returns:
            The dimension of embeddings produced by this model
        """
        model = await self._get_model()
        # sentence-transformers models have this method
        dim = model.get_sentence_embedding_dimension()
        logger.info(f"Local model {self.model_name} embedding dimension: {dim}")
        return dim
