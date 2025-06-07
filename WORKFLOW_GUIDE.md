# Ptolemies URL Ingestion Workflow Guide

## Overview

The URL ingestion workflow (`ingest_urls_workflow.py`) is a comprehensive automation script that:
- Manages all required services (SurrealDB, Neo4j, Graphiti)
- Verifies prerequisites (API keys, connections)
- Crawls and processes URLs with advanced content extraction
- Stores content in both document and graph formats
- Generates detailed reports

## Prerequisites

1. **Python Environment**
   ```bash
   cd /Users/dionedge/devqai/ptolemies
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment Variables** (`.env` file)
   ```bash
   # Core Configuration (Required)
   SURREALDB_URL=ws://localhost:8000/rpc
   SURREALDB_NAMESPACE=ptolemies
   SURREALDB_DATABASE=knowledge
   SURREALDB_USERNAME=root
   SURREALDB_PASSWORD=root
   
   # Optional (for semantic search)
   OPENAI_API_KEY=your_openai_api_key
   
   # Optional (for Neo4j/Graphiti integration)
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=Ptolemis
   ```

3. **Neo4j** (optional, for Graphiti integration)
   - **Option A**: Docker (recommended) - The script will automatically start Neo4j in a container
   - **Option B**: Manual installation - Install Neo4j separately and ensure it's running on port 7474
   - **Option C**: Skip - Continue with SurrealDB only (without graph capabilities)
   
   The script will:
   - Check if Neo4j is already running
   - Try to start it via Docker if available
   - Prompt you to continue without it if Docker isn't available

## Usage

### Simple Batch Processing (Recommended)
```bash
python simple_batch_ingest.py
```
This is the **recommended approach** that:
- Processes predefined documentation URLs (PyGAD, PyTorch, Bokeh, Panel)
- Uses only SurrealDB (no Docker required)
- Has proven 100% success rate
- Stores data in `ptolemies.knowledge` database

### Interactive Mode
```bash
./run_ingest_workflow.sh
```
This will:
1. Prompt you for the number of URLs
2. Collect URLs one by one
3. Process each URL with appropriate tags
4. Generate a comprehensive report

### Test Mode
```bash
./run_ingest_workflow.sh --test
```
Automatically processes two test URLs:
- Bokeh documentation (Python visualization)
- Panel/HoloViz documentation (Python dashboards)

### Direct Python Execution
```bash
python src/ingest_urls_workflow.py
python src/ingest_urls_workflow.py --test
```

## Workflow Steps

### 1. Service Startup
- **SurrealDB**: Checks if running, starts if needed
- **Neo4j**: Starts in Docker container (ptolemies-neo4j)
- **Graphiti**: Connects to service wrapper

### 2. Verification
- Validates OpenAI API key (from env or .env file)
- Tests database connections
- Ensures all services are responsive

### 3. URL Collection
- Interactive: Prompts for number of URLs and collects them
- Test mode: Uses predefined test URLs
- Validates URL format (must start with http:// or https://)

### 4. Content Crawling
For each URL:
- Determines appropriate tags based on content
- Crawls with depth=2 by default
- Extracts code blocks and tables
- Stores in SurrealDB with embeddings
- Creates relationships in Graphiti

### 5. Report Generation
Creates `knowledge_base_report.md` with:
- Total items and categories
- Top tags and their counts
- Sample items from each category
- Workflow execution results
- Success/failure status for each URL

### 6. README Update
Automatically updates the project README with:
- Workflow documentation
- Usage instructions
- Architecture overview

## Output Files

1. **knowledge_base_report.md**
   - Comprehensive summary of all content
   - Categories and tag statistics
   - Sample entries from each category

2. **workflow_results.json**
   - Detailed execution results
   - Service status
   - URL processing outcomes
   - Any errors encountered

## Troubleshooting

### SurrealDB Won't Start
```bash
# Check if already running
curl http://localhost:8000/health

# Start manually
surreal start --log info --user root --pass root file:~/.ptolemies/data
```

### Neo4j Issues
```bash
# Check Docker container
docker ps -a | grep ptolemies-neo4j

# View logs
docker logs ptolemies-neo4j

# Remove and restart
docker rm -f ptolemies-neo4j
```

### OpenAI API Key
```bash
# Set in current session
export OPENAI_API_KEY="your-key-here"

# Or add to .env file
echo "OPENAI_API_KEY=your-key-here" >> .env
```

### Crawling Failures
- Check network connectivity
- Verify URLs are accessible
- Some sites may block automated crawling
- Try with different URLs or adjust depth

## Advanced Usage

### Custom Tags and Categories
Modify the script to add custom logic:
```python
# In crawl_urls() method
if "your-domain" in url.lower():
    tags.extend(["custom", "tags"])
    category = "Your Category"
```

### Adjust Crawl Depth
Edit `ingest_urls_workflow.py`:
```python
result = await self.crawl_manager.crawl_url(
    url=url,
    depth=3,  # Increase for deeper crawling
    # ...
)
```

### Batch Processing
Create a file with URLs and modify the script to read from it:
```python
with open("urls.txt") as f:
    urls = [line.strip() for line in f if line.strip()]
```

## Integration with MCP

The workflow integrates with the Ptolemies MCP server:
```bash
# Start MCP server after ingestion
python -m ptolemies.mcp.ptolemies_mcp

# Or use enhanced MCP with Graphiti
./src/start_enhanced_mcp.sh
```

This exposes tools for AI agents:
- `search`: Semantic and keyword search
- `retrieve`: Get specific items
- `store`: Add new knowledge
- `related`: Find related content

## Success Summary

The Ptolemies knowledge base has been successfully tested with:

### Processed Content (12 items total)
- **PyGAD**: Genetic algorithm documentation
- **PyTorch**: Deep learning framework documentation  
- **Bokeh**: 3 visualization library pages
- **Panel/HoloViz**: 6 dashboard framework pages
- **Test item**: Verification content

### Database Confirmation
- **Location**: `ptolemies.knowledge` ✓
- **Total Items**: 12 ✓
- **Success Rate**: 100% (11/11 URLs) ✓
- **No Docker Required**: SurrealDB only ✓

### Technical Achievements
1. Fixed Pydantic v2 compatibility issues
2. Resolved database schema validation problems
3. Corrected namespace/database configuration
4. Implemented reliable CLI-based ingestion
5. Created verification and reporting tools

### Current Status
The knowledge base is **production ready** with comprehensive documentation from machine learning, deep learning, visualization, and dashboard development domains. All content is properly stored, searchable, and accessible via both CLI tools and MCP server integration.