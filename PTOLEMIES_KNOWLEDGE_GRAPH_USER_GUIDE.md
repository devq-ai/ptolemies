# Ptolemies Knowledge Graph - User Guide

**Version**: 1.0  
**Date**: December 6, 2025  
**Status**: Production Ready  
**Audience**: End Users, Researchers, Developers

---

## 🎯 Overview

The Ptolemies Knowledge Graph is an interactive visualization system that provides intuitive access to a comprehensive knowledge base containing 877 high-quality documents from 7 major Python and web development domains. This guide will help you navigate, explore, and extract insights from this rich knowledge repository.

### What You'll Find Here
- **877 Knowledge Documents** across programming frameworks
- **590+ Relationships** connecting related concepts
- **7 Domain Areas** including ML, visualization, databases, and web frameworks
- **Interactive Exploration** with search, filtering, and detailed views
- **Temporal Analysis** showing knowledge evolution over time

---

## 🚀 Getting Started

### Accessing the Knowledge Graph

The Ptolemies Knowledge Graph is available through multiple interfaces:

1. **Web Interface**: Interactive browser-based visualization
2. **MCP Server**: AI agent integration for programmatic access
3. **API Endpoints**: Direct database queries for custom applications
4. **Neo4j Browser**: Advanced graph analysis for technical users

### System Requirements

- **Web Browser**: Chrome, Firefox, Safari, or Edge (latest versions)
- **Screen Resolution**: Minimum 1024x768, recommended 1920x1080
- **Internet Connection**: Required for real-time data updates
- **JavaScript**: Must be enabled

---

## 🎨 Interface Overview

### Main Components

#### 1. Graph Visualization Area
- **Central Canvas**: Interactive node-link diagram of knowledge entities
- **Zoom Controls**: Mouse wheel or touch gestures to zoom in/out
- **Pan Navigation**: Click and drag to move around the graph
- **Selection**: Click nodes or edges to select and view details

#### 2. Header Controls
- **Search Box**: Find entities by name, domain, or content keywords
- **Domain Filters**: Show/hide entities from specific knowledge domains
- **Layout Controls**: Switch between different graph layout algorithms
- **Export Options**: Save views as images or export data

#### 3. Side Panel (Details View)
- **Entity Information**: Detailed metadata about selected nodes
- **Relationship Explorer**: Connected entities and relationship types
- **Content Preview**: Snippets from source documentation
- **Quality Metrics**: Confidence scores and validation information

#### 4. Legend and Statistics
- **Color Legend**: Domain identification by color coding
- **Graph Statistics**: Real-time counts of entities and relationships
- **Selection Info**: Details about currently selected elements

---

## 🔍 Navigation and Exploration

### Basic Navigation

#### Viewing the Full Graph
1. **Initial Load**: Graph opens with overview of all domains
2. **Fit to Screen**: Double-click empty space to fit entire graph
3. **Reset View**: Use reset button to return to original layout
4. **Zoom Levels**: Zoom out for overview, zoom in for details

#### Selecting Entities
1. **Single Click**: Select individual nodes or edges
2. **Multiple Selection**: Hold Ctrl/Cmd and click multiple elements
3. **Area Selection**: Click and drag to select region (if enabled)
4. **Clear Selection**: Click empty space to deselect all

### Advanced Navigation

#### Following Relationships
1. **Explore Connections**: Click node to see immediate neighbors
2. **Path Finding**: Use "Find Path" feature between two nodes
3. **Neighborhood View**: Focus on local subgraph around selected entity
4. **Relationship Types**: Filter by specific relationship categories

#### Graph Layouts
- **Force-Directed**: Natural clustering based on relationships
- **Circular**: Domains arranged in circles for clear separation
- **Hierarchical**: Tree-like structure showing information flow
- **Grid**: Organized layout for systematic exploration

---

## 🔎 Search and Filtering

### Search Functionality

#### Basic Search
1. **Entity Names**: Search for specific technologies, frameworks, concepts
2. **Content Keywords**: Find entities related to specific topics
3. **Partial Matching**: Search works with incomplete terms
4. **Auto-suggest**: Dropdown shows matching entities as you type

#### Advanced Search Techniques
```
Examples:
- "neural networks" → Find ML-related entities
- "authentication" → Find security-related concepts
- "visualization" → Find plotting and charting tools
- "async" → Find asynchronous programming concepts
```

#### Search Operators
- **Quoted Phrases**: `"exact phrase"` for precise matching
- **Wildcards**: `tensor*` to find tensor-related terms
- **Boolean**: `python AND web` for intersection searches
- **Exclusion**: `database -nosql` to exclude specific terms

### Filtering Options

