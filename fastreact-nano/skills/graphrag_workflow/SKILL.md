---
name: graphrag_workflow
description: Guide for using GraphRAG knowledge graph tools effectively to search and explore entities and relationships
tags: [graphrag, knowledge, search, graph, semantic]
version: 1.0.0
mcp_servers: [graphrag]
recommended_tools: [graphrag_search_graph, graphrag_get_entity, graphrag_query_relationships, graphrag_vector_search]
---

# GraphRAG Workflow Skill

This skill provides guidance on effectively using GraphRAG (Graph Retrieval-Augmented Generation) tools to search and explore knowledge graphs.

## When to Use GraphRAG Tools

Use GraphRAG tools when the user asks about:
- Knowledge retrieval: "Search for information about X", "Find entities related to Y"
- Entity details: "Tell me more about [specific entity]", "What do you know about X?"
- Relationships: "How are X and Y related?", "What connects X to Y?"
- Similar concepts: "Find entities similar to X", "What's related to X?"
- Semantic search: "Search for concepts like..."

## Tool Selection Guide

### search_graph
**Use for**: General knowledge search and entity discovery

**When to use**:
- User's query is broad or exploratory
- Looking for entities matching specific keywords
- Discovering what's available in the knowledge graph
- Initial exploration before deeper investigation

**Example queries**:
- "Search for AI-related entities"
- "Find entities about machine learning"
- "What entities mention 'neural'?"

**Parameters**:
- `query` (required): Search text
- `limit` (optional): Max results (default: 10)

### get_entity
**Use for**: Getting detailed information about a specific entity

**When to use**:
- User mentions a specific entity ID or name
- After search_graph to get full entity details
- Need complete entity information including properties

**Example queries**:
- "Tell me more about entity_1"
- "Get details for Machine Learning entity"
- "Show me full information about Deep Learning"

**Parameters**:
- `entity_id` (required): Entity identifier (e.g., "entity_1", "entity_2")

### query_relationships
**Use for**: Exploring connections between entities

**When to use**:
- User asks about relationships or connections
- Understanding how entities relate to each other
- Building knowledge chains or paths
- Finding linked concepts

**Example queries**:
- "How is AI related to Machine Learning?"
- "What's connected to Neural Networks?"
- "Show relationships for Deep Learning"

**Parameters**:
- `entity_id` (required): Source entity identifier
- `max_depth` (optional): Relationship depth (default: 2)

### vector_search
**Use for**: Finding semantically similar entities

**When to use**:
- User wants to find related concepts
- Semantic similarity search needed
- Finding entities by meaning rather than keywords
- Exploring conceptual neighborhoods

**Example queries**:
- "Find entities similar to Neural Networks"
- "What concepts are like Deep Learning?"
- "Search for similar AI architectures"

**Parameters**:
- `query_text` (required): Query text
- `top_k` (optional): Number of results (default: 5)

## Best Practices

### 1. Start Broad, Then Deep
Begin with `search_graph` for exploration, then use `get_entity` for details.

**Example**:
```
User: "What do you know about AI?"
Assistant:
1. Call search_graph with query="Artificial Intelligence"
2. For each result, call get_entity to get details
3. Present comprehensive information
```

### 2. Follow Relationship Chains
Use `query_relationships` to explore connections and build understanding.

**Example**:
```
User: "How are AI and LLMs connected?"
Assistant:
1. Call query_relationships for AI entity
2. Follow the chain through ML, Deep Learning, to LLMs
3. Explain each connection
```

### 3. Combine Tools for Rich Answers
Use multiple tools together to provide comprehensive responses.

**Example**:
```
User: "Tell me about Deep Learning and related concepts"
Assistant:
1. Call get_entity for Deep Learning (details)
2. Call query_relationships for Deep Learning (connections)
3. Call vector_search for "Deep Learning" (similar concepts)
4. Synthesize information from all sources
```

### 4. Use Vector Search for Discovery
When keyword search doesn't find what user wants, try semantic search.

**Example**:
```
User: "Find modern AI architectures"
Assistant:
1. Try search_graph with "modern architecture" (may miss relevant results)
2. Call vector_search with "modern AI architectures" (finds Transformers, LLMs)
3. Present semantically similar entities
```

## Tool Workflow Examples

### Example 1: Exploratory Search
```
User: "What's in your knowledge graph about AI?"

1. search_graph(query="Artificial Intelligence", limit=10)
   → Returns: [AI, ML, DL, NLP, CV, Neural Networks, Transformers, LLMs]

2. get_entity(entity_id="entity_1")  # AI
   → Returns: Full AI entity with properties

3. query_relationships(entity_id="entity_1", max_depth=2)
   → Returns: AI → ML, NLP, CV

4. Synthesize: Present AI overview with key subfields
```

### Example 2: Relationship Tracing
```
User: "How are Transformers related to AI?"

1. search_graph(query="Transformers")
   → Returns: entity_7 (Transformers)

2. query_relationships(entity_id="entity_7", max_depth=3)
   → Returns: Transformers ← Neural Networks ← ML ← AI

3. get_entity(entity_id="entity_1")  # AI
4. get_entity(entity_id="entity_6")  # Neural Networks

5. Synthesize: Explain the hierarchical relationship
```

### Example 3: Semantic Discovery
```
User: "What's similar to Large Language Models?"

1. vector_search(query_text="Large Language Models", top_k=5)
   → Returns: [LLMs, Transformers, Deep Learning, NLP, AI]

2. get_entity for each result to provide details

3. Synthesize: Present similar concepts with explanations
```

## Common Patterns

### Pattern 1: Entity Lookup
```
search_graph → get_entity (for each result)
```

### Pattern 2: Relationship Exploration
```
search_graph → get_entity → query_relationships → get_entity (related)
```

### Pattern 3: Semantic Discovery
```
vector_search → get_entity (for each result)
```

### Pattern 4: Comprehensive Analysis
```
search_graph → get_entity → query_relationships → vector_search
```

## Error Handling

If an entity is not found:
- Use `search_graph` to find similar entities
- Suggest available entity IDs
- Try `vector_search` for semantic alternatives

If relationships are empty:
- The entity might be isolated in the graph
- Try `vector_search` to find semantically related entities
- Check if the entity ID is correct

## Tips for Better Results

1. **Be specific with queries**: Use full terms like "Machine Learning" instead of "ML"
2. **Try different tools**: If search_graph doesn't work, try vector_search
3. **Follow connections**: Use query_relationships to discover related entities
4. **Combine information**: Synthesize data from multiple tool calls
5. **Present clearly**: Structure answers with entity names, descriptions, and relationships
