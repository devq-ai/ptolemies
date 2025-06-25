# Ptolemies Knowledge Base - Quick Start Guide
==============================================

## 🚀 **Get Started in 5 Minutes**

This guide gets you up and running with the comprehensive framework knowledge base for AI hallucination detection and code validation.

---

## ✅ **Prerequisites Check**

### **Required Services:**
```bash
# Check SurrealDB (should return status)
curl -s http://localhost:8000/status

# Check Neo4j (should connect without error)  
cypher-shell -a bolt://localhost:7687 -u neo4j -p ptolemies "RETURN 1;"

# Check Python environment
python3 --version  # Should be 3.12+
```

### **Environment Variables:**
```bash
export OPENAI_API_KEY="your-openai-api-key"
export LOGFIRE_TOKEN="your-logfire-token"  # Optional but recommended
```

---

## 🎯 **Current System Status**

Your knowledge base is **READY TO USE** with:
- ✅ **2,296 total chunks** across 17 frameworks
- ✅ **Complete SurrealDB RAG system** 
- ✅ **Comprehensive Neo4j knowledge graph**
- ✅ **AI hallucination detection tools**

---

## 🔥 **Quick Actions**

### **1. Check System Status (30 seconds)**
```bash
python3 monitoring/check_completion_status.py
```

### **2. Explore Knowledge Graph (2 minutes)**
```bash
# Build/verify the graph relationships
python3 graph_visualization/neo4j_graph_builder.py

# Open Neo4j Browser
open http://localhost:7474
# Login: neo4j / ptolemies
```

### **3. Detect AI Hallucinations (1 minute)**
```bash
# Test with a sample script
echo 'import fastapi; app = fastapi.FakeClass()' > test_script.py
python3 ai_detection/ai_hallucination_detector.py test_script.py

# Check the generated report
ls hallucination_reports/
```

### **4. Query the Knowledge Base (30 seconds)**
```bash
# Quick data check  
python3 simple_data_check.py

# Run example queries
python3 query_examples_and_results.py
```

---

## 📊 **Essential Visualizations**

### **Framework Overview in Neo4j:**
```cypher
MATCH (f:Framework)
OPTIONAL MATCH (f)-[:HAS_CLASS]->(c:Class)
OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
RETURN f, c, m
LIMIT 25;
```

### **Framework Integration Map:**
```cypher
MATCH (f1:Framework)-[r]->(f2:Framework)
RETURN f1, r, f2;
```

### **Class Inheritance Trees:**
```cypher
MATCH (c1:Class)-[r:INHERITS_FROM]->(c2:Class)
RETURN c1, r, c2;
```

---

## 🔧 **Common Tasks**

### **Add More Documentation for Minimal Sources:**
```bash
# Target sources with <10 chunks
python3 crawling_tools/targeted_gap_filler.py
```

### **Monitor Crawling Progress:**
```bash
# Real-time monitoring
python3 monitoring/monitor_crawl_completion.py
```

### **Validate AI-Generated Code:**
```bash
# Analyze any Python script
python3 ai_detection/ai_hallucination_detector.py your_script.py

# Batch analyze multiple files
python3 ai_detection/ai_hallucination_detector.py --batch /path/to/scripts/
```

### **Search the Knowledge Base:**
```bash
# Search for specific terms in SurrealDB
python3 -c "
import subprocess
result = subprocess.run([
    'surreal', 'sql', '--conn', 'ws://localhost:8000/rpc',
    '--user', 'root', '--pass', 'root', '--ns', 'ptolemies', '--db', 'knowledge'
], input='SELECT * FROM document_chunks WHERE content CONTAINS \"FastAPI\" LIMIT 5;', 
text=True, capture_output=True)
print(result.stdout)
"
```

---

## 🎨 **Visualization Workflows**

### **Workflow 1: Framework Analysis**
1. Open Neo4j Browser: http://localhost:7474
2. Run framework overview query
3. Explore specific framework ecosystems
4. Analyze integration patterns

### **Workflow 2: Code Validation**
1. Create or identify suspicious AI-generated code
2. Run hallucination detector
3. Review JSON/Markdown reports
4. Cross-reference with knowledge graph

### **Workflow 3: Documentation Research**
1. Search SurrealDB for specific topics
2. Examine chunk sources and content
3. Trace relationships in Neo4j
4. Discover usage patterns

---

## 📁 **File Organization**

```
ptolemies/
├── crawling_tools/          # Web crawling and data collection
├── graph_visualization/     # Neo4j graph building and queries  
├── ai_detection/           # Hallucination detection system
├── monitoring/             # Progress and status monitoring
├── src/                    # Core application code
├── tests/                  # Test suites
├── reports/                # Generated reports and metrics
└── TOOLKIT_ORGANIZATION.md # Detailed file descriptions
```

---

## 🔍 **Debugging & Troubleshooting**

### **Common Issues:**

#### **SurrealDB Connection Failed:**
```bash
# Start SurrealDB
surreal start --bind 0.0.0.0:8000 --user root --pass root memory

# Verify connection
curl -s http://localhost:8000/status
```

#### **Neo4j Connection Failed:**
```bash
# Check Neo4j status
neo4j status

# Start if needed
neo4j start

# Reset password if needed
neo4j-admin set-initial-password ptolemies
```

#### **Missing Dependencies:**
```bash
# Install requirements
pip install -r requirements.txt

# Or install individually
pip install openai httpx beautifulsoup4 logfire python-dotenv
```

#### **Empty Query Results:**
```bash
# Verify data exists
python3 monitoring/check_completion_status.py

# Re-run crawling if needed
python3 crawling_tools/enhanced_production_crawler.py
```

---

## 🎯 **Next Steps**

### **For Developers:**
1. Integrate hallucination detection into your AI pipelines
2. Use the knowledge graph for framework selection
3. Query the RAG system for accurate documentation
4. Build upon the existing crawling tools

### **For Researchers:**
1. Analyze framework relationships and patterns
2. Study documentation quality and coverage
3. Explore ecosystem evolution trends
4. Compare framework architectures

### **For AI Systems:**
1. Use as ground truth for code validation
2. Enhance RAG-based code generation
3. Implement real-time hallucination detection
4. Build framework-aware AI assistants

---

## 📚 **Learn More**

- **Complete Documentation**: `TOOLKIT_ORGANIZATION.md`
- **Visualization Guide**: `graph_visualization/neo4j_graph_visualization_guide.md`
- **Query Examples**: `neo4j_visualization_queries.cypher`
- **System Configuration**: `CLAUDE.md`, `CONFIG.md`

---

## 🎉 **You're Ready!**

Your comprehensive framework knowledge base is fully operational. Start exploring, validating, and building with confidence! 

**Pro Tip**: Begin with the Neo4j visualizations to get oriented with the ecosystem, then try detecting hallucinations in some AI-generated code samples.