#### Domain Filters
- **All Domains**: View complete knowledge graph
- **PyTorch**: Deep learning and neural network concepts
- **Bokeh**: Data visualization and interactive plotting
- **SurrealDB**: Multi-model database concepts
- **FastAPI**: Web API development and frameworks
- **Panel**: Dashboard and application building
- **PyGAD**: Genetic algorithms and optimization
- **Logfire**: Observability and monitoring

#### Quality Filters
- **High Quality** (80%+): Most reliable and comprehensive content
- **Good Quality** (60-79%): Well-documented with good coverage
- **All Content**: Include all quality levels for complete view

#### Relationship Filters
- **Direct Connections**: Only immediate neighbors
- **2-Hop Paths**: Entities connected through one intermediary
- **Cross-Domain**: Focus on relationships between different domains
- **Temporal**: Show relationships that evolved over time

---

## 📊 Understanding the Visualization

### Node Types and Meanings

#### Domain Nodes (Large, Bold Border)
- **Representation**: Major knowledge domains or frameworks
- **Size**: Proportional to number of documentation pages
- **Color**: Unique color per domain (see legend)
- **Information**: Total pages, quality score, processing time

#### Concept Nodes (Medium, Standard Border)
- **Representation**: Specific concepts, features, or topics
- **Size**: Based on importance and connection count
- **Color**: Inherited from parent domain
- **Information**: Related pages, quality metrics, relationships

#### Document Nodes (Small, Subtle)
- **Representation**: Individual documentation pages
- **Size**: Based on content length and quality
- **Color**: Domain-based with transparency
- **Information**: URL, title, content preview, metadata

### Edge Types and Relationships

#### Structural Relationships
- **Contains**: Domain contains concepts or documents
- **References**: Cross-references between topics
- **Depends On**: Dependencies and prerequisites
- **Implements**: Concrete implementations of abstract concepts

#### Semantic Relationships
- **Similar To**: Conceptually related topics
- **Alternative To**: Competing or alternative approaches
- **Extends**: Enhanced or specialized versions
- **Uses**: Practical application or usage patterns

#### Temporal Relationships
- **Evolved From**: Historical development paths
- **Deprecated By**: Replacement or succession
- **Concurrent With**: Developed or documented simultaneously

### Visual Encodings

#### Colors
- **Domain Identity**: Each domain has unique color scheme
- **Quality Indication**: Saturation indicates content quality
- **Selection State**: Highlighted nodes show current selection
- **Filtering State**: Faded nodes indicate filtered out content

#### Sizes
- **Importance**: Larger nodes represent more central concepts
- **Content Volume**: Size correlates with documentation depth
- **Connection Count**: Highly connected nodes appear larger
- **Quality Weight**: High-quality content gets size boost

#### Edge Styles
- **Line Thickness**: Indicates relationship strength
- **Line Style**: Solid (direct), dashed (inferred), dotted (weak)
- **Arrows**: Show directional relationships where applicable
- **Colors**: Inherit from source node or relationship type

---

## 💡 Common Use Cases

### For Researchers and Students

#### Exploring New Technologies
1. **Start with Domain**: Click on framework you're learning
2. **Browse Concepts**: Explore connected concepts and features
3. **Find Learning Path**: Follow prerequisite relationships
4. **Compare Alternatives**: Look for "alternative to" relationships

#### Literature Review and Research
1. **Comprehensive Coverage**: Ensure complete topic coverage
2. **Cross-Domain Analysis**: Find connections between fields
3. **Quality Assessment**: Focus on high-quality content sources
4. **Gap Identification**: Find under-connected or missing areas

### For Developers and Engineers

#### Technology Selection
1. **Feature Comparison**: Compare capabilities across frameworks
2. **Integration Patterns**: Find how technologies work together
3. **Implementation Examples**: Locate specific usage patterns
4. **Best Practices**: Identify well-documented approaches

#### Problem Solving
1. **Concept Lookup**: Quick access to specific technical concepts
2. **Related Solutions**: Find alternative approaches to problems
3. **Dependency Mapping**: Understand technology requirements
4. **Migration Planning**: Identify replacement technologies

### For Data Scientists and Analysts

#### Knowledge Discovery
1. **Pattern Recognition**: Identify clusters of related concepts
2. **Trend Analysis**: Observe evolution of technologies over time
3. **Gap Analysis**: Find under-represented or missing topics
4. **Network Analysis**: Understand information flow patterns

#### Research Planning
1. **Coverage Assessment**: Evaluate knowledge base completeness
2. **Priority Identification**: Focus on central, well-connected topics
3. **Collaboration Opportunities**: Find overlapping research areas
4. **Resource Allocation**: Direct efforts based on quality metrics

