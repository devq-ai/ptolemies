# Ptolemies MCP Server - Demonstration Guide

**Date**: December 6, 2025  
**Version**: 1.0  
**Purpose**: Demonstrate Model Context Protocol integration with Ptolemies Knowledge Base

---

## 🎯 Overview

This demonstration shows how AI agents can access the Ptolemies Knowledge Base through the Model Context Protocol (MCP), enabling intelligent knowledge retrieval, semantic search, and graph-based reasoning over our 877 high-quality documents.

### What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI agents to access external knowledge sources and tools. It allows Large Language Models (LLMs) to:

- **Query Knowledge Bases**: Search and retrieve relevant information
- **Execute Tools**: Perform actions beyond text generation
- **Access Real-time Data**: Get current information from live systems
- **Maintain Context**: Keep track of conversation state and knowledge

---

## 🏗️ Ptolemies MCP Server Architecture

### Server Components

```python
# MCP Server Structure
mcp_server/
├── server.py           # Main MCP server implementation
├── tools/              # Available tools for AI agents
│   ├── search.py       # Semantic search functionality
│   ├── graph.py        # Graph traversal and analysis
│   ├── temporal.py     # Time-based knowledge queries
│   └── export.py       # Data export and visualization
├── resources/          # Knowledge base resources
│   ├── entities.py     # Entity management
│   ├── relationships.py # Relationship queries
│   └── metadata.py     # Quality and metadata access
└── config/             # Configuration and authentication
    ├── database.py     # Database connections
    ├── auth.py         # Authentication handlers
    └── settings.py     # Server configuration
```

### Available Tools

#### 1. Knowledge Search
- **semantic_search**: Find documents by meaning and context
- **keyword_search**: Traditional text-based search
- **entity_lookup**: Find specific entities by name or ID
- **concept_search**: Search for abstract concepts across domains

#### 2. Graph Operations
- **find_relationships**: Discover connections between entities
- **graph_traversal**: Navigate the knowledge graph
- **shortest_path**: Find connections between concepts
- **neighborhood_analysis**: Explore local graph structure

#### 3. Temporal Analysis
- **timeline_query**: Get knowledge evolution over time
- **episode_search**: Find specific temporal episodes
- **trend_analysis**: Identify patterns in knowledge development
- **version_comparison**: Compare different versions of information

#### 4. Quality Assessment
- **quality_metrics**: Get quality scores for content
- **reliability_check**: Assess information trustworthiness
- **completeness_analysis**: Identify knowledge gaps
- **citation_tracking**: Find source documentation

---

## 🚀 Demonstration Scripts

### Script 1: Basic Knowledge Retrieval

```python
#!/usr/bin/env python3
"""
Ptolemies MCP Demo 1: Basic Knowledge Retrieval
Demonstrates how AI agents can search and retrieve knowledge
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def demo_basic_search():
    """Demonstrate basic knowledge search capabilities"""
    
    # Connect to Ptolemies MCP Server
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/server.py"],
        env={"PTOLEMIES_DB": "ws://localhost:8000/rpc"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize connection
            await session.initialize()
            
            print("🔍 Ptolemies MCP Demo: Basic Knowledge Retrieval")
            print("=" * 60)
            
            # Example 1: Semantic search for neural networks
            print("\n1. Searching for 'neural networks'...")
            result = await session.call_tool(
                "semantic_search",
                {
                    "query": "neural networks",
                    "limit": 5,
                    "min_quality": 0.7
                }
            )
            
            print("Results:")
            for doc in result.content:
                print(f"  📄 {doc['title']}")
                print(f"     Domain: {doc['domain']}")
                print(f"     Quality: {doc['quality']:.1%}")
                print(f"     Snippet: {doc['summary'][:100]}...")
                print()
            
            # Example 2: Find relationships between concepts
            print("\n2. Finding relationships between PyTorch and FastAPI...")
            relationships = await session.call_tool(
                "find_relationships",
                {
                    "entity1": "PyTorch",
                    "entity2": "FastAPI",
                    "max_depth": 3
                }
            )
            
            print("Discovered relationships:")
            for rel in relationships.content:
                print(f"  🔗 {rel['path']}")
                print(f"     Type: {rel['relationship_type']}")
                print(f"     Strength: {rel['confidence']:.2f}")
                print()
            
            # Example 3: Get entity details
            print("\n3. Getting detailed information about SurrealDB...")
            entity_info = await session.call_tool(
                "entity_lookup",
                {
                    "name": "SurrealDB",
                    "include_metadata": True
                }
            )
            
            entity = entity_info.content[0]
            print(f"Entity: {entity['name']}")
            print(f"Type: {entity['type']}")
            print(f"Domain: {entity['domain']}")
            print(f"Quality Score: {entity['quality']:.1%}")
            print(f"Page Count: {entity['pages']}")
            print(f"Description: {entity['description']}")
            print(f"Key Features: {', '.join(entity['features'])}")

# Run the demonstration
if __name__ == "__main__":
    asyncio.run(demo_basic_search())
```

