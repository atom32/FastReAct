"""
BM25 Keyword Search Implementation

Implements BM25 algorithm for keyword-based exact matching search.
Combines term frequency, inverse document frequency, and document length normalization.

Reference: Robertson & Zaragoza (2009) - The Probabilistic Relevance Framework: BM25 and Beyond
"""

import math
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Set
import logging

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25 index for keyword search"""

    def __init__(
        self,
        k1: float = 1.2,
        b: float = 0.75,
        language: str = "chinese",
    ):
        """Initialize BM25 index

        Args:
            k1: Term saturation parameter (default 1.2)
                - Higher = term frequency has more impact
                - Lower = term frequency saturates quickly
            b: Length normalization parameter (default 0.75)
                - Higher = longer documents penalized more
                - 0.0 = no length normalization
            language: Tokenization language ("chinese", "english", "mixed")
        """
        self.k1 = k1
        self.b = b
        self.language = language

        # Index structures
        self.doc_count: int = 0
        self.doc_lengths: List[int] = []  # Length of each document
        self.avgdl: float = 0.0  # Average document length

        # Term frequency: doc_id -> {term: frequency}
        self.doc_term_freqs: List[Dict[str, int]] = []

        # Document frequency: {term: number of docs containing term}
        self.doc_freqs: Dict[str, int] = defaultdict(int)

        # Document IDs to content mapping
        self.doc_ids: List[str] = []
        self.doc_contents: List[str] = []

        # Tokenizer
        self._init_tokenizer()

        logger.info(f"BM25 index initialized: k1={k1}, b={b}, language={language}")

    def _init_tokenizer(self) -> None:
        """Initialize tokenizer based on language"""
        if self.language == "chinese":
            # Simple character-based tokenization for Chinese
            # For production, consider jieba or similar
            self._tokenize = self._tokenize_chinese
        elif self.language == "english":
            # Word-based tokenization for English
            self._tokenize = self._tokenize_english
        else:  # mixed
            self._tokenize = self._tokenize_mixed

    def _tokenize_chinese(self, text: str) -> List[str]:
        """Tokenize Chinese text (character-based)"""
        # Remove punctuation and whitespace
        text = re.sub(r'[^\u4e00-\u9fff\w]', '', text)
        return list(text)  # Character-based

    def _tokenize_english(self, text: str) -> List[str]:
        """Tokenize English text (word-based)"""
        # Convert to lowercase, remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()

    def _tokenize_mixed(self, text: str) -> List[str]:
        """Tokenize mixed Chinese-English text"""
        tokens = []

        # Extract Chinese characters
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        tokens.extend(chinese_chars)

        # Extract English words
        english_words = re.findall(r'[a-zA-Z]+', text)
        tokens.extend([w.lower() for w in english_words])

        return tokens

    def add_document(
        self,
        doc_id: str,
        content: str,
    ) -> None:
        """Add a document to the index

        Args:
            doc_id: Unique document identifier
            content: Document text content
        """
        # Tokenize document
        tokens = self._tokenize(content)

        # Calculate term frequencies
        term_freqs = defaultdict(int)
        for token in tokens:
            term_freqs[token] += 1

        # Store document
        doc_idx = self.doc_count
        self.doc_ids.append(doc_id)
        self.doc_contents.append(content)
        self.doc_term_freqs.append(dict(term_freqs))
        self.doc_lengths.append(len(tokens))

        # Update document frequencies
        for term in term_freqs.keys():
            self.doc_freqs[term] += 1

        # Update statistics
        self.doc_count += 1
        self.avgdl = sum(self.doc_lengths) / self.doc_count

        logger.debug(f"Added document {doc_id}: {len(tokens)} tokens, {len(term_freqs)} unique terms")

    def add_documents(
        self,
        documents: List[Dict[str, str]],
    ) -> None:
        """Add multiple documents to the index

        Args:
            documents: List of {"doc_id": str, "content": str} dicts
        """
        for doc in documents:
            self.add_document(doc["doc_id"], doc["content"])

        logger.info(f"Added {len(documents)} documents to BM25 index")

    def _calculate_idf(
        self,
        term: str,
    ) -> float:
        """Calculate IDF (Inverse Document Frequency) for a term

        Args:
            term: Query term

        Returns:
            IDF score
        """
        df = self.doc_freqs.get(term, 0)
        if df == 0:
            return 0.0

        # Standard IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
        # Using +1 to avoid log(0)
        idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)
        return idf

    def _calculate_score(
        self,
        doc_idx: int,
        query_terms: List[str],
    ) -> float:
        """Calculate BM25 score for a document

        Args:
            doc_idx: Document index
            query_terms: Tokenized query terms

        Returns:
            BM25 score
        """
        score = 0.0
        doc_len = self.doc_lengths[doc_idx]
        term_freqs = self.doc_term_freqs[doc_idx]

        for term in query_terms:
            # Skip if term not in document
            if term not in term_freqs:
                continue

            # Get term frequency in document
            tf = term_freqs[term]

            # Calculate IDF
            idf = self._calculate_idf(term)

            # BM25 formula
            # numerator: tf * (k1 + 1)
            # denominator: tf + k1 * (1 - b + b * (doc_len / avgdl))
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))

            score += idf * (numerator / denominator)

        return score

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search for documents using BM25

        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum score threshold

        Returns:
            List of {"doc_id": str, "score": float, "content": str} results
        """
        # Tokenize query
        query_terms = self._tokenize(query)

        if not query_terms:
            logger.warning(f"Empty query after tokenization: {query}")
            return []

        logger.debug(f"Searching with {len(query_terms)} query terms: {query_terms[:10]}")

        # Calculate scores for all documents
        scores = []
        for doc_idx in range(self.doc_count):
            score = self._calculate_score(doc_idx, query_terms)
            if score >= min_score:
                scores.append({
                    "doc_idx": doc_idx,
                    "doc_id": self.doc_ids[doc_idx],
                    "score": score,
                    "content": self.doc_contents[doc_idx],
                })

        # Sort by score (descending)
        scores.sort(key=lambda x: x["score"], reverse=True)

        # Return top-k
        results = scores[:top_k]

        logger.debug(f"BM25 search returned {len(results)} results (query: {query[:50]})")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics

        Returns:
            Statistics dictionary
        """
        unique_terms = len(self.doc_freqs)
        total_terms = sum(len(tf) for tf in self.doc_term_freqs)

        return {
            "doc_count": self.doc_count,
            "avg_doc_length": round(self.avgdl, 2),
            "unique_terms": unique_terms,
            "total_terms": total_terms,
            "vocab_size": unique_terms,
            "k1": self.k1,
            "b": self.b,
            "language": self.language,
        }


class BM25Retriever:
    """High-level BM25 retriever interface"""

    def __init__(
        self,
        k1: float = 1.2,
        b: float = 0.75,
        language: str = "chinese",
        top_k: int = 5,
        min_score: float = 0.0,
    ):
        """Initialize BM25 retriever

        Args:
            k1: Term saturation parameter
            b: Length normalization parameter
            language: Tokenization language
            top_k: Default number of results
            min_score: Default minimum score threshold
        """
        self.index = BM25Index(k1=k1, b=b, language=language)
        self.top_k = top_k
        self.min_score = min_score

        logger.info(f"BM25 retriever initialized: top_k={top_k}, min_score={min_score}")

    async def initialize(self) -> None:
        """Initialize retriever (async compatibility)

        Note: BM25 is synchronous, but we provide this for compatibility
        """
        logger.info("BM25 retriever initialized (async compatibility)")

    async def index_documents(
        self,
        documents: List[Dict[str, str]],
    ) -> None:
        """Index documents

        Args:
            documents: List of {"doc_id": str, "content": str} dicts
        """
        self.index.add_documents(documents)
        logger.info(f"Indexed {len(documents)} documents in BM25 retriever")

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve documents using BM25

        Args:
            query: Search query
            top_k: Number of results (overrides default)
            min_score: Minimum score (overrides default)

        Returns:
            List of results with doc_id, score, content
        """
        top_k = top_k or self.top_k
        min_score = min_score or self.min_score

        results = self.index.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
        )

        # Add retrieval method metadata
        for result in results:
            result["retrieval_method"] = "bm25"
            result["retrieval_metadata"] = {
                "k1": self.index.k1,
                "b": self.index.b,
                "language": self.index.language,
            }

        return results

    async def delete_session(self, session_id: str) -> int:
        """Delete all documents for a session

        Note: BM25 index doesn't support deletion efficiently.
        This is a placeholder for compatibility.

        Args:
            session_id: Session ID to delete

        Returns:
            Number of documents deleted
        """
        # In a real implementation, you'd need to rebuild the index
        # For now, return 0 (not supported)
        logger.warning(f"BM25 delete not implemented for session {session_id}")
        return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics

        Returns:
            Statistics dictionary
        """
        stats = self.index.get_stats()
        stats.update({
            "top_k": self.top_k,
            "min_score": self.min_score,
        })
        return stats
