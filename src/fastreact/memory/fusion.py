"""
Rank Fusion Algorithms

Implements various methods for combining ranked search results from multiple retrieval methods.
Includes Reciprocal Rank Fusion (RRF) and weighted score fusion.
"""

import math
from typing import List, Dict, Any, Optional, Set
import logging

logger = logging.getLogger(__name__)


class ReciprocalRankFusion:
    """Reciprocal Rank Fusion (RRF) algorithm

    RRF combines ranked results from multiple retrieval methods without requiring
    score normalization. It's robust to different score scales and outliers.

    Reference: Cormack et al. (2009) - Reciprocal Rank Fusion outperforms Condorcet
    and individual Rank Learning Methods
    """

    def __init__(
        self,
        k: int = 60,
    ):
        """Initialize RRF fusion

        Args:
            k: Constant to prevent rank from dominating score (default 60)
               - Higher = ranks have less impact
               - Lower = top ranks are more important
        """
        self.k = k
        logger.info(f"RRF fusion initialized: k={k}")

    def fuse(
        self,
        ranked_lists: List[List[Dict[str, Any]]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fuse multiple ranked result lists using RRF

        Args:
            ranked_lists: List of ranked results from different methods
                         Each list contains dicts with "doc_id" field
            top_k: Number of top results to return (None = all)

        Returns:
            Fused and re-ranked results
        """
        if not ranked_lists:
            return []

        # Calculate RRS (Reciprocal Rank Score) for each document
        rrs_scores: Dict[str, float] = {}
        doc_data: Dict[str, Dict[str, Any]] = {}

        for method_idx, ranked_list in enumerate(ranked_lists):
            for rank, result in enumerate(ranked_list, start=1):
                doc_id = result.get("doc_id")
                if not doc_id:
                    continue

                # RRF formula: 1 / (k + rank)
                contribution = 1.0 / (self.k + rank)

                # Accumulate score
                if doc_id not in rrs_scores:
                    rrs_scores[doc_id] = 0.0
                    doc_data[doc_id] = result.copy()
                    doc_data[doc_id]["rank_positions"] = []

                rrs_scores[doc_id] += contribution
                doc_data[doc_id]["rank_positions"].append({
                    "method": method_idx,
                    "rank": rank,
                })

        # Build fused results
        fused_results = []
        for doc_id, rrs_score in rrs_scores.items():
            result = doc_data[doc_id]
            result["rrf_score"] = round(rrs_score, 4)
            result["fusion_method"] = "rrf"
            fused_results.append(result)

        # Sort by RRF score (descending)
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)

        # Return top-k
        if top_k:
            fused_results = fused_results[:top_k]

        logger.debug(f"RRF fused {len(ranked_lists)} ranked lists into {len(fused_results)} results")

        return fused_results


class WeightedFusion:
    """Weighted score fusion algorithm

    Combines results from multiple retrieval methods using weighted scores.
    Requires score normalization to handle different scales.
    """

    def __init__(
        self,
        weights: Optional[List[float]] = None,
        normalization: str = "minmax",
    ):
        """Initialize weighted fusion

        Args:
            weights: List of weights for each method (default: equal weights)
            normalization: Score normalization method
                          - "minmax": Scale to [0, 1]
                          - "zscore": Standard score (mean=0, std=1)
                          - "sigmoid": Sigmoid transformation
        """
        self.weights = weights
        self.normalization = normalization
        logger.info(f"Weighted fusion initialized: weights={weights}, normalization={normalization}")

    def _normalize_scores(
        self,
        results: List[Dict[str, Any]],
        method: str = "minmax",
    ) -> List[Dict[str, Any]]:
        """Normalize scores in results

        Args:
            results: List of results with "score" field
            method: Normalization method

        Returns:
            Results with normalized scores
        """
        if not results:
            return results

        scores = [r.get("score", 0.0) for r in results]

        if method == "minmax":
            # Min-max normalization: (x - min) / (max - min)
            min_score = min(scores)
            max_score = max(scores)

            if max_score == min_score:
                # All scores are the same
                normalized = [1.0] * len(scores)
            else:
                normalized = [
                    (s - min_score) / (max_score - min_score)
                    for s in scores
                ]

        elif method == "zscore":
            # Z-score normalization: (x - mean) / std
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            std_score = math.sqrt(variance)

            if std_score == 0:
                normalized = [0.0] * len(scores)
            else:
                normalized = [
                    (s - mean_score) / std_score
                    for s in scores
                ]

        elif method == "sigmoid":
            # Sigmoid: 1 / (1 + exp(-x))
            normalized = [
                1.0 / (1.0 + math.exp(-s))
                for s in scores
            ]

        else:
            logger.warning(f"Unknown normalization method: {method}, using raw scores")
            normalized = scores

        # Update results with normalized scores
        for result, norm_score in zip(results, normalized):
            result["_normalized_score"] = norm_score

        return results

    def fuse(
        self,
        result_lists: List[List[Dict[str, Any]]],
        weights: Optional[List[float]] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fuse multiple result lists using weighted scores

        Args:
            result_lists: List of result lists from different methods
            weights: Override weights (optional)
            top_k: Number of top results to return (None = all)

        Returns:
            Fused and re-ranked results
        """
        if not result_lists:
            return []

        # Use provided weights or default
        if weights is None:
            weights = self.weights

        if weights is None:
            # Equal weights
            weights = [1.0 / len(result_lists)] * len(result_lists)

        # Validate weights
        if len(weights) != len(result_lists):
            raise ValueError(f"Number of weights ({len(weights)}) must match number of result lists ({len(result_lists)})")

        # Normalize scores for each method
        normalized_lists = []
        for results in result_lists:
            normalized = self._normalize_scores(
                [r.copy() for r in results],
                method=self.normalization,
            )
            normalized_lists.append(normalized)

        # Calculate weighted scores
        fused_scores: Dict[str, float] = {}
        doc_data: Dict[str, Dict[str, Any]] = {}

        for method_idx, results in enumerate(normalized_lists):
            weight = weights[method_idx]

            for result in results:
                doc_id = result.get("doc_id")
                if not doc_id:
                    continue

                norm_score = result.get("_normalized_score", 0.0)
                weighted_score = weight * norm_score

                if doc_id not in fused_scores:
                    fused_scores[doc_id] = 0.0
                    doc_data[doc_id] = result.copy()
                    doc_data[doc_id]["method_scores"] = []

                fused_scores[doc_id] += weighted_score
                doc_data[doc_id]["method_scores"].append({
                    "method": method_idx,
                    "weight": weight,
                    "normalized_score": norm_score,
                    "weighted_score": weighted_score,
                })

        # Build fused results
        fused_results = []
        for doc_id, fused_score in fused_scores.items():
            result = doc_data[doc_id]
            result["fused_score"] = round(fused_score, 4)
            result["fusion_method"] = "weighted"
            fused_results.append(result)

        # Sort by fused score (descending)
        fused_results.sort(key=lambda x: x["fused_score"], reverse=True)

        # Return top-k
        if top_k:
            fused_results = fused_results[:top_k]

        logger.debug(f"Weighted fusion combined {len(result_lists)} result lists into {len(fused_results)} results")

        return fused_results


class HybridRetriever:
    """Hybrid retriever combining BM25 and semantic search

    Uses RRF or weighted fusion to combine results from:
    - BM25 keyword search
    - Semantic vector search
    """

    def __init__(
        self,
        bm25_retriever,
        semantic_retriever,
        fusion_method: str = "rrf",
        alpha: float = 0.5,
        rrf_k: int = 60,
    ):
        """Initialize hybrid retriever

        Args:
            bm25_retriever: BM25 retriever instance
            semantic_retriever: Semantic retriever instance (MemoryRetriever)
            fusion_method: "rrf" or "weighted"
            alpha: Weight for BM25 (0-1), semantic gets (1-alpha)
            rrf_k: RRF constant
        """
        self.bm25 = bm25_retriever
        self.semantic = semantic_retriever
        self.fusion_method = fusion_method
        self.alpha = alpha

        # Initialize fusion
        if fusion_method == "rrf":
            self.fusion = ReciprocalRankFusion(k=rrf_k)
        elif fusion_method == "weighted":
            # Weights: alpha for BM25, (1-alpha) for semantic
            weights = [alpha, 1 - alpha]
            self.fusion = WeightedFusion(weights=weights)
        else:
            raise ValueError(f"Unknown fusion method: {fusion_method}")

        logger.info(
            f"Hybrid retriever initialized: "
            f"fusion={fusion_method}, alpha={alpha}, rrf_k={rrf_k}"
        )

    async def initialize(self) -> None:
        """Initialize all retrievers"""
        await self.bm25.initialize()
        await self.semantic.initialize()
        logger.info("Hybrid retriever initialized")

    async def retrieve(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Retrieve using hybrid search

        Args:
            query: Search query
            session_id: Session ID (for semantic search)
            top_k: Number of results
            min_score: Minimum score threshold

        Returns:
            Fused results from BM25 and semantic search
        """
        # Retrieve from both methods
        bm25_results = await self.bm25.retrieve(
            query=query,
            top_k=top_k * 2,  # Get more candidates
            min_score=0.0,  # Don't filter yet
        )

        # Call semantic retriever directly to avoid hybrid mode recursion
        # Use _semantic_retrieve() to bypass hybrid mode check
        semantic_results = await self.semantic._semantic_retrieve(
            query=query,
            session_id=session_id,
        )

        logger.debug(
            f"Hybrid search: BM25={len(bm25_results)} results, "
            f"Semantic={len(semantic_results)} results"
        )

        # Fuse results
        if self.fusion_method == "rrf":
            # RRF doesn't need scores, just ranks
            fused = self.fusion.fuse(
                ranked_lists=[bm25_results, semantic_results],
                top_k=top_k * 3,  # Get more before filtering
            )
        else:  # weighted
            fused = self.fusion.fuse(
                result_lists=[bm25_results, semantic_results],
                top_k=top_k * 3,
            )

        # Filter by score and re-sort
        if self.fusion_method == "rrf":
            # RRF scores are typically 0.01-0.1 range
            filtered = [r for r in fused if r.get("rrf_score", 0) >= min_score / 100]
            filtered.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)
        else:  # weighted
            filtered = [r for r in fused if r.get("fused_score", 0) >= min_score]
            filtered.sort(key=lambda x: x.get("fused_score", 0), reverse=True)

        # Return top-k
        results = filtered[:top_k]

        # Add metadata
        for result in results:
            result["retrieval_method"] = "hybrid"
            result["hybrid_metadata"] = {
                "fusion_method": self.fusion_method,
                "alpha": self.alpha,
                "bm25_rank": None,
                "semantic_rank": None,
            }

            # Find ranks from each method
            for i, r in enumerate(bm25_results):
                if r.get("doc_id") == result.get("doc_id"):
                    result["hybrid_metadata"]["bm25_rank"] = i + 1
                    break

            for i, r in enumerate(semantic_results):
                if r.get("doc_id") == result.get("doc_id"):
                    result["hybrid_metadata"]["semantic_rank"] = i + 1
                    break

        logger.info(f"Hybrid search returned {len(results)} fused results")

        return results

    async def get_stats(self) -> Dict[str, Any]:
        """Get hybrid retriever statistics

        Returns:
            Statistics dictionary
        """
        bm25_stats = await self.bm25.get_stats()
        semantic_stats = await self.semantic.get_stats()

        return {
            "fusion_method": self.fusion_method,
            "alpha": self.alpha,
            "bm25": bm25_stats,
            "semantic": semantic_stats,
        }
