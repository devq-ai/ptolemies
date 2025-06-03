#!/usr/bin/env python3
"""
Standalone Web Graph Explorer for Ptolemies

This creates a web interface for exploring the Ptolemies knowledge graph
that's accessible via browser at http://localhost:8080

Features:
- Interactive D3.js graph visualization
- Search and exploration capabilities
- Real-time data from hybrid storage system
- Temporal evolution tracking
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ptolemies.integrations.hybrid_storage import HybridKnowledgeManager
from ptolemies.integrations.graphiti.service_wrapper import GraphitiServiceConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_explorer")

# Global hybrid manager
manager: HybridKnowledgeManager = None

app = FastAPI(title="Ptolemies Knowledge Graph Explorer", version="1.0.0")

async def get_manager():
    """Get or create hybrid manager."""
    global manager
    if not manager:
        config = GraphitiServiceConfig()
        manager = HybridKnowledgeManager(graphiti_config=config)
        await manager.initialize()
        logger.info("Hybrid manager initialized for web explorer")
    return manager

@app.get("/", response_class=HTMLResponse)
async def graph_explorer():
    """Serve the main graph explorer interface."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ptolemies Knowledge Graph Explorer</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .controls {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        
        .search-section {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .search-input {
            flex: 1;
            min-width: 300px;
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #e1e5e9;
            border-radius: 25px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .search-input:focus {
            border-color: #4CAF50;
        }
        
        .btn {
            padding: 12px 25px;
            font-size: 16px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 500;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
            color: white;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .options {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .option-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .option-group label {
            font-weight: 500;
            color: #555;
        }
        
        .graph-container {
            height: 700px;
            position: relative;
            background: #fff;
            border-bottom: 1px solid #dee2e6;
        }
        
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 18px;
            color: #666;
        }
        
        .stats-panel {
            padding: 30px;
            background: #f8f9fa;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .node {
            stroke: #fff;
            stroke-width: 2px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .node:hover {
            stroke-width: 3px;
            r: 8;
        }
        
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
            stroke-width: 2px;
        }
        
        .node-label {
            font-size: 12px;
            font-weight: 500;
            text-anchor: middle;
            fill: #333;
            pointer-events: none;
        }
        
        .tooltip {
            position: absolute;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        @media (max-width: 768px) {
            .search-section {
                flex-direction: column;
            }
            
            .search-input {
                min-width: 100%;
            }
            
            .options {
                flex-direction: column;
                align-items: stretch;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Ptolemies Knowledge Graph</h1>
            <p>Explore temporal relationships and knowledge evolution</p>
        </div>
        
        <div class="controls">
            <div class="search-section">
                <input type="text" id="searchInput" class="search-input" 
                       placeholder="Enter a concept to explore (e.g., 'machine learning', 'AI', 'neural networks')...">
                <button onclick="exploreGraph()" class="btn btn-primary">🔍 Explore</button>
                <button onclick="searchKnowledge()" class="btn btn-secondary">📚 Search</button>
            </div>
            
            <div class="options">
                <div class="option-group">
                    <label for="depthSlider">Depth:</label>
                    <input type="range" id="depthSlider" min="1" max="5" value="3">
                    <span id="depthValue">3</span>
                </div>
                
                <div class="option-group">
                    <label for="layoutSelect">Layout:</label>
                    <select id="layoutSelect">
                        <option value="force">Force</option>
                        <option value="hierarchical">Hierarchical</option>
                        <option value="circular">Circular</option>
                    </select>
                </div>
                
                <div class="option-group">
                    <input type="checkbox" id="includeDocuments" checked>
                    <label for="includeDocuments">Include Documents</label>
                </div>
            </div>
        </div>
        
        <div class="graph-container" id="graphContainer">
            <div class="loading">
                🌟 Enter a concept above to start exploring the knowledge graph
            </div>
        </div>
        
        <div class="stats-panel">
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card">
                    <div class="stat-number" id="nodeCount">-</div>
                    <div class="stat-label">Nodes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="linkCount">-</div>
                    <div class="stat-label">Relationships</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="documentsCount">-</div>
                    <div class="stat-label">Documents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="searchTime">-</div>
                    <div class="stat-label">Search Time (ms)</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip"></div>

    <script>
        // Update depth display
        document.getElementById('depthSlider').addEventListener('input', function(e) {
            document.getElementById('depthValue').textContent = e.target.value;
        });
        
        // Graph visualization variables
        let svg, simulation, nodes, links;
        
        async function exploreGraph() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) {
                alert('Please enter a concept to explore');
                return;
            }
            
            const depth = document.getElementById('depthSlider').value;
            const layout = document.getElementById('layoutSelect').value;
            const includeDocuments = document.getElementById('includeDocuments').checked;
            
            showLoading('Exploring knowledge graph...');
            
            try {
                const response = await fetch('/api/explore', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        query: query,
                        depth: parseInt(depth),
                        layout: layout,
                        include_documents: includeDocuments
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    visualizeGraph(data);
                    updateStats(data);
                } else {
                    showError('Graph exploration failed: ' + (data.detail || 'Unknown error'));
                }
            } catch (error) {
                showError('Failed to connect to Ptolemies backend: ' + error.message);
            }
        }
        
        async function searchKnowledge() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) {
                alert('Please enter a search query');
                return;
            }
            
            showLoading('Searching knowledge base...');
            
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        query: query,
                        limit: 20,
                        include_documents: true,
                        include_entities: true,
                        include_relationships: true
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    displaySearchResults(data);
                } else {
                    showError('Search failed: ' + (data.detail || 'Unknown error'));
                }
            } catch (error) {
                showError('Failed to connect to Ptolemies backend: ' + error.message);
            }
        }
        
        function visualizeGraph(data) {
            const container = document.getElementById('graphContainer');
            container.innerHTML = '';
            
            const width = container.clientWidth;
            const height = container.clientHeight;
            
            svg = d3.select('#graphContainer')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            // Create mock graph data for demonstration
            const graphData = {
                nodes: data.nodes || generateMockNodes(data.exploration_query),
                links: data.edges || generateMockLinks()
            };
            
            // Create force simulation
            simulation = d3.forceSimulation(graphData.nodes)
                .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2));
            
            // Add links
            const link = svg.selectAll('.link')
                .data(graphData.links)
                .enter().append('line')
                .attr('class', 'link');
            
            // Add nodes
            const node = svg.selectAll('.node')
                .data(graphData.nodes)
                .enter().append('circle')
                .attr('class', 'node')
                .attr('r', d => d.size || 6)
                .attr('fill', d => d.color || '#4CAF50')
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            
            // Add labels
            const label = svg.selectAll('.node-label')
                .data(graphData.nodes)
                .enter().append('text')
                .attr('class', 'node-label')
                .text(d => d.label || d.id);
            
            // Add tooltips
            node.on('mouseover', function(event, d) {
                const tooltip = document.getElementById('tooltip');
                tooltip.style.opacity = 1;
                tooltip.style.left = (event.pageX + 10) + 'px';
                tooltip.style.top = (event.pageY - 10) + 'px';
                tooltip.innerHTML = `
                    <strong>${d.label || d.id}</strong><br>
                    Type: ${d.type || 'Node'}<br>
                    ${d.document_references ? `Documents: ${d.document_references.length}` : ''}
                `;
            }).on('mouseout', function() {
                document.getElementById('tooltip').style.opacity = 0;
            });
            
            // Update positions on simulation tick
            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
                
                label
                    .attr('x', d => d.x)
                    .attr('y', d => d.y + 4);
            });
        }
        
        function generateMockNodes(query) {
            return [
                { id: query, label: query, type: 'query', color: '#FF6B6B', size: 10 },
                { id: 'related1', label: 'Related Concept 1', type: 'concept', color: '#4ECDC4', size: 8 },
                { id: 'related2', label: 'Related Concept 2', type: 'concept', color: '#45B7D1', size: 8 },
                { id: 'doc1', label: 'Document 1', type: 'document', color: '#96CEB4', size: 6 },
                { id: 'doc2', label: 'Document 2', type: 'document', color: '#96CEB4', size: 6 }
            ];
        }
        
        function generateMockLinks() {
            return [
                { source: 'related1', target: 'related2' },
                { source: 'related1', target: 'doc1' },
                { source: 'related2', target: 'doc2' }
            ];
        }
        
        function displaySearchResults(data) {
            const container = document.getElementById('graphContainer');
            container.innerHTML = `
                <div style="padding: 30px; overflow-y: auto; height: 100%;">
                    <h3>🔍 Search Results for "${data.query}"</h3>
                    <p><strong>Total Results:</strong> ${data.total_results} 
                       <strong>Processing Time:</strong> ${(data.processing_time * 1000).toFixed(1)}ms</p>
                    
                    ${data.documents && data.documents.length > 0 ? `
                        <h4>📄 Documents (${data.documents.length})</h4>
                        ${data.documents.map(doc => `
                            <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #4CAF50;">
                                <h5 style="margin: 0 0 10px 0; color: #2c3e50;">${doc.title}</h5>
                                <p style="margin: 5px 0; color: #666; line-height: 1.4;">${doc.content_preview}</p>
                                <div style="margin-top: 10px;">
                                    <small style="color: #888;">
                                        Source: ${doc.source || 'Unknown'} | 
                                        Tags: ${doc.tags.join(', ') || 'None'} |
                                        Created: ${doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Unknown'}
                                    </small>
                                </div>
                            </div>
                        `).join('')}
                    ` : ''}
                    
                    ${data.entities && data.entities.length > 0 ? `
                        <h4>🔗 Entities (${data.entities.length})</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                            ${data.entities.map(entity => `
                                <span style="background: #e3f2fd; padding: 5px 10px; border-radius: 15px; font-size: 0.9em;">
                                    ${entity.name || entity.id}
                                </span>
                            `).join('')}
                        </div>
                    ` : ''}
                    
                    ${data.relationships && data.relationships.length > 0 ? `
                        <h4>🔀 Relationships (${data.relationships.length})</h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
                            ${data.relationships.map(rel => `
                                <div style="background: #fff3e0; padding: 10px; border-radius: 8px; border: 1px solid #ffcc02;">
                                    <strong>${rel.source || rel.id}</strong> 
                                    → <em>${rel.type || 'related_to'}</em> → 
                                    <strong>${rel.target || 'target'}</strong>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        function updateStats(data) {
            document.getElementById('nodeCount').textContent = data.graph_data?.nodes?.length || data.nodes?.length || 0;
            document.getElementById('linkCount').textContent = data.graph_data?.edges?.length || data.edges?.length || 0;
            document.getElementById('documentsCount').textContent = data.total_results || 0;
            document.getElementById('searchTime').textContent = ((data.processing_time || 0) * 1000).toFixed(0);
        }
        
        function showLoading(message) {
            document.getElementById('graphContainer').innerHTML = `
                <div class="loading">
                    <div style="animation: spin 2s linear infinite; display: inline-block;">⟳</div>
                    ${message}
                </div>
            `;
        }
        
        function showError(message) {
            document.getElementById('graphContainer').innerHTML = `
                <div class="loading" style="color: #dc3545;">
                    ❌ ${message}
                    <br><br>
                    <small>Make sure the Ptolemies system is running and try again.</small>
                </div>
            `;
        }
        
        // Drag functions
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        // Allow Enter key to search
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                exploreGraph();
            }
        });
        
        // Add CSS animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/search")
async def api_search(request: Request):
    """API endpoint for knowledge search."""
    try:
        data = await request.json()
        query = data.get("query", "")
        limit = data.get("limit", 20)
        include_documents = data.get("include_documents", True)
        include_entities = data.get("include_entities", True)
        include_relationships = data.get("include_relationships", True)
        
        manager = await get_manager()
        
        result = await manager.hybrid_search(
            query=query,
            limit=limit,
            include_documents=include_documents,
            include_entities=include_entities,
            include_relationships=include_relationships
        )
        
        # Convert datetime objects to strings before serialization
        result_dict = result.to_dict()
        
        # Fix datetime serialization in documents
        if 'documents' in result_dict:
            for doc in result_dict['documents']:
                if 'created_at' in doc and doc['created_at']:
                    doc['created_at'] = doc['created_at'].isoformat() if hasattr(doc['created_at'], 'isoformat') else str(doc['created_at'])
        
        return JSONResponse(content=result_dict)
        
    except Exception as e:
        logger.error(f"Search API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/explore")
async def api_explore(request: Request):
    """API endpoint for graph exploration."""
    try:
        data = await request.json()
        query = data.get("query", "")
        depth = data.get("depth", 3)
        layout = data.get("layout", "force")
        include_documents = data.get("include_documents", True)
        
        manager = await get_manager()
        
        viz_data = await manager.get_graph_visualization(
            query=query,
            depth=depth,
            layout=layout
        )
        
        # Add exploration metadata
        response = {
            "exploration_query": query,
            "graph_data": viz_data,
            "nodes": viz_data.get("nodes", []),
            "edges": viz_data.get("edges", []),
            "exploration_stats": {
                "nodes": len(viz_data.get("nodes", [])),
                "edges": len(viz_data.get("edges", [])),
                "depth": depth,
                "layout": layout
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Explore API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def api_stats():
    """API endpoint for system statistics."""
    try:
        manager = await get_manager()
        
        # Get basic stats
        documents = await manager.surrealdb_client.list_knowledge_items(limit=1000)
        
        stats = {
            "timestamp": "2025-06-02T00:15:00Z",
            "total_documents": len(documents),
            "storage_systems": {
                "surrealdb": {"status": "active", "documents": len(documents)},
                "graphiti": {"status": "active", "service_url": "http://localhost:8001"}
            },
            "integration_status": "hybrid_active"
        }
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Stats API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize the hybrid manager on startup."""
    logger.info("🚀 Starting Ptolemies Web Graph Explorer")
    logger.info("Visit: http://localhost:8080")

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean up on shutdown."""
    global manager
    if manager:
        await manager.close()
        logger.info("Hybrid manager closed")

if __name__ == "__main__":
    print("🌐 Starting Ptolemies Knowledge Graph Explorer")
    print("🚀 Visit: http://localhost:8080")
    print("📊 Neo4j Browser: http://localhost:7474")
    print("⚙️ Graphiti Service: http://localhost:8001")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )