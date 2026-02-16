"""
GraphRAG工具集（异步版本）

从Biro迁移的GraphRAG工具，使用MCP适配器注册
所有工具已改为异步实现，使用httpx替代requests
"""

import os
import asyncio
import time
from typing import Optional, Dict, Any, List
import httpx
from fastreact.tools.mcp_adapter import register_mcp_tool


# GraphRAG配置
HIPPO_RAG_URL = os.getenv("HIPPO_RAG_URL", "http://localhost:8080")
HIPPO_RAG_API_KEY = os.getenv("HIPPO_RAG_API_KEY")
HIPPO_RAG_TIMEOUT = int(os.getenv("HIPPO_RAG_TIMEOUT", "10"))


async def _make_graphrag_request(
    endpoint: str,
    payload: Dict[str, Any],
    timeout: int = HIPPO_RAG_TIMEOUT
) -> Dict[str, Any]:
    """
    发送异步HTTP请求到GraphRAG服务（内部辅助函数）

    Args:
        endpoint: API端点路径
        payload: 请求负载
        timeout: 超时时间（秒）

    Returns:
        响应JSON数据

    Raises:
        httpx.HTTPError: 请求失败
    """
    url = f"{HIPPO_RAG_URL}{endpoint}"

    headers = {}
    if HIPPO_RAG_API_KEY:
        headers["Authorization"] = f"Bearer {HIPPO_RAG_API_KEY}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


@register_mcp_tool(
    "query_graph_rag",
    description="Query GraphRAG knowledge graph with natural language. Returns answers with sources, confidence, related entities, and key concepts.",
)
async def query_graph_rag(
    query: str,
    max_results: int = 10,
    reasoning_depth: int = 3,
) -> Dict[str, Any]:
    """
    Query GraphRAG knowledge graph (异步版本)

    Args:
        query: Natural language query
        max_results: Maximum number of results to return
        reasoning_depth: Depth of reasoning (1-5)

    Returns:
        {
            "status": "success" | "failed",
            "answer": "Main answer content",
            "sources": ["source1", "source2"],
            "confidence": 0.85,
            "related_entities": ["entity1", "entity2"],
            "key_concepts": ["concept1", "concept2"],
            "execution_time": 3.2
        }
    """
    try:
        start_time = time.time()

        result_data = await _make_graphrag_request(
            endpoint="/api/v1/query",
            payload={
                "query": query,
                "max_results": max_results,
                "reasoning_depth": reasoning_depth,
            }
        )

        execution_time = time.time() - start_time

        return {
            "status": "success",
            "action": "query_graph_rag",
            "parameters": {"query": query, "max_results": max_results, "reasoning_depth": reasoning_depth},
            "execution_time": execution_time,
            "answer": result_data.get("answer", ""),
            "sources": result_data.get("sources", []),
            "confidence": result_data.get("confidence", 0.0),
            "related_entities": result_data.get("entities", []),
            "key_concepts": result_data.get("concepts", []),
        }

    except httpx.HTTPError as e:
        return {"status": "failed", "error": f"Failed to query GraphRAG: {str(e)}"}
    except Exception as e:
        return {"status": "failed", "error": f"Unexpected error: {str(e)}"}


@register_mcp_tool(
    "analyze_relationships",
    description="Analyze relationships between multiple entities in the knowledge graph. Returns direct relationships, indirect connections, relationship strength, and centrality metrics.",
)
async def analyze_relationships(
    entities: List[str],
    relationship_types: Optional[List[str]] = None,
    max_depth: int = 2,
) -> Dict[str, Any]:
    """
    Analyze relationships between entities (异步版本)

    Args:
        entities: List of entity names to analyze
        relationship_types: Optional list of relationship types to filter
        max_depth: Maximum depth for relationship traversal

    Returns:
        {
            "status": "success",
            "entities": ["Alice", "Bob"],
            "direct_relationships": [...],
            "indirect_relationships": [...],
            "relationship_graph": {...},
            "centrality": {"Alice": 0.8, "Bob": 0.6}
        }
    """
    try:
        payload = {
            "entities": entities,
            "max_depth": max_depth,
        }

        if relationship_types:
            payload["relationship_types"] = relationship_types

        result_data = await _make_graphrag_request(
            endpoint="/api/v1/analyze",
            payload=payload
        )

        return {
            "status": "success",
            "action": "analyze_relationships",
            "parameters": {"entities": entities, "relationship_types": relationship_types},
            "entities": entities,
            "direct_relationships": result_data.get("direct_relationships", []),
            "indirect_relationships": result_data.get("indirect_relationships", []),
            "relationship_graph": result_data.get("graph", {}),
            "centrality": result_data.get("centrality", {}),
            "common_entities": result_data.get("common_entities", []),
        }

    except httpx.HTTPError as e:
        return {"status": "failed", "error": f"Failed to analyze relationships: {str(e)}"}
    except Exception as e:
        return {"status": "failed", "error": f"Unexpected error: {str(e)}"}


