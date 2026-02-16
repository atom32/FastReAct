"""
SQLite + sqlite-vec vector storage

Implements vector storage using SQLite with the sqlite-vec extension.
"""

import asyncio
import aiosqlite
import json
import logging
import sys
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import apsw for Windows compatibility
try:
    import apsw
    APSW_AVAILABLE = True
    logger.info("apsw available for Windows sqlite-vec support")
except ImportError:
    APSW_AVAILABLE = False
    logger.debug("apsw not available, will use aiosqlite")


class SQLiteVecStore:
    """Vector store using SQLite + sqlite-vec extension

    Stores document chunks with embeddings for semantic search.
    """

    def __init__(
        self,
        db_path: str = "./data/memory.db",
        embedding_dim: int = 1536,  # Default for text-embedding-3-small
    ):
        """Initialize SQLite vector store

        Args:
            db_path: Path to SQLite database
            embedding_dim: Embedding vector dimension
        """
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize database and create tables

        Loads sqlite-vec extension and creates necessary tables.
        Uses apsw on Windows for extension loading compatibility.
        """
        # Ensure data directory exists
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # On Windows, use apsw for extension loading
        if sys.platform == "win32" and APSW_AVAILABLE:
            await self._initialize_apsw()
        else:
            await self._initialize_aiosqlite()

    async def _initialize_apsw(self) -> None:
        """Initialize using apsw (Windows)

        apsw can load sqlite-vec extensions on Windows using absolute paths.
        """
        import apsw
        import sqlite_vec
        import site

        # Find vec0.dll absolute path
        module_dir = os.path.dirname(sqlite_vec.__file__)
        vec_dll_path = os.path.join(module_dir, "vec0.dll")

        if not os.path.exists(vec_dll_path):
            raise RuntimeError(
                f"sqlite-vec extension not found at {vec_dll_path}. "
                "Make sure sqlite-vec is installed: pip install sqlite-vec"
            )

        logger.info(f"Using apsw with sqlite-vec extension at: {vec_dll_path}")

        # Create connection and enable extensions
        conn = apsw.Connection(self.db_path)
        conn.enableloadextension(True)

        # Load extension with absolute path
        try:
            conn.loadextension(vec_dll_path)
            logger.info("sqlite-vec extension loaded successfully (apsw + absolute path)")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load sqlite-vec extension: {e}. "
                "Ensure vec0.dll exists and is accessible."
            )

        # Create tables
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'chat',
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create chunks table with embedding
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Create vector index for similarity search
        cursor.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks
            USING vec0(
                embedding float[{self.embedding_dim}]
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_session_id
            ON documents(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_session_id
            ON chunks(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id
            ON chunks(doc_id)
        """)

        # Close connection (apsw doesn't need async)
        # Note: For apsw, we'll need to handle connections differently

        logger.info(f"SQLiteVecStore initialized (apsw): {self.db_path}")

    async def _initialize_aiosqlite(self) -> None:
        """Initialize using aiosqlite (Linux/Mac)

        Loads sqlite-vec extension and creates necessary tables.
        """
        # Ensure data directory exists
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")

            # Load sqlite-vec extension
            # Try multiple methods for Windows compatibility
            extension_loaded = False

            # Method 1: Direct load
            try:
                await db.execute("SELECT load_extension('sqlite_vec')")
                logger.info("sqlite-vec extension loaded successfully (direct load)")
                extension_loaded = True
            except aiosqlite.Error as e:
                logger.debug(f"Direct load failed: {e}")

            # Method 2: Try with absolute path (Windows)
            if not extension_loaded:
                try:
                    import sqlite_vec
                    ext_path = sqlite_vec.__file__
                    await db.execute(f"SELECT load_extension('{ext_path}')")
                    logger.info(f"sqlite-vec extension loaded successfully (path: {ext_path})")
                    extension_loaded = True
                except Exception as e:
                    logger.debug(f"Path load failed: {e}")

            # Method 3: Enable extension loading
            if not extension_loaded:
                try:
                    # On Windows, might need to enable extension loading
                    import sys
                    if sys.platform == "win32":
                        # Try enabling extensions
                        await db.execute("PRAGMA enable_load_extension=1")
                        await db.execute("SELECT load_extension('sqlite_vec')")
                        logger.info("sqlite-vec extension loaded successfully (Windows mode)")
                        extension_loaded = True
                except Exception as e:
                    logger.debug(f"Windows load failed: {e}")

            if not extension_loaded:
                logger.error("Failed to load sqlite-vec extension")
                logger.error("Troubleshooting:")
                logger.error("1. Make sure sqlite-vec is installed: pip install sqlite-vec")
                logger.error("2. On Windows, run Python as Administrator")
                logger.error("3. Or use an alternative vector store (chromadb, weaviate)")
                raise RuntimeError("sqlite-vec extension not available")

            # Create documents table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'chat',
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create chunks table with embedding
            await db.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            # Create vector index for similarity search
            # sqlite-vec uses a special virtual table for vector search
            await db.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks
                USING vec0(
                    embedding float[{self.embedding_dim}]
                )
            """)

            # Create indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_session_id
                ON documents(session_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_session_id
                ON chunks(session_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_doc_id
                ON chunks(doc_id)
            """)

            await db.commit()

            logger.info(f"SQLiteVecStore initialized: {self.db_path}")

    async def add_document(
        self,
        doc_id: str,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document

        Args:
            doc_id: Document ID
            session_id: Session ID
            content: Document content
            metadata: Optional metadata
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO documents (id, session_id, source, content, metadata, updated_at)
                VALUES (?, ?, 'chat', ?, ?, CURRENT_TIMESTAMP)
            """, (
                doc_id,
                session_id,
                content,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            await db.commit()

    async def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> None:
        """Add document chunks with embeddings

        Args:
            chunks: List of chunk dicts with keys:
                - id: chunk ID
                - doc_id: document ID
                - session_id: session ID
                - chunk_index: chunk index
                - content: chunk content
                - embedding: embedding vector (list of floats)
                - metadata: optional metadata
        """
        async with aiosqlite.connect(self.db_path) as db:
            for chunk in chunks:
                # Convert embedding list to blob
                import struct
                embedding = chunk["embedding"]
                embedding_blob = struct.pack(f"{len(embedding)}f", *embedding)

                await db.execute("""
                    INSERT OR REPLACE INTO chunks
                    (id, doc_id, session_id, chunk_index, content, embedding, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk["id"],
                    chunk["doc_id"],
                    chunk["session_id"],
                    chunk["chunk_index"],
                    chunk["content"],
                    embedding_blob,
                    json.dumps(chunk.get("metadata", {}), ensure_ascii=False)
                ))

            # Update vector table
            # Note: sqlite-vec's vec0 table is automatically updated
            # when we use the vec_search() function

            await db.commit()

            logger.debug(f"Added {len(chunks)} chunks to vector store")

    async def search(
        self,
        query_embedding: List[float],
        session_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Semantic similarity search

        Args:
            query_embedding: Query embedding vector
            session_id: Optional session ID filter
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (cosine)

        Returns:
            List of search results with keys:
                - id: chunk ID
                - session_id: session ID
                - content: chunk content
                - similarity: similarity score
                - metadata: chunk metadata
        """
        import struct

        # Convert query embedding to blob
        query_blob = struct.pack(f"{len(query_embedding)}f", *query_embedding)

        async with aiosqlite.connect(self.db_path) as db:
            # Build query with optional session filter
            if session_id:
                where_clause = "AND c.session_id = ?"
                params = (query_blob, top_k, session_id, top_k)
            else:
                where_clause = ""
                params = (query_blob, top_k, top_k)

            # Use sqlite-vec's vec_search function
            # Note: vec0 requires explicit k parameter for KNN search
            query = f"""
                SELECT
                    c.id,
                    c.session_id,
                    c.content,
                    c.metadata,
                    distance
                FROM vec_chunks
                JOIN chunks c ON vec_chunks.rowid = c.rowid
                WHERE vec_chunks.embedding MATCH ?
                  AND k = ?
                  {where_clause}
                ORDER BY distance
                LIMIT ?
            """

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

            results = []
            for row in rows:
                similarity = 1.0 - row[4]  # Convert distance to similarity
                results.append({
                    "id": row[0],
                    "session_id": row[1],
                    "content": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "similarity": similarity,
                })

            logger.debug(f"Vector search returned {len(results)} results")

            return results

    async def get_session_chunks(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a session

        Args:
            session_id: Session ID
            limit: Maximum number of chunks

        Returns:
            List of chunks
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, doc_id, session_id, chunk_index, content, metadata
                FROM chunks
                WHERE session_id = ?
                ORDER BY chunk_index
                LIMIT ?
            """, (session_id, limit)) as cursor:
                rows = await cursor.fetchall()

            chunks = []
            for row in rows:
                chunks.append({
                    "id": row[0],
                    "doc_id": row[1],
                    "session_id": row[2],
                    "chunk_index": row[3],
                    "content": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {},
                })

            return chunks

    async def delete_session(self, session_id: str) -> int:
        """Delete all data for a session

        Args:
            session_id: Session ID

        Returns:
            Number of chunks deleted
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Delete documents (will cascade to chunks)
            cursor = await db.execute(
                "DELETE FROM documents WHERE session_id = ?",
                (session_id,)
            )
            await db.commit()

            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted} documents for session {session_id}")

            return deleted

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics

        Returns:
            Statistics dict
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Count documents
            async with db.execute(
                "SELECT COUNT(*) FROM documents"
            ) as cursor:
                doc_count = (await cursor.fetchone())[0]

            # Count chunks
            async with db.execute(
                "SELECT COUNT(*) FROM chunks"
            ) as cursor:
                chunk_count = (await cursor.fetchone())[0]

            # Count sessions
            async with db.execute(
                "SELECT COUNT(DISTINCT session_id) FROM documents"
            ) as cursor:
                session_count = (await cursor.fetchone())[0]

            return {
                "total_documents": doc_count,
                "total_chunks": chunk_count,
                "total_sessions": session_count,
                "embedding_dim": self.embedding_dim,
            }


class APSWVecStore:
    """Vector store using apsw + sqlite-vec (Windows compatible)

    Uses apsw (Another Python SQLite Wrapper) which can load
    sqlite-vec extensions on Windows using absolute paths.

    This solves the Windows compatibility issue where standard
    sqlite3 module cannot load extensions due to permissions.
    """

    def __init__(
        self,
        db_path: str = "./data/memory.db",
        embedding_dim: int = 1536,  # Default for text-embedding-3-small
    ):
        """Initialize APSW SQLite vector store

        Args:
            db_path: Path to SQLite database
            embedding_dim: Embedding vector dimension
        """
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self._lock = asyncio.Lock()
        self._conn = None

    async def _get_connection(self):
        """Get or create apsw connection (thread-safe with lock)"""
        if self._conn is None:
            import apsw

            self._conn = apsw.Connection(self.db_path)
            self._conn.enableloadextension(True)

            # Load sqlite-vec extension
            import sqlite_vec
            import os

            module_dir = os.path.dirname(sqlite_vec.__file__)
            vec_dll_path = os.path.join(module_dir, "vec0.dll")

            if not os.path.exists(vec_dll_path):
                raise RuntimeError(
                    f"sqlite-vec extension not found at {vec_dll_path}"
                )

            self._conn.loadextension(vec_dll_path)
            logger.info(f"Loaded sqlite-vec from: {vec_dll_path}")

        return self._conn

    async def initialize(self) -> None:
        """Initialize database and create tables"""
        # Ensure data directory exists
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        async with self._lock:
            conn = await self._get_connection()
            cursor = conn.cursor()

            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")

            # Create documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'chat',
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create chunks table with embedding
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            # Create vector index for similarity search
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks
                USING vec0(
                    embedding float[{self.embedding_dim}]
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_session_id
                ON documents(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_session_id
                ON chunks(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_doc_id
                ON chunks(doc_id)
            """)

            logger.info(f"APSWVecStore initialized: {self.db_path}")

    async def add_document(
        self,
        doc_id: str,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document"""
        async with self._lock:
            conn = await self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO documents (id, session_id, source, content, metadata, updated_at)
                VALUES (?, ?, 'chat', ?, ?, CURRENT_TIMESTAMP)
            """, (
                doc_id,
                session_id,
                content,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))

    async def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> None:
        """Add document chunks with embeddings"""
        import struct

        async with self._lock:
            conn = await self._get_connection()
            cursor = conn.cursor()

            for chunk in chunks:
                # Convert embedding list to blob
                embedding = chunk["embedding"]
                embedding_blob = struct.pack(f"{len(embedding)}f", *embedding)

                # Insert into chunks table
                cursor.execute("""
                    INSERT OR REPLACE INTO chunks
                    (id, doc_id, session_id, chunk_index, content, embedding, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk["id"],
                    chunk["doc_id"],
                    chunk["session_id"],
                    chunk["chunk_index"],
                    chunk["content"],
                    embedding_blob,
                    json.dumps(chunk.get("metadata", {}), ensure_ascii=False)
                ))

                # Insert into vec_chunks table for vector search
                # Delete existing row if any, then insert
                cursor.execute("""
                    DELETE FROM vec_chunks WHERE rowid = (SELECT rowid FROM chunks WHERE id = ?)
                """, (chunk["id"],))

                cursor.execute("""
                    INSERT INTO vec_chunks(rowid, embedding)
                    VALUES (
                        (SELECT rowid FROM chunks WHERE id = ?),
                        ?
                    )
                """, (chunk["id"], embedding_blob))

            logger.debug(f"Added {len(chunks)} chunks to vector store")

    async def search(
        self,
        query_embedding: List[float],
        session_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Semantic similarity search"""
        import struct

        # Convert query embedding to blob
        query_blob = struct.pack(f"{len(query_embedding)}f", *query_embedding)

        async with self._lock:
            conn = await self._get_connection()
            cursor = conn.cursor()

            # Build query with optional session filter
            if session_id:
                where_clause = "AND c.session_id = ?"
                params = (query_blob, top_k, session_id, top_k)
            else:
                where_clause = ""
                params = (query_blob, top_k, top_k)

            # Use sqlite-vec's vec_search function
            # Note: vec0 requires explicit k parameter for KNN search
            query = f"""
                SELECT
                    c.id,
                    c.session_id,
                    c.content,
                    c.metadata,
                    distance
                FROM vec_chunks
                JOIN chunks c ON vec_chunks.rowid = c.rowid
                WHERE vec_chunks.embedding MATCH ?
                  AND k = ?
                  {where_clause}
                ORDER BY distance
                LIMIT ?
            """

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                similarity = 1.0 - row[4]  # Convert distance to similarity
                results.append({
                    "id": row[0],
                    "session_id": row[1],
                    "content": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "similarity": similarity,
                })

            logger.debug(f"Vector search returned {len(results)} results")

            return results

    async def get_session_chunks(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a session"""
        async with self._lock:
            conn = await self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, doc_id, session_id, chunk_index, content, metadata
                FROM chunks
                WHERE session_id = ?
                ORDER BY chunk_index
                LIMIT ?
            """, (session_id, limit))

            rows = cursor.fetchall()

            chunks = []
            for row in rows:
                chunks.append({
                    "id": row[0],
                    "doc_id": row[1],
                    "session_id": row[2],
                    "chunk_index": row[3],
                    "content": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {},
                })

            return chunks

    async def delete_session(self, session_id: str) -> int:
        """Delete all data for a session"""
        async with self._lock:
            conn = await self._get_connection()
            cursor = conn.cursor()

            # Delete documents (will cascade to chunks)
            cursor.execute(
                "DELETE FROM documents WHERE session_id = ?",
                (session_id,)
            )

            # apsw doesn't have rowcount, get it manually
            cursor.execute("SELECT changes()")
            deleted = cursor.fetchone()[0]
            logger.info(f"Deleted {deleted} documents for session {session_id}")

            return deleted

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        async with self._lock:
            conn = await self._get_connection()
            cursor = conn.cursor()

            # Count documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]

            # Count chunks
            cursor.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cursor.fetchone()[0]

            # Count sessions
            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM documents")
            session_count = cursor.fetchone()[0]

            return {
                "total_documents": doc_count,
                "total_chunks": chunk_count,
                "total_sessions": session_count,
                "embedding_dim": self.embedding_dim,
            }

    async def close(self) -> None:
        """Close the connection"""
        async with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                logger.info("APSWVecStore connection closed")