### Script 2: Advanced Graph Analysis

```python
#!/usr/bin/env python3
"""
Ptolemies MCP Demo 2: Advanced Graph Analysis
Shows how AI agents can perform complex graph reasoning
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def demo_graph_analysis():
    """Demonstrate advanced graph analysis capabilities"""
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            await session.initialize()
            
            print("🕸️ Ptolemies MCP Demo: Advanced Graph Analysis")
            print("=" * 60)
            
            # Example 1: Neighborhood analysis
            print("\n1. Analyzing neighborhood around 'machine learning'...")
            neighborhood = await session.call_tool(
                "neighborhood_analysis",
                {
                    "entity": "machine learning",
                    "radius": 2,
                    "include_quality": True
                }
            )
            
            print("Neighborhood structure:")
            for neighbor in neighborhood.content:
                print(f"  🎯 {neighbor['name']} ({neighbor['distance']} hops)")
                print(f"     Domain: {neighbor['domain']}")
                print(f"     Connections: {neighbor['degree']}")
                print(f"     Quality: {neighbor['quality']:.1%}")
                print()
            
            # Example 2: Cross-domain bridge analysis
            print("\n2. Finding bridges between domains...")
            bridges = await session.call_tool(
                "find_bridges",
                {
                    "domain1": "pytorch",
                    "domain2": "fastapi",
                    "bridge_type": "conceptual"
                }
            )
            
            print("Cross-domain bridges:")
            for bridge in bridges.content:
                print(f"  🌉 {bridge['concept']}")
                print(f"     Connects: {bridge['domain1']} ↔ {bridge['domain2']}")
                print(f"     Bridge strength: {bridge['strength']:.2f}")
                print(f"     Use case: {bridge['use_case']}")
                print()
            
            # Example 3: Knowledge pathway discovery
            print("\n3. Discovering learning pathway for web development...")
            pathway = await session.call_tool(
                "discover_pathway",
                {
                    "start_concept": "beginner programming",
                    "end_concept": "production web API",
                    "optimize_for": "learning_curve"
                }
            )
            
            print("Recommended learning pathway:")
            for step, concept in enumerate(pathway.content, 1):
                print(f"  {step}. {concept['name']}")
                print(f"     Domain: {concept['domain']}")
                print(f"     Difficulty: {concept['difficulty']}")
                print(f"     Prerequisites: {', '.join(concept['prerequisites'])}")
                print(f"     Estimated time: {concept['time_estimate']}")
                print()

if __name__ == "__main__":
    asyncio.run(demo_graph_analysis())
```

### Script 3: Temporal Knowledge Analysis

