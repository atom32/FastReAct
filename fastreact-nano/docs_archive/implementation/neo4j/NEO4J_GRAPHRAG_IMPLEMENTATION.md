# Neo4j GraphRAG 实现方案

**目标**: 将当前的mock GraphRAG升级为真正的Neo4j图数据库实现

---

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    GraphRAG Neo4j Server            │
│                                                            │
│  MCP Server (FastReAct)                                │
│    │                                                       │
│    ├─→ search_graph         → Neo4j Cypher             │
│    ├─→ get_entity           → Neo4j Cypher             │
│    ├─→ query_relationships  → Neo4j Cypher             │
│    ├─→ vector_search       → Neo4j + Vector Index      │
│    └─→ create_entity        → Neo4j Cypher             │
│                                                            │
│  Neo4j Connection (neo4j Python Driver)                 │
│    • URI: bolt://localhost:7687                          │
│    • 用户: neo4j                                        │
│    • 密码: password                                      │
│                                                            │
│  Neo4j Database                                          │
│    • Nodes: 实体 (Entity)                                │
│    • Relationships: 关系 (RELATES_TO, INCLUDES, etc.)    │
│    • Properties: 属性 (name, type, description, etc.)   │
│    • Indexes: 向量索引、全文索引                         │
└─────────────────────────────────────────────────────────┘
```

---

## 实现步骤

### Step 1: 安装Neo4j

**Docker方式（推荐）**:
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS=["apoc"] \
  neo4j:latest
```

**本地安装**:
```bash
# macOS
brew install neo4j

# 启动
neo4j start
```

### Step 2: Python依赖

```bash
pip install neo4j>=5.0.0 numpy>=1.20.0
```

### Step 3: 创建Neo4j GraphRAG服务器

**文件**: `mcp_servers/builtin/graph_rag_neo4j_server.py`

```python
"""
FastReAct Nano - Neo4j-based GraphRAG MCP Server

Real GraphRAG implementation using Neo4j graph database.
"""

import asyncio
from typing import Any, Dict
from neo4j import AsyncGraphDatabase
from fastreact.mcp.server import SimpleMCPServer


class Neo4jGraphRAGServer(SimpleMCPServer):
    """
    Neo4j-based GraphRAG MCP Server

    Uses Neo4j for:
    - Entity and relationship storage
    - Cypher query execution
    - Graph algorithms (PageRank, community detection)
    - Vector similarity search (via Neo4j vector index)
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
    ):
        super().__init__()
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: AsyncGraphDatabase = None
        self._register_tools()

    async def _connect(self):
        """Establish Neo4j connection"""
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password)
        )
        print("[Neo4j] Connected to graph database")

    async def _disconnect(self):
        """Close Neo4j connection"""
        if self._driver:
            await self._driver.close()
            print("[Neo4j] Disconnected from graph database")

    def _register_tools(self):
        """Register GraphRAG tools"""

        # Tool 1: Search entities (Cypher)
        self.register_tool(
            name="search_graph",
            description="Search knowledge graph using Neo4j Cypher queries. Supports name, type, property, and full-text search.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., name:'Machine Learning', type:'concept')"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Max results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )

        # Tool 2: Get entity details
        self.register_tool(
            name="get_entity",
            description="Get detailed entity info including relationships using Neo4j graph traversal",
            input_schema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Entity name to retrieve"
                    },
                    "depth": {
                        "type": "number",
                        "description": "Relationship depth (1-3)",
                        "default": 2
                    }
                },
                "required": ["entity_name"]
            }
        )

        # Tool 3: Query relationships
        self.register_tool(
            name="query_relationships",
            description="Query relationships using Neo4j Cypher with variable depth traversal",
            input_schema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source entity name"
                    },
                    "relationship_type": {
                        "type": "string",
                        "description": "Relationship type (optional)"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["OUTGOING", "INCOMING", "BOTH"],
                        "description": "Traversal direction",
                        "default": "OUTGOING"
                    },
                    "max_depth": {
                        "type": "number",
                        "description": "Max depth (1-5)",
                        "default": 2
                    }
                },
                "required": ["source"]
            }
        )

        # Tool 4: Vector search (Neo4j vector index)
        self.register_tool(
            name="vector_search",
            description="Semantic search using Neo4j vector index and cosine similarity",
            input_schema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Query text for semantic search"
                    },
                    "top_k": {
                        "type": "number",
                        "description": "Number of results",
                        "default": 5
                    },
                    "index_name": {
                        "type": "string",
                        "description": "Vector index name",
                        "default": "entity_embeddings"
                    }
                },
                "required": ["query_text"]
            }
        )

        # Tool 5: Create entity
        self.register_tool(
            name="create_entity",
            description="Create new entity in Neo4j graph database with properties and optional relationships",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Entity name (must be unique)"
                    },
                    "type": {
                        "type": "string",
                        "description": "Entity type (e.g., Concept, Algorithm, Person)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Entity description"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Additional properties (year, field, etc.)"
                    },
                    "relationships": {
                        "type": "array",
                        "description": "List of relationships to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "target": {"type": "string"},
                                "type": {"type": "string"},
                                "weight": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["name", "type"]
            }
        )

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> str:
        """Handle tool calls to Neo4j"""
        await self._connect()

        try:
            if name == "search_graph":
                return await self._search_graph(**arguments)
            elif name == "get_entity":
                return await self._get_entity(**arguments)
            elif name == "query_relationships":
                return await self._query_relationships(**arguments)
            elif name == "vector_search":
                return await self._vector_search(**arguments)
            elif name == "create_entity":
                return await self._create_entity(**arguments)
            else:
                return f"Unknown tool: {name}"
        finally:
            await self._disconnect()

    async def _search_graph(self, query: str, limit: int = 10) -> str:
        """Search entities using Neo4j Cypher"""
        cypher = f"""
        MATCH (e:Entity)
        WHERE e.name CONTAINS $query
           OR e.description CONTAINS $query
           OR any(prop IN e.properties WHERE toString(prop) CONTAINS $query)
        RETURN e.name as name,
               e.type as type,
               e.description as description,
               labels(e) as labels
        LIMIT $limit
        """

        async with self._driver.session() as session:
            result = await session.run(
                cypher,
                query=query,
                limit=limit
            )

            records = await result.data()

            if not records:
                return f"No entities found matching query: {query}"

            output = [f"## Search Results for '{query}'\n"]
            for record in records:
                output += f"- **{record['name']}** ({record['type']})\n"
                output += f"  {record['description']}\n"
                if record.get('labels'):
                    output += f"  Labels: {', '.join(record['labels'])}\n"
                output += "\n"

            return "\n".join(output)

    async def _get_entity(self, entity_name: str, depth: int = 2) -> str:
        """Get entity with relationships using Neo4j graph traversal"""
        cypher = f"""
        MATCH path = (e:Entity {{name: $entity_name}})-[*1..{depth}]-(related)
        RETURN e.name as entity,
               e.type as type,
               e.description as description,
               relationships(path) as rels,
               nodes(path) as nodes
        """

        async with self._driver.session() as session:
            result = await session.run(
                cypher,
                entity_name=entity_name,
                depth=depth
            )

            record = await result.single()

            if not record:
                return f"Entity '{entity_name}' not found"

            output = [
                f"## {record['entity']} ({record['type']})",
                f"{record['description']}\n",
                f"### Relationships ({len(record['rels'])}):\n"
            ]

            for rel in record['rels'][:10]:  # Limit to first 10
                output.append(f"- **{rel.type}** → {rel.end_node['name']}")

            return "\n".join(output)

    async def _query_relationships(
        self,
        source: str,
        relationship_type: str = None,
        direction: str = "OUTGOING",
        max_depth: int = 2
    ) -> str:
        """Query relationships using Neo4j Cypher"""

        if direction == "OUTGOING":
            arrow = "->"
        elif direction == "INCOMING":
            arrow = "<-"
        else:
            arrow = "-"

        rel_pattern = f"[r:{relationship_type}]" if relationship_type else ""

        cypher = f"""
        MATCH (start:Entity {{name: $source}}){arrow}[{rel_pattern}*1..{max_depth}]-(end:Entity)
        RETURN start.name as source,
               type(r) as relationship,
               end.name as target,
               r.weight as weight
        ORDER BY weight DESC
        """

        async with self._driver.session() as session:
            result = await session.run(cypher, source=source)
            records = await result.data()

            if not records:
                return f"No relationships found from '{source}'"

            output = [f"## Relationships from '{source}'\n"]
            for record in records:
                output.append(
                    f"- **{record['source']}** --[{record['relationship']}({record['weight']:.2f})--> **{record['target']}**"
                )

            return "\n".join(output)

    async def _vector_search(self, query_text: str, top_k: int = 5, index_name: str = "entity_embeddings") -> str:
        """Vector similarity search using Neo4g vector index"""
        # Note: This requires embeddings to be pre-computed in Neo4j
        # For now, use simple keyword matching as fallback

        cypher = f"""
        CALL db.index.vector.queryNodes($index_name, {{
            indexQuery: $query_text,
            topK: $top_k
        }}) YIELD node, score
        RETURN node.name as name,
               node.type as type,
               node.description as description,
               score
        ORDER BY score DESC
        """

        async with self._driver.session() as session:
            result = await session.run(
                cypher,
                query_text=query_text,
                top_k=top_k,
                index_name=index_name
            )
            records = await result.data()

            if not records:
                return f"No similar entities found for: {query_text}"

            output = [f"## Vector Search Results for '{query_text}'\n"]
            for record in records:
                output.append(
                    f"- **{record['name']}** (similarity: {record['score']:.4f})\n"
                    f"  {record['description']}\n"
                )

            return "\n".join(output)

    async def _create_entity(
        self,
        name: str,
        type: str,
        description: str = "",
        properties: dict = None,
        relationships: list = None
    ) -> str:
        """Create entity in Neo4j"""
        cypher = """
        CREATE (e:Entity:$type {name: $name, description: $description})
        """

        async with self._driver.session() as session:
            # Create entity
            await session.run(
                cypher,
                name=name,
                type=type,
                description=description
            )

            # Add relationships
            if relationships:
                for rel in relationships:
                    await session.run(
                        f"""
                        MATCH (e:Entity {{name: $name}}), (target:Entity {{name: $target}})
                        CREATE (e)-[r:{rel['type']} {{weight: {rel.get('weight', 1.0)}}]->(target)
                        """,
                        name=name,
                        target=rel.get('target'),
                        type=rel.get('type', 'RELATES_TO')
                    )

            await session.close()

        return f"Entity '{name}' created successfully with {len(relationships) or 0} relationships"


# Entry point for MCP server
async def main():
    server = Neo4jGraphRAGServer()
    # Start MCP server (SimpleMCPServer has run() method)
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## MCP配置

**文件**: `~/.fastreact/config.json`

```json
{
  "mcp": {
    "servers": [
      {
        "name": "graphrag_neo4j",
        "command": "uvx",
        "args": [
          "--from", "mcp_servers.builtin.graph_rag_neo4j_server",
          "graph_rag_neo4j_server"
        ],
        "isolation": "shared",
        "description": "Neo4j-based GraphRAG knowledge graph",
        "associated_skill": "graphrag_workflow",
        "environment": {
          "NEO4J_URI": "bolt://localhost:7687",
          "NEO4J_USER": "neo4j",
          "NEO4J_PASSWORD": "password"
        }
      }
    ]
  }
}
```

---

## 数据初始化

### 方案A: 从Mock数据迁移

```python
# scripts/init_neo4j.py

