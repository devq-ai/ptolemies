
def create_real_graph_visualization(driver, query: str = "", depth: int = 2):
    """Create real graph visualization from Neo4j data"""
    # FIXED_VIZ - Return actual graph data instead of mock data
    
    try:
        with driver.session() as session:
            # Get actual entities and relationships
            if query:
                # Search for entities related to the query
                cypher_query = """
                    MATCH (e:Entity)
                    WHERE toLower(e.name) CONTAINS toLower($query) 
                       OR toLower(e.summary) CONTAINS toLower($query)
                    WITH e
                    LIMIT 20
                    
                    OPTIONAL MATCH (e)-[r:RELATES_TO]-(connected:Entity)
                    
                    RETURN e, r, connected
                """
                result = session.run(cypher_query, query=query)
            else:
                # Get a sample of the graph
                cypher_query = """
                    MATCH (e:Entity)
                    WITH e
                    LIMIT 10
                    
                    OPTIONAL MATCH (e)-[r:RELATES_TO]-(connected:Entity)
                    
                    RETURN e, r, connected
                """
                result = session.run(cypher_query)
            
            nodes = {}
            edges = []
            
            for record in result:
                entity = record.get('e')
                relationship = record.get('r')
                connected = record.get('connected')
                
                if entity:
                    nodes[entity['uuid']] = {
                        "id": entity['uuid'],
                        "label": entity['name'],
                        "type": "entity", 
                        "size": 1.0,
                        "color": "#1f77b4",
                        "summary": entity.get('summary', ''),
                        "group_id": entity.get('group_id', '')
                    }
                
                if connected:
                    nodes[connected['uuid']] = {
                        "id": connected['uuid'],
                        "label": connected['name'],
                        "type": "entity",
                        "size": 1.0, 
                        "color": "#ff7f0e",
                        "summary": connected.get('summary', ''),
                        "group_id": connected.get('group_id', '')
                    }
                
                if relationship and entity and connected:
                    edges.append({
                        "id": relationship['uuid'],
                        "source": entity['uuid'],
                        "target": connected['uuid'], 
                        "label": relationship['name'],
                        "fact": relationship.get('fact', ''),
                        "weight": 1.0
                    })
            
            return {
                "nodes": list(nodes.values()),
                "edges": edges,
                "metadata": {
                    "query": query,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "data_source": "real_neo4j_data"
                }
            }
            
    except Exception as e:
        print(f"Error creating real visualization: {e}")
        # Fallback to basic mock data
        return {
            "nodes": [{"id": "error", "label": "Visualization Error", "type": "error"}],
            "edges": [],
            "metadata": {"error": str(e)}
        }


"""
Visual Knowledge Graph component for Ptolemies-Graphiti integration.

This module provides interactive graph visualization capabilities using Graphiti's
knowledge graph data. Supports real-time exploration, temporal visualization,
and conflict detection through web-based interfaces.

References:
- Graphiti Visualization: https://github.com/getzep/graphiti#visualization
- Neo4j Graph Visualization: https://neo4j.com/docs/browser-manual/current/
- D3.js Force-Directed Graphs: https://d3js.org/d3-force
"""

import json
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# from .client import GraphitiIntegrationClient

# Configure logging
logger = logging.getLogger(__name__)

class GraphVisualizationConfig(BaseModel):
    """Configuration for graph visualization."""
    max_nodes: int = Field(default=100, description="Maximum nodes to display")
    max_edges: int = Field(default=200, description="Maximum edges to display")
    layout_algorithm: str = Field(default="force", description="Layout algorithm")
    node_size_factor: float = Field(default=1.0, description="Node size multiplier")
    edge_width_factor: float = Field(default=1.0, description="Edge width multiplier")
    temporal_window_hours: int = Field(default=24, description="Temporal visualization window")

class GraphNode(BaseModel):
    """Graph node for visualization."""
    id: str = Field(description="Unique node identifier")
    label: str = Field(description="Display label")
    type: str = Field(description="Node type/category")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    size: float = Field(default=1.0, description="Visual size")
    color: str = Field(default="#1f77b4", description="Node color")
    x: Optional[float] = Field(None, description="X coordinate for layout")
    y: Optional[float] = Field(None, description="Y coordinate for layout")

