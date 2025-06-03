# Crawl4AI Integration with Ptolemies Knowledge Base

This document outlines the integration between the Crawl4AI MCP server and the Ptolemies Knowledge Base, enabling automated content ingestion from web sources.

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation](#implementation)
4. [Usage](#usage)
5. [Configuration](#configuration)

## Overview

The Crawl4AI integration allows the Ptolemies Knowledge Base to automatically discover, crawl, and ingest content from the web. This integration leverages the Crawl4AI MCP server's capabilities for intelligent web crawling with AI-powered content extraction and analysis.

Key features of this integration include:
- Intelligent web crawling with configurable depth and scope
- Content extraction with structure preservation
- Automatic categorization and tagging of content
- Metadata extraction for knowledge enrichment
- Scheduled crawling for content freshness

## Architecture

```
┌────────────────────────┐     ┌─────────────────────┐     ┌───────────────────┐
│                        │     │                     │     │                   │
│   Ptolemies            │     │                     │     │                   │
│   Knowledge Base       │◀───▶│   MCP Gateway       │◀───▶│   Crawl4AI MCP    │
│                        │     │                     │     │   Server          │
└────────────┬───────────┘     └─────────────────────┘     └─────────┬─────────┘
             │                                                       │
             │                                                       │
             ▼                                                       ▼
┌────────────────────────┐                                 ┌─────────────────────┐
│                        │                                 │                     │
│   SurrealDB            │                                 │    Web Sources      │
│   (Knowledge Storage)  │                                 │    (Content)        │
│                        │                                 │                     │
└────────────────────────┘                                 └─────────────────────┘
```

## Implementation

The integration is implemented as follows:

1. **Crawl Manager Service**:
   - Orchestrates crawling operations
   - Manages crawl schedules and triggers
   - Tracks crawl history and status

2. **Content Processor**:
   - Extracts structured content from crawled pages
   - Preserves document structure and formatting
   - Handles different content types (articles, docs, code)

3. **Knowledge Transformer**:
   - Converts extracted content to knowledge items
   - Generates metadata and relationships
   - Applies content categorization rules

4. **MCP Adapter**:
   - Interfaces with the Crawl4AI MCP server
   - Translates between Ptolemies and MCP formats
   - Handles authentication and rate limiting

## Usage

### Crawling a Single URL

```python
from ptolemies.integrations.crawl4ai import CrawlManager

# Initialize the crawl manager
crawl_manager = CrawlManager()

# Crawl a single URL
result = await crawl_manager.crawl_url(
    url="https://example.com/documentation",
    depth=2,
    extract_code=True,
    extract_tables=True,
    categorize=True
)

# Process and store the results
knowledge_items = await crawl_manager.process_results(result)
```

### Scheduling Regular Crawls

```python
from ptolemies.integrations.crawl4ai import CrawlScheduler

# Initialize the scheduler
scheduler = CrawlScheduler()

# Add a scheduled crawl
scheduler.add_scheduled_crawl(
    name="Documentation Crawler",
    urls=["https://example.com/docs", "https://example.com/api"],
    schedule="0 0 * * *",  # Daily at midnight
    depth=3,
    extract_code=True,
    tags=["documentation", "api"],
    category="Technical Documentation"
)

# Start the scheduler
scheduler.start()
```

### Using the CLI

```bash
# Crawl a URL and add to knowledge base
python -m ptolemies.cli crawl-url https://example.com/article --depth 2 --tags news,tech

# Set up a scheduled crawl
python -m ptolemies.cli add-crawl-schedule "News Crawler" https://example.com/news --schedule "0 */6 * * *"

# List active crawl schedules
python -m ptolemies.cli list-crawl-schedules
```

## Configuration

### Crawl4AI MCP Configuration

Configure the connection to the Crawl4AI MCP server in your `.env` file:

```
# Crawl4AI MCP Configuration
MCP_CRAWL4AI_ENDPOINT=http://localhost:8080/tools/crawl4ai-mcp/invoke
MCP_CRAWL4AI_API_KEY=your_api_key_here
```

### Crawler Settings

Configure the crawler behavior:

```
# Crawler Configuration
CRAWLER_MAX_DEPTH=3
CRAWLER_MAX_PAGES=100
CRAWLER_DELAY_MS=1000
CRAWLER_RESPECT_ROBOTS_TXT=true
CRAWLER_USER_AGENT=Ptolemies Knowledge Crawler/1.0
```

### Content Processing Settings

Configure how content is processed and stored:

```
# Content Processing
CONTENT_EXTRACT_CODE=true
CONTENT_EXTRACT_TABLES=true
CONTENT_PRESERVE_IMAGES=true
CONTENT_MIN_TEXT_LENGTH=100
CONTENT_MAX_TEXT_LENGTH=50000
CONTENT_CATEGORIZATION_ENABLED=true
```