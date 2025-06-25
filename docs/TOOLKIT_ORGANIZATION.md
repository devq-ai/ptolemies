# Ptolemies Knowledge Base Toolkit Organization
=============================================

## 📁 Directory Structure

This repository has been organized into specialized directories containing the tools and resources for the comprehensive knowledge base system.

---

## 🔧 **crawling_tools/**
**Advanced web crawling and data collection tools**

### Primary Crawlers:
- **`enhanced_production_crawler.py`** - Main production crawler with depth=4, pages=750 capability
- **`targeted_gap_filler.py`** - Specialized crawler for minimal-coverage sources  
- **`final_gap_filler.py`** - Quick gap-filling for specific sources

### Usage:
```bash
# Run comprehensive crawling of all 17 framework sources
python3 crawling_tools/enhanced_production_crawler.py

# Target specific sources that need more coverage
python3 crawling_tools/targeted_gap_filler.py

# Quick fix for remaining gaps
python3 crawling_tools/final_gap_filler.py
```

---

## 🎨 **graph_visualization/**
**Neo4j knowledge graph building and visualization tools**

### Core Files:
- **`neo4j_graph_builder.py`** - Comprehensive graph relationship builder
- **`neo4j_graph_visualization_guide.md`** - Complete visualization guide
- **`neo4j_visualization_queries.cypher`** - Ready-to-use graph queries

### Features:
- Framework dependency mapping
- Class inheritance trees
- Method call chains
- Type relationships
- Usage patterns

### Usage:
```bash
# Build comprehensive knowledge graph
python3 graph_visualization/neo4j_graph_builder.py

# Then open Neo4j Browser at http://localhost:7474
# Use queries from neo4j_visualization_queries.cypher
```

---

## 🤖 **ai_detection/**
**AI hallucination detection and code validation tools**

### Detection System:
- **`ai_hallucination_detector.py`** - Main orchestrator for hallucination detection
- **`ai_script_analyzer.py`** - AST-based Python script analysis
- **`knowledge_graph_validator.py`** - Neo4j knowledge graph validation
- **`hallucination_reporter.py`** - Report generation and analysis

### Capabilities:
- Validates code against Neo4j knowledge base
- Detects non-existent classes, methods, functions
- Generates detailed JSON and Markdown reports
- Provides confidence scores for code elements

### Usage:
```bash
# Analyze a single script for hallucinations
python3 ai_detection/ai_hallucination_detector.py script.py

# Batch analyze multiple scripts
python3 ai_detection/ai_hallucination_detector.py --batch /path/to/scripts/
```

---

## 📊 **monitoring/**
**Crawling progress and system status monitoring tools**

### Monitoring Tools:
- **`monitor_crawl_completion.py`** - Comprehensive crawling progress monitor
- **`check_completion_status.py`** - Quick status checker
- **`completion_monitor.sh`** - Background monitoring script

### Features:
- Real-time chunk count tracking
- Source coverage monitoring
- Completion assessment
- Progress notifications

### Usage:
```bash
# Quick status check
python3 monitoring/check_completion_status.py

# Continuous monitoring
python3 monitoring/monitor_crawl_completion.py

# Background monitoring
nohup ./monitoring/completion_monitor.sh > monitor.log 2>&1 &
```

---

## 📊 **Current System Status**

### **Knowledge Base Statistics:**
- **Total Chunks**: 2,296 across all frameworks
- **Sources Covered**: 17/17 frameworks
- **Neo4j Nodes**: 143 (frameworks, classes, methods, functions)
- **Neo4j Relationships**: 149 (inheritance, dependencies, calls)

### **Framework Coverage:**
```
FastAPI:     450 chunks  ✅ Excellent
Pydantic AI: 329 chunks  ✅ Excellent  
Claude Code: 543 chunks  ✅ Excellent
Logfire:     149 chunks  ✅ Good
NextJS:      73 chunks   ✅ Good
Crawl4AI:    57 chunks   ✅ Adequate
Panel:       57 chunks   ✅ Adequate
circom:      24 chunks   ✅ Adequate
FastMCP:     17 chunks   ✅ Adequate
SurrealDB:   7 chunks    ⚠️  Minimal
AnimeJS:     7 chunks    ⚠️  Minimal
Wildwood:    6 chunks    ⚠️  Minimal
```

---

## 🚀 **Quick Start Guide**

### 1. **Set up Environment**
```bash
# Ensure databases are running
# SurrealDB: ws://localhost:8000/rpc
# Neo4j: bolt://localhost:7687

# Verify environment variables
export OPENAI_API_KEY="your-key"
export LOGFIRE_TOKEN="your-token"
```

### 2. **Build Knowledge Graph**
```bash
python3 graph_visualization/neo4j_graph_builder.py
```

### 3. **Explore Visualizations**
- Open Neo4j Browser: http://localhost:7474
- Login: `neo4j` / `ptolemies`
- Use queries from `graph_visualization/neo4j_visualization_queries.cypher`

### 4. **Detect AI Hallucinations**
```bash
python3 ai_detection/ai_hallucination_detector.py your_script.py
```

### 5. **Monitor System Status**
```bash
python3 monitoring/check_completion_status.py
```

---

## 📋 **Integration Points**

### **SurrealDB Integration**
- Stores 2,296 document chunks with embeddings
- Namespace: `ptolemies`
- Database: `knowledge`
- Full RAG system ready

### **Neo4j Integration**  
- 143 nodes representing code elements
- 149 relationships showing connections
- Complete framework ecosystem graph
- Inheritance trees and method call chains

### **OpenAI Integration**
- Embeddings: `text-embedding-3-small`
- Vector search capabilities
- AI hallucination detection

### **Logfire Integration**
- Complete observability for all operations
- Performance metrics and error tracking
- Span-based monitoring

---

## 🎯 **Use Cases**

### **For Developers:**
- **Framework Selection**: Compare frameworks using the knowledge graph
- **Code Validation**: Detect hallucinations in AI-generated code
- **API Discovery**: Find classes, methods, and usage patterns
- **Integration Planning**: Understand framework dependencies

### **For AI Systems:**
- **Hallucination Detection**: Validate generated code against real documentation
- **Context Enhancement**: Use RAG system for accurate code generation
- **Knowledge Verification**: Cross-reference claims against documentation
- **Learning Assistance**: Discover framework relationships and patterns

### **For Research:**
- **Framework Analysis**: Study ecosystem relationships and patterns
- **Documentation Quality**: Assess coverage and completeness
- **Trend Analysis**: Track framework evolution and adoption
- **Comparative Studies**: Analyze similarities and differences

---

## 📚 **Additional Resources**

### **Documentation Files in Root:**
- `README.md` - Main project documentation
- `CLAUDE.md` - Claude Code configuration
- `CONFIG.md` - System configuration guide
- Various status and completion reports

### **Generated Reports:**
- `crawl_monitor.log` - Crawling progress logs
- `hallucination_reports/` - AI detection results
- `metrics/` - System performance metrics
- `backups/` - Database backups

### **Example Scripts:**
- `test_*.py` files - Testing and validation scripts
- `query_examples_and_results.py` - Example queries
- `practical_usage_guide.py` - Usage demonstrations

---

## ⚡ **Performance Notes**

- **Crawling**: Enhanced crawler can process 750 pages at depth 4 per source
- **Graph Queries**: Neo4j optimized with indexes and constraints
- **Vector Search**: OpenAI embeddings provide semantic search capabilities
- **Monitoring**: Real-time progress tracking with 2-minute intervals

---

This organized toolkit provides everything needed to build, maintain, and utilize the comprehensive framework knowledge base for AI hallucination detection and code validation. 🎉