class GraphEdge(BaseModel):
    """Graph edge for visualization."""
    id: str = Field(description="Unique edge identifier") 
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    label: str = Field(description="Relationship label")
    weight: float = Field(default=1.0, description="Edge weight")
    color: str = Field(default="#999999", description="Edge color")
    width: float = Field(default=1.0, description="Edge width")
    temporal_validity: Optional[Dict[str, Any]] = Field(None, description="Temporal validity")

class GraphVisualizationData(BaseModel):
    """Complete graph visualization data."""
    nodes: List[GraphNode] = Field(description="Graph nodes")
    edges: List[GraphEdge] = Field(description="Graph edges") 
    metadata: Dict[str, Any] = Field(description="Graph metadata")
    layout: str = Field(default="force", description="Layout algorithm used")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VisualKnowledgeGraph:
    """
    Interactive visual knowledge graph interface.
    
    Provides methods for generating interactive graph visualizations from
    Graphiti's temporal knowledge graph data with support for:
    - Real-time graph exploration
    - Temporal evolution visualization
    - Conflict detection and highlighting
    - Custom filtering and layout options
    """
    
    def __init__(
        self,
        graphiti_client: GraphitiIntegrationClient,
        config: Optional[GraphVisualizationConfig] = None
    ):
        """
        Initialize the visual knowledge graph.
        
        Args:
            graphiti_client: Graphiti integration client
            config: Visualization configuration
        """
        self.graphiti_client = graphiti_client
        self.config = config or GraphVisualizationConfig()
        self._node_type_colors = self._get_default_color_scheme()
        self._active_connections: List[WebSocket] = []
    
    def _get_default_color_scheme(self) -> Dict[str, str]:
        """Get default color scheme for different node types."""
        return {
            "entity": "#1f77b4",      # Blue
            "concept": "#ff7f0e",     # Orange  
            "document": "#2ca02c",    # Green
            "framework": "#d62728",   # Red
            "technology": "#9467bd",  # Purple
            "person": "#8c564b",      # Brown
            "organization": "#e377c2", # Pink
            "location": "#7f7f7f",    # Gray
            "default": "#17becf"      # Cyan
        }
    
    async def generate_graph_visualization(
        self,
        query: str,
        depth: int = 3,
        layout: str = "force",
        filter_types: Optional[List[str]] = None
    ) -> GraphVisualizationData:
        """
        Generate interactive graph visualization for query results.
        
        Args:
            query: Search query text
            depth: Graph traversal depth
            layout: Layout algorithm ("force", "circular", "hierarchical")
            filter_types: Optional node type filtering
            
        Returns:
            Complete graph visualization data
        """
        try:
            # Get graph data from Graphiti
            entities = await self.graphiti_client.search_entities(
                query=query,
                limit=self.config.max_nodes
            )
            
            relationships = await self.graphiti_client.search_relationships(
                query=query,
                limit=self.config.max_edges
            )
            
            # Convert to visualization format
            nodes = []
            edges = []
            
            # Process entities into nodes
            for entity in entities:
                if filter_types and entity.get("entity_type") not in filter_types:
                    continue
                    
                node = self._format_node(entity)
                nodes.append(node)
            
            # Process relationships into edges
            node_ids = {node.id for node in nodes}
            for relationship in relationships:
                edge = self._format_edge(relationship)
                
                # Only include edges between visible nodes
                if edge.source in node_ids and edge.target in node_ids:
                    edges.append(edge)
            
            # Apply layout if specified
            if layout != "force":
                nodes = self._apply_layout(nodes, edges, layout)
            
            # Create visualization data
            graph_data = GraphVisualizationData(
                nodes=nodes,
                edges=edges,
                metadata={
                    "query": query,
                    "depth": depth,
                    "layout": layout,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "filter_types": filter_types
                },
                layout=layout
            )
            
            logger.info(f"Generated graph visualization: {len(nodes)} nodes, {len(edges)} edges")
            return graph_data
            
        except Exception as e:
            logger.error(f"Error generating graph visualization: {str(e)}")
            raise
    
    def _format_node(self, entity: Dict[str, Any]) -> GraphNode:
        """Format entity data into a graph node."""
        entity_type = entity.get("entity_type", "default")
        
        return GraphNode(
            id=entity.get("uuid", str(uuid4())),
            label=entity.get("name", "Unknown"),
            type=entity_type,
            properties=entity.get("properties", {}),
            size=self._calculate_node_size(entity),
            color=self._node_type_colors.get(entity_type, self._node_type_colors["default"])
        )
    
    def _format_edge(self, relationship: Dict[str, Any]) -> GraphEdge:
        """Format relationship data into a graph edge."""
        return GraphEdge(
            id=relationship.get("uuid", str(uuid4())),
            source=relationship.get("source_uuid", ""),
            target=relationship.get("target_uuid", ""),
            label=relationship.get("name", "related_to"),
            weight=relationship.get("weight", 1.0),
            color=self._get_edge_color(relationship),
            width=self._calculate_edge_width(relationship),
            temporal_validity={
                "start": relationship.get("valid_at"),
                "end": relationship.get("invalid_at"),
                "current": self._is_currently_valid(relationship)
            }
        )
    
    def _calculate_node_size(self, entity: Dict[str, Any]) -> float:
        """Calculate node size based on entity properties."""
        # Base size
        base_size = 1.0
        
        # Scale by connection count if available
        connections = entity.get("connection_count", 1)
        size_factor = min(1.0 + (connections / 10), 3.0)
        
        return base_size * size_factor * self.config.node_size_factor
    
    def _calculate_edge_width(self, relationship: Dict[str, Any]) -> float:
        """Calculate edge width based on relationship strength."""
        weight = relationship.get("weight", 1.0)
        width = max(0.5, min(weight * 2, 5.0))
        return width * self.config.edge_width_factor
    
    def _get_edge_color(self, relationship: Dict[str, Any]) -> str:
        """Get edge color based on relationship type and validity."""
        if not self._is_currently_valid(relationship):
            return "#cccccc"  # Gray for invalid relationships
        
        rel_type = relationship.get("relationship_type", "")
        
        color_map = {
            "depends_on": "#ff6b6b",
            "influences": "#4ecdc4", 
            "similar_to": "#45b7d1",
            "part_of": "#96ceb4",
            "mentions": "#feca57"
        }
        
        return color_map.get(rel_type, "#999999")
    
    def _is_currently_valid(self, relationship: Dict[str, Any]) -> bool:
        """Check if relationship is currently valid."""
        now = datetime.now(timezone.utc)
        
        valid_at = relationship.get("valid_at")
        invalid_at = relationship.get("invalid_at")
        
        if valid_at and valid_at > now:
            return False
        
        if invalid_at and invalid_at <= now:
            return False
            
        return True
    
    def _apply_layout(self, nodes: List[GraphNode], edges: List[GraphEdge], layout: str) -> List[GraphNode]:
        """Apply specified layout algorithm to nodes."""
        if layout == "circular":
            return self._apply_circular_layout(nodes)
        elif layout == "hierarchical":
            return self._apply_hierarchical_layout(nodes, edges)
        else:
            return nodes  # Let frontend handle force layout
    
    def _apply_circular_layout(self, nodes: List[GraphNode]) -> List[GraphNode]:
        """Apply circular layout to nodes."""
        import math
        
        radius = max(100, len(nodes) * 5)
        center_x, center_y = 400, 300
        
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / len(nodes)
            node.x = center_x + radius * math.cos(angle)
            node.y = center_y + radius * math.sin(angle)
        
        return nodes
    
    def _apply_hierarchical_layout(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> List[GraphNode]:
        """Apply hierarchical layout based on node connections."""
        # Simple hierarchical layout - group by node type
        type_groups = {}
        for node in nodes:
            if node.type not in type_groups:
                type_groups[node.type] = []
            type_groups[node.type].append(node)
        
        y_offset = 0
        layer_height = 150
        
        for node_type, type_nodes in type_groups.items():
            x_spacing = max(800 // (len(type_nodes) + 1), 50)
            
            for i, node in enumerate(type_nodes):
                node.x = (i + 1) * x_spacing
                node.y = y_offset + layer_height // 2
            
            y_offset += layer_height
        
        return nodes
    
    async def generate_temporal_visualization(
        self,
        entity_name: str,
        timespan: Optional[Tuple[datetime, datetime]] = None
    ) -> GraphVisualizationData:
        """
        Generate temporal evolution visualization for an entity.
        
        Args:
            entity_name: Name of entity to track
            timespan: Optional time range
            
        Returns:
            Temporal graph visualization data
        """
        try:
            # Get temporal evolution data
            evolution_data = await self.graphiti_client.get_temporal_evolution(
                entity_name=entity_name,
                start_time=timespan[0] if timespan else None,
                end_time=timespan[1] if timespan else None
            )
            
            # Convert temporal data to visualization format
            nodes = []
            edges = []
            
            # Create timeline-based layout
            # Implementation would depend on specific temporal data structure
            
            return GraphVisualizationData(
                nodes=nodes,
                edges=edges,
                metadata={
                    "entity": entity_name,
                    "temporal": True,
                    "timespan": {
                        "start": timespan[0].isoformat() if timespan else None,
                        "end": timespan[1].isoformat() if timespan else None
                    }
                },
                layout="temporal"
            )
            
        except Exception as e:
            logger.error(f"Error generating temporal visualization: {str(e)}")
            raise
    
    async def generate_conflict_visualization(self, conflicts: List[Dict[str, Any]]) -> GraphVisualizationData:
        """
        Generate visualization highlighting knowledge conflicts.
        
        Args:
            conflicts: List of detected conflicts
            
        Returns:
            Conflict visualization data
        """
        try:
            nodes = []
            edges = []
            
            # Process conflicts into visual elements
            for conflict in conflicts:
                # Create nodes for conflicting entities
                source_node = GraphNode(
                    id=conflict.get("source_id", str(uuid4())),
                    label=conflict.get("source_name", "Unknown"),
                    type="conflict_source",
                    color="#ff4444",  # Red for conflicts
                    size=1.5
                )
                
                target_node = GraphNode(
                    id=conflict.get("target_id", str(uuid4())),
                    label=conflict.get("target_name", "Unknown"),
                    type="conflict_target",
                    color="#ff4444",
                    size=1.5
                )
                
                # Create conflict edge
                conflict_edge = GraphEdge(
                    id=str(uuid4()),
                    source=source_node.id,
                    target=target_node.id,
                    label="conflicts_with",
                    color="#ff0000",  # Bright red
                    width=3.0
                )
                
                nodes.extend([source_node, target_node])
                edges.append(conflict_edge)
            
            return GraphVisualizationData(
                nodes=nodes,
                edges=edges,
                metadata={
                    "visualization_type": "conflicts",
                    "conflict_count": len(conflicts)
                },
                layout="conflict"
            )
            
        except Exception as e:
            logger.error(f"Error generating conflict visualization: {str(e)}")
            raise
    
    # WebSocket management for real-time updates
    
    async def add_websocket_connection(self, websocket: WebSocket) -> None:
        """Add WebSocket connection for real-time updates."""
        await websocket.accept()
        self._active_connections.append(websocket)
        logger.info(f"Added WebSocket connection. Total: {len(self._active_connections)}")
    
    async def remove_websocket_connection(self, websocket: WebSocket) -> None:
        """Remove WebSocket connection."""
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)
            logger.info(f"Removed WebSocket connection. Total: {len(self._active_connections)}")
    
    async def broadcast_graph_update(self, update_data: Dict[str, Any]) -> None:
        """Broadcast graph update to all connected clients."""
        if not self._active_connections:
            return
        
        message = {
            "type": "graph_update",
            "data": update_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        disconnected = []
        for websocket in self._active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {str(e)}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            await self.remove_websocket_connection(websocket)

# HTML template for graph explorer interface
GRAPH_EXPLORER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ptolemies Knowledge Graph Explorer</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; background: #1a1a1a; color: white; }
        #controls { padding: 20px; background: #2a2a2a; border-bottom: 1px solid #444; }
        #graph-container { width: 100vw; height: calc(100vh - 100px); }
        .node { cursor: pointer; }
        .edge { stroke-opacity: 0.6; }
        .node-label { pointer-events: none; font-size: 12px; fill: white; }
        input, button, select { margin: 5px; padding: 8px; }
        #search-input { width: 300px; }
        .tooltip { position: absolute; background: rgba(0,0,0,0.8); color: white; 
                   padding: 10px; border-radius: 5px; pointer-events: none; }
    </style>
</head>
<body>
    <div id="controls">
        <input id="search-input" type="text" placeholder="Search knowledge graph..." />
        <button onclick="searchGraph()">Search</button>
        <select id="layout-select">
            <option value="force">Force Layout</option>
            <option value="circular">Circular Layout</option>
            <option value="hierarchical">Hierarchical Layout</option>
        </select>
        <button onclick="toggleRealtime()">Toggle Real-time</button>
        <span id="status">Ready</span>
    </div>
    <div id="graph-container"></div>
    <div id="tooltip" class="tooltip" style="display: none;"></div>

    <script>
        // D3.js graph visualization implementation
        let graph = { nodes: [], links: [] };
        let simulation;
        let svg, g;
        let websocket;
        let realtimeEnabled = false;

        function initializeGraph() {
            const container = d3.select('#graph-container');
            const width = container.node().offsetWidth;
            const height = container.node().offsetHeight;

            svg = container.append('svg')
                .attr('width', width)
                .attr('height', height);

            g = svg.append('g');

            // Add zoom behavior
            const zoom = d3.zoom()
                .scaleExtent([0.1, 3])
                .on('zoom', (event) => {
                    g.attr('transform', event.transform);
                });

            svg.call(zoom);

            // Initialize force simulation
            simulation = d3.forceSimulation()
                .force('link', d3.forceLink().id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2));
        }

        function updateGraph(data) {
            // Update graph data
            graph.nodes = data.nodes || [];
            graph.links = data.edges || [];

            // Update visualization
            const link = g.selectAll('.edge')
                .data(graph.links, d => d.id);

            link.exit().remove();

            const linkEnter = link.enter().append('line')
                .attr('class', 'edge')
                .attr('stroke', d => d.color)
                .attr('stroke-width', d => d.width);

            const node = g.selectAll('.node')
                .data(graph.nodes, d => d.id);

            node.exit().remove();

            const nodeEnter = node.enter().append('g')
                .attr('class', 'node')
                .call(d3.drag()
                    .on('start', dragStarted)
                    .on('drag', dragged)
                    .on('end', dragEnded));

            nodeEnter.append('circle')
                .attr('r', d => d.size * 10)
                .attr('fill', d => d.color)
                .on('mouseover', showTooltip)
                .on('mouseout', hideTooltip);

            nodeEnter.append('text')
                .attr('class', 'node-label')
                .attr('dy', '.35em')
                .attr('text-anchor', 'middle')
                .text(d => d.label);

            // Update simulation
            simulation.nodes(graph.nodes);
            simulation.force('link').links(graph.links);
            simulation.alpha(1).restart();

            simulation.on('tick', () => {
                linkEnter.merge(link)
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);

                nodeEnter.merge(node)
                    .attr('transform', d => `translate(${d.x},${d.y})`);
            });

            document.getElementById('status').textContent = 
                `${graph.nodes.length} nodes, ${graph.links.length} edges`;
        }

        async function searchGraph() {
            const query = document.getElementById('search-input').value;
            const layout = document.getElementById('layout-select').value;

            if (!query.trim()) return;

            try {
                document.getElementById('status').textContent = 'Searching...';
                
                const response = await fetch(
                    `/api/graph/visualize?query=${encodeURIComponent(query)}&layout=${layout}`
                );
                const result = await response.json();

                if (result.success) {
                    updateGraph(result.data);
                } else {
                    console.error('Search failed:', result);
                }
            } catch (error) {
                console.error('Search error:', error);
                document.getElementById('status').textContent = 'Search failed';
            }
        }

        function toggleRealtime() {
            if (realtimeEnabled) {
                if (websocket) {
                    websocket.close();
                    websocket = null;
                }
                realtimeEnabled = false;
                document.getElementById('status').textContent = 'Real-time disabled';
            } else {
                connectWebSocket();
                realtimeEnabled = true;
                document.getElementById('status').textContent = 'Real-time enabled';
            }
        }

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/graph/realtime`;
            
            websocket = new WebSocket(wsUrl);

            websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                if (message.type === 'graph_update') {
                    updateGraph(message.data);
                }
            };

            websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }

        function showTooltip(event, d) {
            const tooltip = document.getElementById('tooltip');
            tooltip.style.display = 'block';
            tooltip.style.left = (event.pageX + 10) + 'px';
            tooltip.style.top = (event.pageY + 10) + 'px';
            tooltip.innerHTML = `
                <strong>${d.label}</strong><br/>
                Type: ${d.type}<br/>
                Size: ${d.size}<br/>
                Properties: ${Object.keys(d.properties).length}
            `;
        }

        function hideTooltip() {
            document.getElementById('tooltip').style.display = 'none';
        }

        function dragStarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragEnded(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', initializeGraph);

        // Handle search on Enter key
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchGraph();
            }
        });
    </script>
</body>
</html>
"""