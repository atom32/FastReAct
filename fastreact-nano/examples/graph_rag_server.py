"""
FastReAct Nano - GraphRAG MCP Server

MCP server providing knowledge graph tools with mock data.
This is a reference implementation for integrating knowledge graph services.
"""

import asyncio
import json
import random
from typing import Any, Dict
from fastreact.mcp.server import SimpleMCPServer


class GraphRAGMCPServer(SimpleMCPServer):
    """
    GraphRAG MCP Server with mock knowledge graph data.

    Provides tools for:
    - Searching the knowledge graph
    - Getting entity details
    - Querying relationships
    - Vector similarity search
    """

    def __init__(self):
        """Initialize GraphRAG MCP server"""
        super().__init__()
        self._load_mock_data()
        self._register_tools()

    def _load_mock_data(self):
        """Load mock knowledge graph with entities and relationships"""
        # Mock entities with embeddings
        self._entities = {
            "entity_1": {
                "id": "entity_1",
                "name": "Artificial Intelligence",
                "type": "concept",
                "description": "Simulation of human intelligence processes by machines, especially computer systems.",
                "properties": {
                    "year_discovered": "1956",
                    "field": "Computer Science",
                    "applications": ["NLP", "Computer Vision", "Robotics"]
                },
                "vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
            },
            "entity_2": {
                "id": "entity_2",
                "name": "Machine Learning",
                "type": "concept",
                "description": "Subset of AI that enables systems to learn and improve from experience without being explicitly programmed.",
                "properties": {
                    "year_discovered": "1980",
                    "field": "Computer Science",
                    "algorithms": ["Neural Networks", "Decision Trees", "SVM"]
                },
                "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
            },
            "entity_3": {
                "id": "entity_3",
                "name": "Deep Learning",
                "type": "concept",
                "description": "Subset of ML using multi-layered neural networks to learn from vast amounts of data.",
                "properties": {
                    "year_discovered": "2010",
                    "field": "Computer Science",
                    "frameworks": ["TensorFlow", "PyTorch", "Keras"]
                },
                "vector": [0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82]
            },
            "entity_4": {
                "id": "entity_4",
                "name": "Natural Language Processing",
                "type": "concept",
                "description": "Branch of AI focused on interaction between computers and human language.",
                "properties": {
                    "year_discovered": "1950",
                    "field": "Computational Linguistics",
                    "tasks": ["Translation", "Sentiment Analysis", "Text Generation"]
                },
                "vector": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.88]
            },
            "entity_5": {
                "id": "entity_5",
                "name": "Computer Vision",
                "type": "concept",
                "description": "Field of AI that trains computers to interpret and understand the visual world.",
                "properties": {
                    "year_discovered": "1960",
                    "field": "Computer Science",
                    "tasks": ["Object Detection", "Image Classification", "Face Recognition"]
                },
                "vector": [0.14, 0.24, 0.34, 0.44, 0.54, 0.64, 0.74, 0.84]
            },
            "entity_6": {
                "id": "entity_6",
                "name": "Neural Networks",
                "type": "algorithm",
                "description": "Computing systems inspired by biological neural networks in human brains.",
                "properties": {
                    "year_discovered": "1943",
                    "field": "Computational Neuroscience",
                    "types": ["CNN", "RNN", "Transformer"]
                },
                "vector": [0.16, 0.26, 0.36, 0.46, 0.56, 0.66, 0.76, 0.86]
            },
            "entity_7": {
                "id": "entity_7",
                "name": "Transformers",
                "type": "architecture",
                "description": "Deep learning architecture using self-attention mechanisms to process sequential data.",
                "properties": {
                    "year_discovered": "2017",
                    "field": "Deep Learning",
                    "models": ["BERT", "GPT", "T5"]
                },
                "vector": [0.13, 0.23, 0.33, 0.43, 0.53, 0.63, 0.73, 0.83]
            },
            "entity_8": {
                "id": "entity_8",
                "name": "Large Language Models",
                "type": "model",
                "description": "AI models trained on vast amounts of text data to understand and generate human-like text.",
                "properties": {
                    "year_discovered": "2018",
                    "field": "NLP",
                    "examples": ["GPT-4", "Claude", "Llama"]
                },
                "vector": [0.11, 0.21, 0.31, 0.41, 0.51, 0.61, 0.71, 0.81]
            },
        }

        # Mock relationships between entities
        self._relationships = [
            {
                "source": "entity_1",
                "target": "entity_2",
                "type": "includes",
                "weight": 0.95,
                "description": "AI includes Machine Learning as a subset"
            },
            {
                "source": "entity_1",
                "target": "entity_4",
                "type": "includes",
                "weight": 0.90,
                "description": "AI includes NLP as a subfield"
            },
            {
                "source": "entity_1",
                "target": "entity_5",
                "type": "includes",
                "weight": 0.90,
                "description": "AI includes Computer Vision as a subfield"
            },
            {
                "source": "entity_2",
                "target": "entity_3",
                "type": "includes",
                "weight": 0.98,
                "description": "ML includes Deep Learning as a subset"
            },
            {
                "source": "entity_2",
                "target": "entity_6",
                "type": "uses",
                "weight": 0.92,
                "description": "ML uses Neural Networks algorithms"
            },
            {
                "source": "entity_3",
                "target": "entity_6",
                "type": "based_on",
                "weight": 0.99,
                "description": "Deep Learning is based on Neural Networks"
            },
            {
                "source": "entity_4",
                "target": "entity_3",
                "type": "uses",
                "weight": 0.88,
                "description": "NLP uses Deep Learning techniques"
            },
            {
                "source": "entity_4",
                "target": "entity_8",
                "type": "powered_by",
                "weight": 0.97,
                "description": "Modern NLP is powered by LLMs"
            },
            {
                "source": "entity_5",
                "target": "entity_3",
                "type": "uses",
                "weight": 0.94,
                "description": "Computer Vision uses Deep Learning"
            },
            {
                "source": "entity_6",
                "target": "entity_7",
                "type": "architecture",
                "weight": 0.91,
                "description": "Neural Networks include Transformers architecture"
            },
            {
                "source": "entity_7",
                "target": "entity_8",
                "type": "enables",
                "weight": 0.96,
                "description": "Transformers enable Large Language Models"
            },
            {
                "source": "entity_3",
                "target": "entity_8",
                "type": "enables",
                "weight": 0.93,
                "description": "Deep Learning enables Large Language Models"
            },
        ]

    def _register_tools(self):
        """Register GraphRAG tools"""

        # Tool 1: Search graph
        self.register_tool(
            name="search_graph",
            description="Search knowledge graph for entities matching query text",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for entities"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )

        # Tool 2: Get entity details
        self.register_tool(
            name="get_entity",
            description="Get detailed information about a specific entity",
            input_schema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID to retrieve (e.g., entity_1)"
                    }
                },
                "required": ["entity_id"]
            }
        )

        # Tool 3: Query relationships
        self.register_tool(
            name="query_relationships",
            description="Query relationships between entities in the knowledge graph",
            input_schema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Source entity ID"
                    },
                    "max_depth": {
                        "type": "number",
                        "description": "Maximum relationship depth",
                        "default": 2
                    }
                },
                "required": ["entity_id"]
            }
        )

        # Tool 4: Vector search
        self.register_tool(
            name="vector_search",
            description="Search entities by vector similarity (semantic search)",
            input_schema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Query text to search"
                    },
                    "top_k": {
                        "type": "number",
                        "description": "Number of similar entities to return",
                        "default": 5
                    }
                },
                "required": ["query_text"]
            }
        )

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> str:
        """Handle tool calls"""

        if name == "search_graph":
            return await self._search_graph(
                arguments["query"],
                arguments.get("limit", 10)
            )

        elif name == "get_entity":
            return await self._get_entity(arguments["entity_id"])

        elif name == "query_relationships":
            return await self._query_relationships(
                arguments["entity_id"],
                arguments.get("max_depth", 2)
            )

        elif name == "vector_search":
            return await self._vector_search(
                arguments["query_text"],
                arguments.get("top_k", 5)
            )

        else:
            return json.dumps({
                "error": f"Unknown tool: {name}"
            }, ensure_ascii=False)

    async def _search_graph(self, query: str, limit: int) -> str:
        """Search graph for matching entities"""
        results = []
        query_lower = query.lower()

        for entity_id, entity in self._entities.items():
            # Simple text matching
            name_match = query_lower in entity["name"].lower()
            desc_match = query_lower in entity["description"].lower()

            # Type matching
            type_match = query_lower in entity["type"].lower()

            # Properties matching
            props_match = False
            for key, value in entity.get("properties", {}).items():
                if isinstance(value, str) and query_lower in value.lower():
                    props_match = True
                    break
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and query_lower in item.lower():
                            props_match = True
                            break

            if name_match or desc_match or type_match or props_match:
                results.append(entity)

            if len(results) >= limit:
                break

        return json.dumps({
            "query": query,
            "results": results,
            "count": len(results)
        }, ensure_ascii=False, indent=2)

    async def _get_entity(self, entity_id: str) -> str:
        """Get entity details"""
        if entity_id in self._entities:
            entity = self._entities[entity_id].copy()

            # Add relationships
            entity["relationships"] = [
                r for r in self._relationships
                if r["source"] == entity_id or r["target"] == entity_id
            ]

            return json.dumps(entity, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "error": f"Entity not found: {entity_id}",
                "available_entities": list(self._entities.keys())
            }, ensure_ascii=False, indent=2)

    async def _query_relationships(self, entity_id: str, max_depth: int) -> str:
        """Query entity relationships"""
        if entity_id not in self._entities:
            return json.dumps({
                "error": f"Entity not found: {entity_id}"
            }, ensure_ascii=False)

        # Find direct relationships
        relationships = []
        visited = {entity_id}
        current_level = [entity_id]

        for depth in range(max_depth):
            next_level = []

            for source_id in current_level:
                for rel in self._relationships:
                    if rel["source"] == source_id and rel["target"] not in visited:
                        relationships.append({
                            **rel,
                            "depth": depth + 1,
                            "source_name": self._entities[rel["source"]]["name"],
                            "target_name": self._entities[rel["target"]]["name"]
                        })
                        visited.add(rel["target"])
                        next_level.append(rel["target"])

            current_level = next_level

            if not current_level:
                break

        return json.dumps({
            "entity": entity_id,
            "entity_name": self._entities[entity_id]["name"],
            "relationships": relationships,
            "total_count": len(relationships)
        }, ensure_ascii=False, indent=2)

    async def _vector_search(self, query_text: str, top_k: int) -> str:
        """Vector similarity search (mock implementation)"""
        # Mock: Generate pseudo-random similarity scores based on query hash
        query_hash = hash(query_text.lower()) % 1000

        results = []
        for entity_id, entity in self._entities.items():
            # Pseudo-random but consistent score based on query
            base_score = 0.7 + ((hash(query_text + entity_id) % 300) / 1000.0)
            similarity = min(0.99, base_score)

            results.append({
                **entity,
                "similarity": round(similarity, 4)
            })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Return top_k
        return json.dumps({
            "query": query_text,
            "results": results[:top_k],
            "count": len(results[:top_k])
        }, ensure_ascii=False, indent=2)


# Server entry point
async def main():
    """Run GraphRAG MCP server"""
    server = GraphRAGMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
