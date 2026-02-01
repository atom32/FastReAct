# Hybrid Search Design Document

## Overview

Based on Anthropic's research, hybrid search combining **BM25 keyword search** with **semantic vector search** provides superior retrieval accuracy compared to either method alone.

## Architecture

```
Query
  ├─→ BM25 Search ──────┐
  │   (Keyword/Exact)    │
  │                      ├─→ RRF Fusion ─→ Ranked Results
  └─→ Semantic Search ──┘
      (Vector/Embedding)
```

## Components

### 1. BM25 Retriever (NEW)

**Purpose**: Keyword-based exact matching search

**Algorithm**:
```
BM25(D, Q) = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))

Where:
- qi: query term
- D: document
- f(qi, D): frequency of qi in D
- |D|: document length
- avgdl: average document length
- k1: term saturation parameter (default 1.2)
- b: length normalization parameter (default 0.75)
- IDF: inverse document frequency
```

**Key Features**:
- Term frequency weighting
- Document length normalization
- Inverse document frequency (IDF)
- Stop word handling (optional)

### 2. RRF (Reciprocal Rank Fusion)

**Purpose**: Merge results from multiple retrieval methods

**Algorithm**:
```
RRS(d) = Σ 1 / (k + rank_i(d))

Where:
- d: document
- k: constant (default 60)
- rank_i(d): rank of d in method i
- RRS: Reciprocal Rank Score

Final score = α × BM25_score + (1 - α) × Semantic_score
```

**Benefits**:
- No score normalization needed
- Handles different score scales
- Robust to outliers
- Simple and effective

### 3. Hybrid Retriever

**Purpose**: Orchestrate BM25 + Semantic search

**Configuration**:
```python
@dataclass
class HybridSearchConfig:
    """Hybrid search configuration"""
    enabled: bool = False
    alpha: float = 0.5  # BM25 weight (0-1)
    rrf_k: int = 60    # RRF constant
    bm25_k1: float = 1.2
    bm25_b: float = 0.75
    top_k: int = 5
    min_score: float = 0.3
```

## Implementation Plan

### Phase 1: BM25 Implementation (NEW)
- [ ] Create `BM25Index` class
- [ ] Implement BM25 scoring algorithm
- [ ] Add document indexing (tokenization, term freq)
- [ ] Implement query processing
- [ ] Add tests

### Phase 2: RRF Fusion (NEW)
- [ ] Create `RankFusion` class
- [ ] Implement RRF algorithm
- [ ] Add weighted fusion support
- [ ] Implement result re-ranking
- [ ] Add tests

### Phase 3: Hybrid Integration
- [ ] Update `RetrievalConfig` with hybrid settings
- [ ] Create `HybridRetriever` class
- [ ] Update `MemoryRetriever` to support hybrid mode
- [ ] Add lazy initialization for BM25 index
- [ ] Update auto-indexing to include BM25

### Phase 4: Testing
- [ ] Unit tests for BM25
- [ ] Unit tests for RRF
- [ ] Integration tests for Hybrid Search
- [ ] Performance benchmarks
- [ ] Accuracy comparison (BM25 vs Semantic vs Hybrid)

## File Structure

```
src/fastreact/memory/
├── bm25.py                 # NEW: BM25 indexer and searcher
│   ├── BM25Index          # BM25 index management
│   └── BM25Retriever      # BM25 search interface
├── fusion.py              # NEW: Rank fusion algorithms
│   ├── ReciprocalRankFusion  # RRF implementation
│   └── WeightedFusion     # Weighted score fusion
├── retriever.py           # UPDATE: Add hybrid support
│   └── MemoryRetriever    # Add hybrid_mode flag
└── embeddings.py          # (unchanged)

tests/memory/
├── test_bm25.py           # NEW: BM25 tests
├── test_fusion.py         # NEW: Fusion tests
└── test_hybrid_retriever.py  # NEW: Hybrid integration tests
```

## Performance Considerations

### BM25 Index
- **Size**: ~10-50MB per 10K documents (depends on vocabulary)
- **Build time**: ~100-500ms per 10K documents
- **Query time**: ~10-50ms per query
- **Update cost**: Low (incremental term frequency updates)

### Hybrid Search
- **Latency**: ~60-150ms (BM25 + Semantic + Fusion)
- **Accuracy**: +10-20% vs pure semantic (per Anthropic)
- **Trade-off**: Slightly higher latency for better accuracy

## Configuration Examples

### Basic Hybrid Search
```python
config = RetrievalConfig(
    enabled=True,
    hybrid_search=HybridSearchConfig(
        enabled=True,
        alpha=0.5,  # Equal weight to BM25 and Semantic
    ),
)
```

### Keyword-Heavy (for exact matches)
```python
config = RetrievalConfig(
    enabled=True,
    hybrid_search=HybridSearchConfig(
        enabled=True,
        alpha=0.7,  # 70% BM25, 30% Semantic
    ),
)
```

### Semantic-Heavy (for conceptual matches)
```python
config = RetrievalConfig(
    enabled=True,
    hybrid_search=HybridSearchConfig(
        enabled=True,
        alpha=0.3,  # 30% BM25, 70% Semantic
    ),
)
```

## Research References

1. **Anthropic's Hybrid Search Approach**
   - Combines keyword and semantic search
   - Uses RRF for result fusion
   - Reports 10-20% accuracy improvement

2. **BM25 Algorithm**
   - Robertson & Zaragoza (2009)
   - State-of-the-art for keyword search
   - Probabilistic retrieval model

3. **Reciprocal Rank Fusion**
   - Cormack et al. (2009)
   - Simple yet effective fusion method
   - No score normalization needed

## Success Criteria

- [ ] BM25 search working correctly
- [ ] RRF fusion implemented and tested
- [ ] Hybrid retriever integrated with Engine
- [ ] Performance benchmarks collected
- [ ] Accuracy improvement verified (vs pure semantic)
- [ ] Configuration examples documented
- [ ] All tests passing

---

**Status**: Design Complete
**Next Step**: Implement BM25 Index
**Priority**: High (per user request)