---

## 🔧 Advanced Features

### Temporal Analysis

#### Timeline View
1. **Chronological Order**: View knowledge extraction timeline
2. **Evolution Tracking**: See how concepts developed over time
3. **Update Patterns**: Identify frequently updated domains
4. **Historical Context**: Understand development sequences

#### Time-Based Filtering
- **Date Ranges**: Focus on specific time periods
- **Update Frequency**: Show recently updated content
- **Version Tracking**: Compare different versions of documentation
- **Trend Analysis**: Identify emerging or declining topics

### Network Analysis

#### Centrality Metrics
- **Betweenness**: Identify bridge concepts between domains
- **Closeness**: Find concepts central to overall knowledge
- **Degree**: Highlight highly connected entities
- **PageRank**: Discover most important concepts

#### Community Detection
- **Clustering**: Automatic grouping of related concepts
- **Module Identification**: Find coherent knowledge modules
- **Cross-Domain Bridges**: Identify inter-domain connections
- **Isolated Components**: Find disconnected knowledge areas

### Export and Integration

#### Data Export
- **Graph Data**: Export in GraphML, GEXF, or JSON formats
- **Selected Subsets**: Export filtered or selected portions
- **Image Export**: Save visualizations as PNG, SVG, or PDF
- **Metadata**: Include quality scores and temporal information

#### API Integration
```javascript
// Example API usage
const graph = await ptolemies.getSubgraph({
  domains: ['pytorch', 'fastapi'],
  minQuality: 0.7,
  maxDepth: 2
});
```

#### MCP Server Access
```python
# Example MCP client usage
async with mcp_client.session() as session:
    entities = await session.call("ptolemies.search", {
        "query": "neural networks",
        "domain": "pytorch"
    })
```

---

## 🎯 Tips and Best Practices

### Effective Exploration Strategies

#### Start Broad, Then Focus
1. **Overview First**: Begin with full graph view
2. **Domain Selection**: Choose relevant domain for your needs
3. **Concept Drilling**: Click through to specific concepts
4. **Detail Exploration**: Use side panel for in-depth information

#### Use Multiple Filters
1. **Combine Filters**: Use domain + quality + relationship filters
2. **Iterative Refinement**: Gradually narrow your search
3. **Save Configurations**: Bookmark useful filter combinations
4. **Compare Views**: Switch between filtered and unfiltered views

### Performance Optimization

#### Large Graph Navigation
1. **Use Filters**: Reduce visual complexity with domain filters
2. **Focus Views**: Use neighborhood views for local exploration
3. **Quality Thresholds**: Filter low-quality content for clarity
4. **Progressive Loading**: Let graph load fully before interaction

#### Search Efficiency
1. **Specific Terms**: Use precise keywords for better results
2. **Domain Context**: Include domain names in searches
3. **Incremental Search**: Build queries gradually
4. **Save Searches**: Bookmark frequently used search terms

### Data Interpretation

#### Understanding Quality Scores
- **90%+**: Exceptional quality, comprehensive documentation
- **80-89%**: Very good quality, reliable information
- **70-79%**: Good quality, useful for most purposes
- **60-69%**: Acceptable quality, may have gaps
- **Below 60%**: Use with caution, may be incomplete

#### Relationship Interpretation
- **Thick Lines**: Strong, well-documented relationships
- **Thin Lines**: Weak or inferred connections
- **Multiple Paths**: Alternative ways to connect concepts
- **Isolated Nodes**: Potentially incomplete or specialized topics

---

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### Performance Problems
**Issue**: Slow rendering or interaction  
**Solutions**:
- Use domain filters to reduce graph size
- Increase browser memory allocation
- Close other browser tabs
- Try a different browser

**Issue**: Graph layout appears jumbled  
**Solutions**:
- Reset to default layout
- Try different layout algorithms
- Adjust zoom level
- Clear browser cache

#### Search and Navigation
**Issue**: Search returns no results  
**Solutions**:
- Check spelling and try synonyms
- Reduce search term specificity
- Clear existing filters
- Try wildcard searches

**Issue**: Cannot find specific entity  
**Solutions**:
- Use broader search terms
- Check all domain filters are enabled
- Try alternative terminology
- Browse through related concepts

#### Display and Interface
**Issue**: Text is too small or large  
**Solutions**:
- Adjust browser zoom level
- Use graph zoom controls
- Check display scaling settings
- Try different screen resolution

**Issue**: Side panel not showing details  
**Solutions**:
- Ensure JavaScript is enabled
- Click directly on nodes, not empty space
- Refresh page if issue persists
- Check browser console for errors

### Browser Compatibility

