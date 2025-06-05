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
- Updated with Midnight UI Dark Palette design system
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Logfire if available
logfire_initialized = False
try:
    import logfire
    
    # Initialize Logfire if token is available
    logfire_token = os.getenv("LOGFIRE_TOKEN")
    if logfire_token:
        logfire.configure(
            token=logfire_token,
            service_name=os.getenv("LOGFIRE_SERVICE_NAME", "ptolemies-web-explorer"),
            environment=os.getenv("LOGFIRE_ENVIRONMENT", "development")
        )
        logfire_initialized = True
        logging.info("Logfire initialized successfully")
    else:
        logging.info("Logfire token not found, running without Logfire")
except ImportError:
    logging.info("Logfire not installed, running without observability")
    logfire = None

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ptolemies.integrations.hybrid_storage import HybridKnowledgeManager
from ptolemies.integrations.graphiti.service_wrapper import GraphitiServiceConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_explorer")

# Log initialization status
if logfire_initialized:
    logger.info("Web Graph Explorer starting with Logfire observability")
else:
    logger.info("Web Graph Explorer starting without Logfire")

# Global hybrid manager
manager: HybridKnowledgeManager = None

app = FastAPI(title="Ptolemies Knowledge Graph Explorer", version="1.0.0")

# Instrument FastAPI with Logfire if available
if logfire and logfire_initialized:
    logfire.instrument_fastapi(app)
    logger.info("FastAPI instrumented with Logfire")

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
    if logfire:
        logfire.info("Graph explorer main page accessed")
    
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ptolemies Knowledge Graph Explorer</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        /* Midnight UI (Elegant & Minimal) Dark Palette */
        :root {
            --primary: #1B03A3;      /* Neon Blue */
            --secondary: #9D00FF;    /* Neon Purple */
            --accent: #FF10F0;       /* Neon Pink */
            --error: #FF3131;        /* Neon Red */
            --success: #39FF14;      /* Neon Green */
            --warning: #E9FF32;      /* Neon Yellow */
            --info: #00FFFF;         /* Neon Cyan */
            --primary-fg: #E3E3E3;   /* Soft White */
            --secondary-fg: #A3A3A3; /* Stone Grey */
            --disabled-fg: #606770;  /* Neutral Grey */
            --primary-bg: #010B13;   /* Rich Black */
            --secondary-bg: #0F1111; /* Charcoal Black */
            --surface-bg: #1A1A1A;   /* Midnight Black */
            --overlay: #121212AA;    /* Transparent Dark */
        }

        body {
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: var(--primary-bg);
            background-image: 
                radial-gradient(circle at 20% 80%, var(--primary) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, var(--secondary) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, var(--accent) 0%, transparent 50%);
            color: var(--primary-fg);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: var(--surface-bg);
            border-radius: 15px;
            border: 1px solid var(--disabled-fg);
            box-shadow: 
                0 0 20px rgba(27, 3, 163, 0.3),
                0 0 40px rgba(157, 0, 255, 0.2),
                0 20px 40px rgba(0, 0, 0, 0.4);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: var(--primary-fg);
            padding: 30px;
            text-align: center;
            border-bottom: 2px solid var(--accent);
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
            text-shadow: 0 0 10px var(--accent);
        }
        
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .controls {
            padding: 30px;
            background: var(--secondary-bg);
            border-bottom: 1px solid var(--disabled-fg);
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
            background: var(--surface-bg);
            color: var(--primary-fg);
            border: 2px solid var(--disabled-fg);
            border-radius: 8px;
            outline: none;
            transition: all 0.3s;
        }
        
        .search-input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 10px rgba(255, 16, 240, 0.5);
        }
        
        .search-input::placeholder {
            color: var(--secondary-fg);
        }
        
        .btn {
            padding: 12px 25px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: var(--primary-fg);
            border: 1px solid var(--accent);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, var(--info) 0%, var(--success) 100%);
            color: var(--primary-bg);
            border: 1px solid var(--info);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px var(--overlay);
            filter: brightness(1.2);
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
            color: var(--primary-fg);
        }
        
        .option-group input[type="range"] {
            background: var(--disabled-fg);
            border-radius: 5px;
        }
        
        .option-group select {
            background: var(--surface-bg);
            color: var(--primary-fg);
            border: 1px solid var(--disabled-fg);
            border-radius: 5px;
            padding: 5px 10px;
        }
        
        .option-group input[type="checkbox"] {
            accent-color: var(--accent);
        }
        
        .graph-container {
            height: 700px;
            position: relative;
            background: var(--primary-bg);
            background-image: 
                radial-gradient(circle at 10% 20%, var(--primary) 0%, transparent 30%),
                radial-gradient(circle at 90% 80%, var(--secondary) 0%, transparent 30%);
            border-bottom: 1px solid var(--disabled-fg);
        }
        
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 18px;
            color: var(--primary-fg);
            text-align: center;
        }
        
        .stats-panel {
            padding: 30px;
            background: var(--secondary-bg);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .stat-card {
            background: var(--surface-bg);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid var(--disabled-fg);
            box-shadow: 0 2px 10px var(--overlay);
            text-align: center;
            transition: all 0.3s;
        }
        
        .stat-card:hover {
            border-color: var(--accent);
            box-shadow: 0 4px 20px rgba(255, 16, 240, 0.2);
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: var(--success);
            text-shadow: 0 0 5px var(--success);
        }
        
        .stat-label {
            color: var(--secondary-fg);
            margin-top: 5px;
        }
        
        .node {
            stroke: var(--primary-fg);
            stroke-width: 2px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .node:hover {
            stroke-width: 3px;
            r: 8;
            filter: brightness(1.3);
        }
        
        .link {
            stroke: var(--disabled-fg);
            stroke-opacity: 0.6;
            stroke-width: 2px;
        }
        
        .node-label {
            font-size: 12px;
            font-weight: 500;
            text-anchor: middle;
            fill: var(--primary-fg);
            pointer-events: none;
        }
        
        .tooltip {
            position: absolute;
            background: var(--surface-bg);
            color: var(--primary-fg);
            border: 1px solid var(--accent);
            padding: 10px;
            border-radius: 8px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
            box-shadow: 0 4px 20px var(--overlay);
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
            
            // Create mock graph data for demonstration with design system colors
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
                .attr('fill', d => d.color || '#FF10F0')
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
                { id: query, label: query, type: 'query', color: '#FF10F0', size: 10 },
                { id: 'related1', label: 'Related Concept 1', type: 'concept', color: '#00FFFF', size: 8 },
                { id: 'related2', label: 'Related Concept 2', type: 'concept', color: '#1B03A3', size: 8 },
                { id: 'doc1', label: 'Document 1', type: 'document', color: '#39FF14', size: 6 },
                { id: 'doc2', label: 'Document 2', type: 'document', color: '#39FF14', size: 6 }
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
                <div style="padding: 30px; overflow-y: auto; height: 100%; background: var(--surface-bg); color: var(--primary-fg);">
                    <h3 style="color: var(--primary-fg);">🔍 Search Results for "${data.query}"</h3>
                    <p><strong>Total Results:</strong> ${data.total_results} 
                       <strong>Processing Time:</strong> ${(data.processing_time * 1000).toFixed(1)}ms</p>
                    
                    ${data.documents && data.documents.length > 0 ? `
                        <h4 style="color: var(--primary-fg);">📄 Documents (${data.documents.length})</h4>
                        ${data.documents.map(doc => `
                            <div style="background: var(--surface-bg); padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid var(--success); border: 1px solid var(--disabled-fg);">
                                <h5 style="margin: 0 0 10px 0; color: var(--primary-fg);">${doc.title}</h5>
                                <p style="margin: 5px 0; color: var(--secondary-fg); line-height: 1.4;">${doc.content_preview}</p>
                                <div style="margin-top: 10px;">
                                    <small style="color: var(--disabled-fg);">
                                        Source: ${doc.source || 'Unknown'} | 
                                        Tags: ${doc.tags.join(', ') || 'None'} |
                                        Created: ${doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Unknown'}
                                    </small>
                                </div>
                            </div>
                        `).join('')}
                    ` : ''}
                    
                    ${data.entities && data.entities.length > 0 ? `
                        <h4 style="color: var(--primary-fg);">🔗 Entities (${data.entities.length})</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                            ${data.entities.map(entity => `
                                <span style="background: var(--surface-bg); color: var(--info); border: 1px solid var(--info); padding: 5px 10px; border-radius: 15px; font-size: 0.9em;">
                                    ${entity.name || entity.id}
                                </span>
                            `).join('')}
                        </div>
                    ` : ''}
                    
                    ${data.relationships && data.relationships.length > 0 ? `
                        <h4 style="color: var(--primary-fg);">🔀 Relationships (${data.relationships.length})</h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
                            ${data.relationships.map(rel => `
                                <div style="background: var(--surface-bg); color: var(--primary-fg); padding: 10px; border-radius: 8px; border: 1px solid var(--warning);">
                                    <strong style="color: var(--accent);">${rel.source || rel.id}</strong> 
                                    → <em style="color: var(--warning);">${rel.type || 'related_to'}</em> → 
                                    <strong style="color: var(--secondary);">${rel.target || 'target'}</strong>
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
                <div class="loading" style="color: var(--error);">
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
        
        if logfire:
            with logfire.span("hybrid_search", query=query, limit=limit):
                manager = await get_manager()
                
                result = await manager.hybrid_search(
                    query=query,
                    limit=limit,
                    include_documents=include_documents,
                    include_entities=include_entities,
                    include_relationships=include_relationships
                )
                
                logfire.info("Search completed",
                           query=query,
                           document_count=len(result.documents) if hasattr(result, 'documents') else 0,
                           entity_count=len(result.entities) if hasattr(result, 'entities') else 0,
                           relationship_count=len(result.relationships) if hasattr(result, 'relationships') else 0,
                           processing_time=result.processing_time if hasattr(result, 'processing_time') else None)
        else:
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
        if logfire:
            logfire.error("Search API error",
                         error_type=type(e).__name__,
                         error_message=str(e),
                         query=query if 'query' in locals() else None)
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
        
        if logfire:
            with logfire.span("graph_exploration", query=query, depth=depth, layout=layout):
                manager = await get_manager()
                
                viz_data = await manager.get_graph_visualization(
                    query=query,
                    depth=depth,
                    layout=layout
                )
                
                node_count = len(viz_data.get("nodes", []))
                edge_count = len(viz_data.get("edges", []))
                
                logfire.info("Graph exploration completed",
                           query=query,
                           depth=depth,
                           layout=layout,
                           node_count=node_count,
                           edge_count=edge_count)
        else:
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
        if logfire:
            logfire.error("Explore API error",
                         error_type=type(e).__name__,
                         error_message=str(e),
                         query=query if 'query' in locals() else None)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def api_stats():
    """API endpoint for system statistics."""
    if logfire:
        logfire.info("System stats requested")
    
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
            "integration_status": "hybrid_active",
            "logfire": "enabled" if logfire_initialized else "disabled"
        }
        
        if logfire:
            logfire.info("System stats retrieved",
                       total_documents=len(documents),
                       storage_active=True)
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Stats API error: {str(e)}")
        if logfire:
            logfire.error("Stats API error",
                         error_type=type(e).__name__,
                         error_message=str(e))
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