```python
#!/usr/bin/env python3
"""
Ptolemies MCP Demo 3: Temporal Knowledge Analysis
Demonstrates time-based knowledge exploration and trends
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def demo_temporal_analysis():
    """Demonstrate temporal knowledge analysis"""
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            await session.initialize()
            
            print("⏰ Ptolemies MCP Demo: Temporal Knowledge Analysis")
            print("=" * 60)
            
            # Example 1: Knowledge evolution timeline
            print("\n1. Tracing evolution of documentation...")
            timeline = await session.call_tool(
                "knowledge_timeline",
                {
                    "start_date": "2025-06-07T00:00:00Z",
                    "end_date": "2025-06-07T23:59:59Z",
                    "granularity": "hourly"
                }
            )
            
            print("Knowledge extraction timeline:")
            for event in timeline.content:
                print(f"  📅 {event['timestamp']}")
                print(f"     Event: {event['event_type']}")
                print(f"     Domain: {event['domain']}")
                print(f"     Pages added: {event['pages_added']}")
                print(f"     Quality impact: {event['quality_change']:+.2f}")
                print()
            
            # Example 2: Episode analysis
            print("\n2. Analyzing temporal episodes...")
            episodes = await session.call_tool(
                "episode_analysis",
                {
                    "domain": "all",
                    "episode_type": "knowledge_extraction",
                    "include_impact": True
                }
            )
            
            print("Temporal episodes summary:")
            for episode in episodes.content:
                print(f"  📚 Episode: {episode['title']}")
                print(f"     Duration: {episode['duration']} minutes")
                print(f"     Entities involved: {len(episode['entities'])}")
                print(f"     Knowledge impact: {episode['impact_score']:.2f}")
                print(f"     Success rate: {episode['success_rate']:.1%}")
                print()
            
            # Example 3: Trend identification
            print("\n3. Identifying knowledge trends...")
            trends = await session.call_tool(
                "identify_trends",
                {
                    "time_window": "1_day",
                    "trend_type": "quality_improvement",
                    "domains": ["all"]
                }
            )
            
            print("Detected trends:")
            for trend in trends.content:
                print(f"  📈 Trend: {trend['name']}")
                print(f"     Pattern: {trend['pattern']}")
                print(f"     Domains affected: {', '.join(trend['domains'])}")
                print(f"     Confidence: {trend['confidence']:.1%}")
                print(f"     Prediction: {trend['future_outlook']}")
                print()

if __name__ == "__main__":
    asyncio.run(demo_temporal_analysis())
```

---

## 🤖 AI Agent Integration Examples

### ChatGPT Plugin Integration

```javascript
// ChatGPT Plugin Manifest
{
  "schema_version": "v1",
  "name_for_human": "Ptolemies Knowledge Graph",
  "name_for_model": "ptolemies_knowledge",
  "description_for_human": "Access comprehensive Python and web development documentation through an intelligent knowledge graph.",
  "description_for_model": "Search and explore 877 high-quality documents across PyTorch, Bokeh, SurrealDB, FastAPI, Panel, PyGAD, and Logfire. Provides semantic search, relationship discovery, and temporal analysis.",
  "auth": {
    "type": "none"
  },
  "api": {
    "type": "openapi",
    "url": "https://ptolemies.example.com/openapi.json"
  },
  "logo_url": "https://ptolemies.example.com/logo.png",
  "contact_email": "support@ptolemies.example.com",
  "legal_info_url": "https://ptolemies.example.com/legal"
}
```

### Claude MCP Integration

```python
# Claude MCP Configuration
import mcp

# Configure Ptolemies MCP server for Claude
class PtolemiesMCPServer(mcp.Server):
    def __init__(self):
        super().__init__("ptolemies-knowledge")
        
        # Register available tools
        self.register_tool("search_knowledge", self.search_knowledge)
        self.register_tool("explore_relationships", self.explore_relationships)
        self.register_tool("analyze_timeline", self.analyze_timeline)
        self.register_tool("get_quality_metrics", self.get_quality_metrics)
    
    async def search_knowledge(self, query: str, domain: str = None, limit: int = 5):
        """Search the Ptolemies knowledge base for relevant information"""
        # Implementation connects to SurrealDB and returns relevant documents
        pass
    
    async def explore_relationships(self, entity1: str, entity2: str, max_depth: int = 3):
        """Find relationships between two entities in the knowledge graph"""
        # Implementation uses Neo4j to find connection paths
        pass
    
    async def analyze_timeline(self, start_date: str, end_date: str):
        """Analyze knowledge evolution over time"""
        # Implementation queries Graphiti for temporal episodes
        pass
    
    async def get_quality_metrics(self, entity_id: str):
        """Get quality metrics and metadata for specific entity"""
        # Implementation returns quality scores and validation data
        pass
```

### Custom Agent Integration

```python
#!/usr/bin/env python3
"""
Custom AI Agent using Ptolemies MCP Server
Demonstrates how to build intelligent agents with knowledge graph access
"""

import asyncio
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class PtolemiesKnowledgeAgent:
    """An intelligent agent that can reason over the Ptolemies knowledge graph"""
    
    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.read, self.write = await stdio_client(self.server_params).__aenter__()
        self.session = await ClientSession(self.read, self.write).__aenter__()
        await self.session.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)
    
    async def answer_question(self, question: str) -> str:
        """Answer a question using the knowledge graph"""
        
        # Step 1: Extract key concepts from the question
        concepts = await self._extract_concepts(question)
        
        # Step 2: Search for relevant knowledge
        knowledge = await self._gather_knowledge(concepts)
        
        # Step 3: Find relationships between concepts
        relationships = await self._find_relationships(concepts)
        
        # Step 4: Synthesize answer
        answer = await self._synthesize_answer(question, knowledge, relationships)
        
        return answer
    
    async def _extract_concepts(self, question: str) -> List[str]:
        """Extract key concepts from a natural language question"""
        # Use semantic search to find relevant entities
        result = await self.session.call_tool(
            "concept_extraction",
            {"text": question, "max_concepts": 5}
        )
        return [concept['name'] for concept in result.content]
    
    async def _gather_knowledge(self, concepts: List[str]) -> List[Dict[str, Any]]:
        """Gather relevant knowledge for the concepts"""
        knowledge = []
        
        for concept in concepts:
            result = await self.session.call_tool(
                "semantic_search",
                {
                    "query": concept,
                    "limit": 3,
                    "min_quality": 0.7,
                    "include_context": True
                }
            )
            knowledge.extend(result.content)
        
        return knowledge
    
    async def _find_relationships(self, concepts: List[str]) -> List[Dict[str, Any]]:
        """Find relationships between the extracted concepts"""
        relationships = []
        
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                result = await self.session.call_tool(
                    "find_relationships",
                    {
                        "entity1": concept1,
                        "entity2": concept2,
                        "max_depth": 2
                    }
                )
                relationships.extend(result.content)
        
        return relationships
    
    async def _synthesize_answer(self, question: str, knowledge: List[Dict], 
                                relationships: List[Dict]) -> str:
        """Synthesize a comprehensive answer from gathered information"""
        
        # This would typically use an LLM to generate the answer
        # For demo purposes, we'll create a structured response
        
        answer_parts = [
            f"Based on the Ptolemies knowledge graph analysis:",
            f"",
            f"📚 Relevant Knowledge Found:",
        ]
        
        for item in knowledge[:3]:  # Top 3 most relevant
            answer_parts.extend([
                f"  • {item['title']} (Quality: {item['quality']:.1%})",
                f"    {item['summary'][:100]}...",
                f""
            ])
        
        if relationships:
            answer_parts.extend([
                f"🔗 Key Relationships:",
                f""
            ])
            
            for rel in relationships[:2]:  # Top 2 relationships
                answer_parts.extend([
                    f"  • {rel['source']} → {rel['target']}",
                    f"    Connection: {rel['relationship_type']}",
                    f"    Confidence: {rel['confidence']:.2f}",
                    f""
                ])
        
        answer_parts.extend([
            f"💡 This information comes from {len(set(item['domain'] for item in knowledge))} different domains",
            f"in the Ptolemies knowledge graph, ensuring comprehensive coverage."
        ])
        
        return "\n".join(answer_parts)

# Example usage
async def demo_intelligent_agent():
    """Demonstrate the intelligent agent capabilities"""
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/server.py"]
    )
    
    async with PtolemiesKnowledgeAgent(server_params) as agent:
        
        print("🤖 Ptolemies Intelligent Agent Demo")
        print("=" * 50)
        
        questions = [
            "How do I create interactive visualizations with real-time data?",
            "What's the best way to deploy a machine learning model as a web API?",
            "How can I implement authentication in a modern web application?",
            "What are the differences between document and graph databases?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n{i}. Question: {question}")
            print("-" * 40)
            
            answer = await agent.answer_question(question)
            print(answer)
            print()

if __name__ == "__main__":
    asyncio.run(demo_intelligent_agent())
```

---

## 🔧 MCP Server Implementation

### Core Server Code

```python
#!/usr/bin/env python3
"""
Ptolemies MCP Server Implementation
Provides Model Context Protocol access to the Ptolemies Knowledge Graph
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Database imports (adjust based on your setup)
from database_clients import SurrealDBClient, Neo4jClient, GraphitiClient

class PtolemiesMCPServer:
    """MCP Server for Ptolemies Knowledge Graph"""
    
    def __init__(self):
        self.server = Server("ptolemies-knowledge")
        self.surrealdb = SurrealDBClient()
        self.neo4j = Neo4jClient()
        self.graphiti = GraphitiClient()
        
        # Register all available tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all available MCP tools"""
        
        # Knowledge search tools
        self.server.register_tool(
            Tool(
                name="semantic_search",
                description="Search the knowledge base using semantic similarity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 5},
                        "min_quality": {"type": "number", "default": 0.0},
                        "domains": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["query"]
                }
            ),
            self.semantic_search
        )
        
        self.server.register_tool(
            Tool(
                name="entity_lookup",
                description="Get detailed information about a specific entity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "entity_id": {"type": "string"},
                        "include_metadata": {"type": "boolean", "default": True}
                    }
                }
            ),
            self.entity_lookup
        )
        
        # Graph analysis tools
        self.server.register_tool(
            Tool(
                name="find_relationships",
                description="Find relationships between entities in the graph",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entity1": {"type": "string"},
                        "entity2": {"type": "string"},
                        "max_depth": {"type": "integer", "default": 3},
                        "relationship_types": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["entity1", "entity2"]
                }
            ),
            self.find_relationships
        )
        
        self.server.register_tool(
            Tool(
                name="neighborhood_analysis",
                description="Analyze the local neighborhood around an entity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entity": {"type": "string"},
                        "radius": {"type": "integer", "default": 2},
                        "include_quality": {"type": "boolean", "default": True}
                    },
                    "required": ["entity"]
                }
            ),
            self.neighborhood_analysis
        )
        
        # Temporal analysis tools
        self.server.register_tool(
            Tool(
                name="timeline_query",
                description="Query temporal episodes and knowledge evolution",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "domains": {"type": "array", "items": {"type": "string"}},
                        "event_types": {"type": "array", "items": {"type": "string"}}
                    }
                }
            ),
            self.timeline_query
        )
    
    async def semantic_search(self, query: str, limit: int = 5, 
                             min_quality: float = 0.0, 
                             domains: Optional[List[str]] = None) -> List[TextContent]:
        """Perform semantic search over the knowledge base"""
        
        # Build search query for SurrealDB
        search_params = {
            "query": query,
            "limit": limit,
            "min_quality": min_quality
        }
        
        if domains:
            search_params["domains"] = domains
        
        # Execute search
        results = await self.surrealdb.semantic_search(**search_params)
        
        # Format results for MCP
        content = []
        for result in results:
            content.append(TextContent(
                type="text",
                text=json.dumps({
                    "title": result.get("title", ""),
                    "domain": result.get("domain", ""),
                    "quality": result.get("quality_score", 0.0),
                    "summary": result.get("summary", ""),
                    "url": result.get("url", ""),
                    "relevance_score": result.get("relevance", 0.0)
                }, indent=2)
            ))
        
        return content
    
    async def entity_lookup(self, name: Optional[str] = None, 
                           entity_id: Optional[str] = None,
                           include_metadata: bool = True) -> List[TextContent]:
        """Look up detailed information about an entity"""
        
        if entity_id:
            entity = await self.surrealdb.get_entity_by_id(entity_id)
        elif name:
            entity = await self.surrealdb.get_entity_by_name(name)
        else:
            raise ValueError("Either name or entity_id must be provided")
        
        if not entity:
            return [TextContent(type="text", text="Entity not found")]
        
        # Get additional metadata if requested
        if include_metadata:
            metadata = await self.neo4j.get_entity_metadata(entity["id"])
            entity.update(metadata)
        
        return [TextContent(
            type="text",
            text=json.dumps(entity, indent=2)
        )]
    
    async def find_relationships(self, entity1: str, entity2: str, 
                                max_depth: int = 3,
                                relationship_types: Optional[List[str]] = None) -> List[TextContent]:
        """Find relationships between two entities"""
        
        # Use Neo4j to find paths between entities
        paths = await self.neo4j.find_paths(
            entity1, entity2, max_depth, relationship_types
        )
        
        content = []
        for path in paths:
            content.append(TextContent(
                type="text",
                text=json.dumps({
                    "path": path["path_description"],
                    "relationship_type": path["relationship_type"],
                    "confidence": path["confidence"],
                    "distance": path["distance"],
                    "intermediate_nodes": path["intermediate_nodes"]
                }, indent=2)
            ))
        
        return content
    
    async def neighborhood_analysis(self, entity: str, radius: int = 2,
                                   include_quality: bool = True) -> List[TextContent]:
        """Analyze the local neighborhood around an entity"""
        
        # Get neighborhood from Neo4j
        neighborhood = await self.neo4j.get_neighborhood(
            entity, radius, include_quality
        )
        
        content = []
        for neighbor in neighborhood:
            neighbor_info = {
                "name": neighbor["name"],
                "distance": neighbor["distance"],
                "degree": neighbor["degree"],
                "domain": neighbor["domain"]
            }
            
            if include_quality:
                neighbor_info["quality"] = neighbor.get("quality", 0.0)
            
            content.append(TextContent(
                type="text",
                text=json.dumps(neighbor_info, indent=2)
            ))
        
        return content
    
    async def timeline_query(self, start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            domains: Optional[List[str]] = None,
                            event_types: Optional[List[str]] = None) -> List[TextContent]:
        """Query temporal episodes and knowledge evolution"""
        
        # Query Graphiti for temporal episodes
        episodes = await self.graphiti.get_episodes(
            start_date=start_date,
            end_date=end_date,
            domains=domains,
            event_types=event_types
        )
        
        content = []
        for episode in episodes:
            content.append(TextContent(
                type="text",
                text=json.dumps({
                    "timestamp": episode["timestamp"],
                    "event_type": episode["event_type"],
                    "domain": episode["domain"],
                    "description": episode["description"],
                    "entities_involved": episode["entities"],
                    "impact_score": episode.get("impact_score", 0.0)
                }, indent=2)
            ))
        
        return content
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

# Main execution
async def main():
    """Main entry point for the MCP server"""
    server = PtolemiesMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📋 Testing and Validation

### MCP Server Testing Script

```python
#!/usr/bin/env python3
"""
Test script for Ptolemies MCP Server
Validates all tools and functionality
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_server():
    """Comprehensive test of MCP server functionality"""
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            await session.initialize()
            
            print("🧪 Ptolemies MCP Server Test Suite")
            print("=" * 50)
            
            # Test 1: Semantic Search
            print("\n1. Testing semantic search...")
            try:
                result = await session.call_tool(
                    "semantic_search",
                    {"query": "machine learning", "limit": 3}
                )
                print(f"✅ Semantic search: {len(result.content)} results")
            except Exception as e:
                print(f"❌ Semantic search failed: {e}")
            
            # Test 2: Entity Lookup
            print("\n2. Testing entity lookup...")
            try:
                result = await session.call_tool(
                    "entity_lookup",
                    {"name": "PyTorch", "include_metadata": True}
                )
                print(f"✅ Entity lookup: Found entity")
            except Exception as e:
                print(f