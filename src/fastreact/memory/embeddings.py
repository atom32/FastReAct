"""
Embedding generation module

Supports multiple embedding providers for vector search.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx

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


class EmbeddingCache:
    """Simple in-memory cache for embeddings"""

    def __init__(self, max_size: int = 10000):
        """Initialize cache

        Args:
            max_size: Maximum number of cached embeddings
        """
        self.cache: Dict[str, List[float]] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding

        Args:
            text: Input text

        Returns:
            Embedding vector or None
        """
        if text in self.cache:
            self.hits += 1
            return self.cache[text]
        self.misses += 1
        return None

    def put(self, text: str, embedding: List[float]) -> None:
        """Cache embedding

        Args:
            text: Input text
            embedding: Embedding vector
        """
        # Evict if cache is full
        if len(self.cache) >= self.max_size:
            # Simple FIFO: remove first item
            self.cache.pop(next(iter(self.cache)))

        self.cache[text] = embedding

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics

        Returns:
            Cache stats dict
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


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
    ):
        """Initialize embedding generator

        Args:
            provider: Embedding provider instance
            enable_cache: Whether to enable caching
            cache_size: Max cache size
        """
        self.provider = provider
        self.enable_cache = enable_cache
        self.cache = EmbeddingCache(max_size=cache_size) if enable_cache else None

    async def generate(self, text: str) -> List[float]:
        """Generate embedding (with cache)

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        # Check cache
        if self.cache:
            cached = self.cache.get(text)
            if cached is not None:
                return cached

        # Generate embedding
        embedding = await self.provider.embed(text)

        # Cache result
        if self.cache:
            self.cache.put(text, embedding)

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

        # Check cache for each text
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        if self.cache:
            for i, text in enumerate(texts):
                cached = self.cache.get(text)
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
                    self.cache.put(text, embedding)

        return results

    async def close(self) -> None:
        """Close provider connection"""
        await self.provider.close()

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics

        Returns:
            Cache stats or None if cache disabled
        """
        if self.cache:
            return self.cache.get_stats()
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
        return EmbeddingGenerator(
            provider=provider,
            enable_cache=True,
            cache_size=10000,
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