from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    # Create entities from mock data
    entities = [
        ("Artificial Intelligence", "concept", {...}),
        ("Machine Learning", "concept", {...}),
        # ...
    ]

    for name, type_, props in entities:
        session.run(
            f"CREATE (e:Entity:{type_} {{name: $name}}) SET e += $props",
            name=name, type=type_, props=props
        )

    # Create relationships
    relationships = [
        ("Artificial Intelligence", "Machine Learning", "includes", 0.95),
        # ...
    ]

    for source, target, type_, weight in relationships:
        session.run(
            f"""
            MATCH (s:Entity {{name: $source}}), (t:Entity {{name: $target}})
            CREATE (s)-[r:{type_} {{weight: $weight}}]->(t)
            """,
            source=source, target=target, type_=type_, weight=weight
        )

driver.close()
```

### 方案B: 从文档构建GraphRAG

```python
# scripts/build_graph_from_docs.py

from pathlib import Path
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# Load documents
docs_dir = Path("documents")
documents = list(docs_dir.glob("**/*.md"))

# Initialize embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    for doc in documents:
        # 1. Create document entity
        session.run(
            "CREATE (d:Document {name: $name, path: $path})",
            name=doc.name, path=str(doc)
        )

        # 2. Split text into chunks
        text = doc.read_text()
        chunks = split_text(text, chunk_size=512, overlap=50)

        for i, chunk in enumerate(chunks):
            # 3. Create chunk entity
            chunk_id = f"{doc.stem}_{i}"
            embedding = embedder.encode(chunk).tolist()

            session.run(
                """
                CREATE (c:Chunk {id: $id, text: $text, embedding: $embedding})
                MERGE (d:Document {name: $name})
                CREATE (d)-[:HAS_CHUNK]->(c)
                """,
                id=chunk_id, text=chunk, embedding=embedding, name=doc.name
            )

        # 4. Create next chunk relationships
        for i in range(len(chunks) - 1):
            session.run(
                """
                MATCH (c1:Chunk {id: $id1}), (c2:Chunk {id: $id2})
                CREATE (c1)-[:NEXT]->(c2)
                """,
                id1=f"{doc.stem}_{i}",
                id2=f"{doc.stem}_{i+1}"
            )

driver.close()
```

---

## Neo4j优势 vs Mock实现

| 特性 | Mock (当前) | Neo4j (真正) |
|------|------------|--------------|
| **数据持久化** | ❌ 内存中，重启丢失 | ✅ 持久化存储 |
| **数据规模** | ❌ 受内存限制 | ✅ TB级数据 |
| **图算法** | ❌ 需手写实现 | ✅ PageRank, 社区检测 |
| **复杂查询** | ❌ Python遍历慢 | ✅ Cypher优化 |
| **并发** | ❌ 需加锁 | ✅ ACID事务 |
| **向量索引** | ❌ 手动计算 | ✅ ANN索引 |
| **PR排序** | ❌ 简单权重 | ✅ 真正PageRank |

---

## 推荐路径

### 阶段1: 保持Mock (当前)
- 适用: 测试、开发
- 优势: 零依赖、快速启动

### 阶段2: Neo4j单机 (推荐)
- 适用: 单用户、小规模
- 优势: 真正图数据库、易部署
- 成本: 低

### 阶段3: Neo4j集群
- 适用: 多用户、大规模
- 优势: 高可用、横向扩展
- 成本: 高

---

**是否需要我帮你实现Neo4j版本？**