@register_mcp_tool(
    "multi_hop_reasoning",
    description="Perform multi-hop reasoning in the knowledge graph to find paths between entities. Returns reasoning paths, shortest path, confidence scores, and intermediate entities.",
)
async def multi_hop_reasoning(
    start_entity: str,
    end_entity: str,
    max_hops: int = 5,
    reasoning_mode: str = "shortest_path",
) -> Dict[str, Any]:
    """
    Perform multi-hop reasoning (异步版本)

    Args:
        start_entity: Starting entity name
        end_entity: Target entity name
        max_hops: Maximum number of hops to explore
        reasoning_mode: Reasoning mode (shortest_path, all_paths, beam_search)

    Returns:
        {
            "status": "success",
            "start_entity": "Alice",
            "end_entity": "Charlie",
            "reasoning_paths": [
                ["Alice", "Bob", "Charlie"],
                ["Alice", "David", "Charlie"]
            ],
            "shortest_path": ["Alice", "Bob", "Charlie"],
            "path_confidence": 0.75,
            "intermediate_entities": ["Bob"]
        }
    """
    try:
        result_data = await _make_graphrag_request(
            endpoint="/api/v1/reasoning",
            payload={
                "start": start_entity,
                "end": end_entity,
                "max_hops": max_hops,
                "mode": reasoning_mode,
            }
        )

        return {
            "status": "success",
            "action": "multi_hop_reasoning",
            "parameters": {"start_entity": start_entity, "end_entity": end_entity, "max_hops": max_hops},
            "start_entity": start_entity,
            "end_entity": end_entity,
            "reasoning_paths": result_data.get("paths", []),
            "shortest_path": result_data.get("shortest_path", []),
            "path_confidence": result_data.get("confidence", 0.0),
            "intermediate_entities": result_data.get("intermediate", []),
            "all_paths": result_data.get("all_paths", []),
        }

    except httpx.HTTPError as e:
        return {"status": "failed", "error": f"Failed multi-hop reasoning: {str(e)}"}
    except Exception as e:
        return {"status": "failed", "error": f"Unexpected error: {str(e)}"}


@register_mcp_tool(
    "knowledge_extraction",
    description="Extract knowledge (entities and relationships) from text and add to the knowledge graph. Returns extracted entities, relationships, and concepts.",
)
async def knowledge_extraction(
    text: str,
    extract_relationships: bool = True,
    add_to_graph: bool = False,
) -> Dict[str, Any]:
    """
    Extract knowledge from text (异步版本)

    Args:
        text: Input text to extract knowledge from
        extract_relationships: Whether to extract relationships
        add_to_graph: Whether to add extracted knowledge to the graph

    Returns:
        {
            "status": "success",
            "text": "Alice works at TechCorp",
            "entities": ["Alice", "TechCorp"],
            "relationships": [
                {"source": "Alice", "target": "TechCorp", "type": "works_at"}
            ],
            "concepts": ["employment", "company"],
            "knowledge_graph": {...}
        }
    """
    try:
        result_data = await _make_graphrag_request(
            endpoint="/api/v1/extract",
            payload={
                "text": text,
                "extract_relationships": extract_relationships,
                "add_to_graph": add_to_graph,
            }
        )

        return {
            "status": "success",
            "action": "knowledge_extraction",
            "parameters": {"text": text, "extract_relationships": extract_relationships},
            "text": text,
            "entities": result_data.get("entities", []),
            "relationships": result_data.get("relationships", []),
            "concepts": result_data.get("concepts", []),
            "knowledge_graph": result_data.get("graph", {}),
            "confidence": result_data.get("confidence", 0.0),
        }

    except httpx.HTTPError as e:
        return {"status": "failed", "error": f"Failed knowledge extraction: {str(e)}"}
    except Exception as e:
        return {"status": "failed", "error": f"Unexpected error: {str(e)}"}


@register_mcp_tool(
    "check_graph_rag_config",
    description="Check GraphRAG system configuration and connectivity. Returns system status, configuration details, and health metrics.",
)
async def check_graph_rag_config() -> Dict[str, Any]:
    """
    Check GraphRAG configuration (异步版本)

    Returns:
        {
            "status": "success" | "warning" | "error",
            "hippo_rag_url": "http://localhost:8080",
            "api_key_configured": true,
            "connection_status": "ok" | "http_xxx" | "unreachable",
            "version": "1.0.0",
            "features": ["query", "analyze", "reasoning", "extraction"]
        }
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            endpoint = f"{HIPPO_RAG_URL}/api/v1/health"

            headers = {}
            if HIPPO_RAG_API_KEY:
                headers["Authorization"] = f"Bearer {HIPPO_RAG_API_KEY}"

            response = await client.get(endpoint, headers=headers)

            if response.status_code == 200:
                result_data = response.json()
                return {
                    "status": "success",
                    "action": "check_graph_rag_config",
                    "hippo_rag_url": HIPPO_RAG_URL,
                    "api_key_configured": HIPPO_RAG_API_KEY is not None,
                    "connection_status": "ok",
                    "version": result_data.get("version", "unknown"),
                    "features": result_data.get("features", []),
                    "health_check": "passed",
                }
            else:
                return {
                    "status": "warning",
                    "action": "check_graph_rag_config",
                    "hippo_rag_url": HIPPO_RAG_URL,
                    "api_key_configured": HIPPO_RAG_API_KEY is not None,
                    "connection_status": f"http_{response.status_code}",
                    "health_check": "failed",
                }

    except httpx.ConnectError:
        return {
            "status": "error",
            "action": "check_graph_rag_config",
            "hippo_rag_url": HIPPO_RAG_URL,
            "api_key_configured": HIPPO_RAG_API_KEY is not None,
            "connection_status": "unreachable",
            "error": "Connection refused",
        }
    except Exception as e:
        return {
            "status": "error",
            "action": "check_graph_rag_config",
            "hippo_rag_url": HIPPO_RAG_URL,
            "api_key_configured": HIPPO_RAG_API_KEY is not None,
            "connection_status": "error",
            "error": str(e),
        }


# 导出工具列表（用于FastReAct引擎）
__all__ = [
    "query_graph_rag",
    "analyze_relationships",
    "multi_hop_reasoning",
    "knowledge_extraction",
    "check_graph_rag_config",
]