#### Recommended Browsers
- **Chrome**: Full feature support, best performance
- **Firefox**: Full feature support, good performance
- **Safari**: Good support, some advanced features limited
- **Edge**: Good support, comparable to Chrome

#### Known Limitations
- **Internet Explorer**: Not supported
- **Mobile Browsers**: Limited interaction on small screens
- **Older Browsers**: Some advanced features may not work
- **Ad Blockers**: May interfere with data loading

---

## 📚 Additional Resources

### Learning Resources

#### Video Tutorials
- Getting Started with Ptolemies Knowledge Graph (10 min)
- Advanced Search and Filtering Techniques (15 min)
- Understanding Graph Visualization Patterns (12 min)
- Using the MCP API for Custom Applications (20 min)

#### Documentation
- **Technical API Reference**: Detailed API documentation
- **Developer Guide**: Custom integration instructions
- **Data Model Documentation**: Understanding the knowledge schema
- **Performance Tuning Guide**: Optimization recommendations

### Community and Support

#### Help and Support
- **User Forum**: Community Q&A and discussions
- **Issue Tracker**: Report bugs and request features
- **Documentation Wiki**: Community-maintained guides
- **Email Support**: Direct assistance for complex issues

#### Contributing
- **Content Suggestions**: Recommend new domains or sources
- **Quality Feedback**: Report accuracy issues or improvements
- **Feature Requests**: Suggest new visualization features
- **Beta Testing**: Early access to new features

### Related Tools

#### Complementary Systems
- **Neo4j Browser**: Advanced graph database queries
- **Gephi**: Offline graph analysis and visualization
- **Cytoscape**: Biological network analysis tools
- **NetworkX**: Python library for graph analysis

#### Integration Possibilities
- **Jupyter Notebooks**: Embed graphs in analysis workflows
- **Dashboard Platforms**: Include as component in larger systems
- **Documentation Sites**: Embed as interactive knowledge maps
- **Learning Management**: Integrate with educational platforms

---

## 📊 Appendices

### Appendix A: Domain Coverage Details

| Domain | Pages | Quality | Key Topics |
|--------|-------|---------|------------|
| **PyTorch** | 180 | 87.3% | Neural Networks, Tensors, CUDA, Autograd |
| **Bokeh** | 200 | 78.9% | Interactive Plots, Widgets, Server Apps |
| **SurrealDB** | 200 | 77.9% | Multi-model DB, SurrealQL, Real-time |
| **FastAPI** | 33 | 74.1% | REST API, Async, Type Hints, OpenAPI |
| **Panel** | 37 | 84.1% | Dashboards, Jupyter, Reactive Programming |
| **PyGAD** | 30 | 37.2% | Genetic Algorithms, Evolution Strategy |
| **Logfire** | 97 | 71.2% | Observability, Tracing, Monitoring |

### Appendix B: Quality Score Methodology

#### Quality Assessment Factors
- **Content Completeness**: Comprehensive coverage of topics
- **Technical Accuracy**: Correctness of information
- **Documentation Quality**: Clear explanations and examples
- **Update Frequency**: Recent and maintained content
- **Cross-References**: Well-linked to related concepts

#### Score Calculation
```
Quality Score = (
  Completeness * 0.3 +
  Accuracy * 0.3 +
  Clarity * 0.2 +
  Recency * 0.1 +
  Connectivity * 0.1
) * 100%
```

### Appendix C: Keyboard Shortcuts

| Action | Shortcut | Description |
|--------|----------|-------------|
| **Search** | Ctrl+F | Focus search box |
| **Fit to Screen** | F | Fit entire graph |
| **Select All** | Ctrl+A | Select all visible elements |
| **Copy Selection** | Ctrl+C | Copy selected elements |
| **Reset View** | R | Reset to default layout |
| **Toggle Sidebar** | S | Show/hide detail panel |
| **Next Result** | Tab | Navigate search results |
| **Previous Result** | Shift+Tab | Navigate backward |

### Appendix D: API Quick Reference

#### Search Endpoints
```javascript
GET /api/search?q={query}&domain={domain}
GET /api/entities/{id}
GET /api/relationships/{source}/{target}
```

#### Graph Endpoints
```javascript
GET /api/graph/subgraph?domains={list}
GET /api/graph/neighbors/{id}?depth={n}
GET /api/graph/path/{source}/{target}
```

#### Export Endpoints
```javascript
GET /api/export/graphml?filter={params}
GET /api/export/json?selection={ids}
```

---

**Document Version**: 1.0  
**Last Updated**: December 6, 2025  
**Next Review**: March 2026  

For questions, feedback, or support, please contact the Ptolemies development team or visit our documentation portal.