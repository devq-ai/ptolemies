# Crawl4AI Knowledge Ingestion Targets

This document defines target URLs for the Ptolemies knowledge base to ingest using the Crawl4AI integration. Each target includes configuration for crawl depth, content extraction settings, and knowledge categorization.

## Table of Contents
1. [Core Framework Documentation](#core-framework-documentation)
2. [Statistical & ML Libraries](#statistical--ml-libraries)
3. [Observability & Logging](#observability--logging)
4. [Database & Storage](#database--storage)
5. [Crawling Configuration](#crawling-configuration)
6. [Scheduled Crawls](#scheduled-crawls)

## Core Framework Documentation

### Pydantic AI

```yaml
url: https://ai.pydantic.dev/
depth: 3
extract_code: true
extract_tables: true
priority: high
tags: 
  - pydantic
  - llm
  - tools
  - agent
  - framework
category: Core Frameworks
crawl_frequency: weekly
excluded_paths:
  - /blog/
  - /changelog/
included_paths:
  - /latest/
  - /tools/
```

Key documentation sections to prioritize:
- https://ai.pydantic.dev/latest/getting-started/
- https://ai.pydantic.dev/latest/tools/
- https://ai.pydantic.dev/latest/mcp/

### PyMC

```yaml
url: https://www.pymc.io/
depth: 3
extract_code: true
extract_tables: true
priority: high
tags:
  - bayesian
  - statistics
  - mcmc
  - probabilistic-programming
category: Statistical Libraries
crawl_frequency: monthly
excluded_paths:
  - /project/
  - /about/
  - /community/
included_paths:
  - /projects/docs/
  - /examples/
```

Key documentation sections to prioritize:
- https://www.pymc.io/projects/docs/en/stable/api.html
- https://www.pymc.io/projects/docs/en/stable/api/distributions.html
- https://www.pymc.io/projects/docs/en/stable/learn.html

## Statistical & ML Libraries

### Wildwood

```yaml
url: https://wildwood.readthedocs.io/en/latest/
depth: 2
extract_code: true
extract_tables: true
priority: medium
tags:
  - machine-learning
  - random-forest
  - decision-trees
  - ensemble-methods
category: ML Libraries
crawl_frequency: monthly
excluded_paths: []
included_paths:
  - /api/
  - /examples/
```

Key documentation sections to prioritize:
- https://wildwood.readthedocs.io/en/latest/wildwood.html
- https://wildwood.readthedocs.io/en/latest/examples.html
- https://wildwood.readthedocs.io/en/latest/api.html

## Observability & Logging

### Logfire

```yaml
url: https://logfire.pydantic.dev/docs/
depth: 2
extract_code: true
extract_tables: true
priority: high
tags:
  - logging
  - observability
  - monitoring
  - structured-logging
category: Observability
crawl_frequency: monthly
excluded_paths:
  - /blog/
included_paths:
  - /docs/api-reference/
  - /docs/how-to/
```

Key documentation sections to prioritize:
- https://logfire.pydantic.dev/docs/
- https://logfire.pydantic.dev/docs/api-reference/
- https://logfire.pydantic.dev/docs/how-to/

## Data Ingestion

### Crawl4AI

```yaml
url: https://docs.crawl4ai.com/
depth: 2
extract_code: true
extract_tables: true
priority: high
tags:
  - web-crawling
  - data-extraction
  - content-analysis
  - mcp
category: Data Ingestion
crawl_frequency: monthly
excluded_paths: []
included_paths:
  - /api/
  - /examples/
  - /integration/
```

Key documentation sections to prioritize:
- https://docs.crawl4ai.com/api/
- https://docs.crawl4ai.com/examples/
- https://docs.crawl4ai.com/integration/

## Database & Storage

### SurrealDB

```yaml
url: https://surrealdb.com/docs/surrealdb
depth: 3
extract_code: true
extract_tables: true
priority: critical
tags:
  - database
  - graph-database
  - multi-model
  - query-language
  - surql
category: Database
crawl_frequency: weekly
excluded_paths:
  - /install/
  - /releases/
included_paths:
  - /docs/surrealdb/surrealql
  - /docs/surrealdb/integration
```

Key documentation sections to prioritize:
- https://surrealdb.com/docs/surrealdb/surrealql/statements
- https://surrealdb.com/docs/surrealdb/surrealql/functions
- https://surrealdb.com/docs/surrealdb/integration/sdks
- https://surrealdb.com/docs/surrealdb/surrealql/datamodel

### Graphiti (Zep K-RAG)

```yaml
url: https://help.getzep.com/concepts
depth: 2
extract_code: true
extract_tables: true
priority: high
tags:
  - knowledge-graph
  - rag
  - visualization
  - graph-relationships
category: Knowledge Graphs
crawl_frequency: monthly
excluded_paths: []
included_paths:
  - /api/
  - /sdk/
```

Key documentation sections to prioritize:
- https://help.getzep.com/concepts/search
- https://help.getzep.com/concepts/collections
- https://help.getzep.com/concepts/embeddings

## Crawling Configuration

For optimal knowledge ingestion, the following configuration should be applied to all crawls:

```yaml
default_config:
  extract_code: true
  extract_tables: true
  respect_robots_txt: true
  user_agent: "Ptolemies Knowledge Crawler/1.0 (https://github.com/devq-ai/ptolemies)"
  delay_ms: 1000
  max_pages_per_domain: 1000
  content_types:
    - text/html
    - text/markdown
    - application/pdf
  extract_metadata:
    - title
    - description
    - keywords
    - author
    - published_date
  preserve_structure: true
  follow_redirects: true
  handle_javascript: true
  proxy_rotation: false
```

## Scheduled Crawls

The following scheduled crawls should be configured for regular knowledge updates:

### Core Frameworks Weekly Update

```yaml
name: "Core Frameworks Update"
schedule: "0 0 * * 1"  # Every Monday at midnight
urls:
  - https://ai.pydantic.dev/
  - https://surrealdb.com/docs/surrealdb
depth: 2
tags:
  - weekly-update
  - core-frameworks
category: "Regular Updates"
```

### Monthly Library Update

```yaml
name: "Monthly Library Update"
schedule: "0 0 1 * *"  # 1st of each month at midnight
urls:
  - https://www.pymc.io/
  - https://wildwood.readthedocs.io/en/latest/
  - https://logfire.pydantic.dev/docs/
  - https://docs.crawl4ai.com/
  - https://help.getzep.com/concepts
depth: 2
tags:
  - monthly-update
  - libraries
category: "Regular Updates"
```

### Example CLI Commands

To start these crawls manually:

```bash
# Run the Core Frameworks crawl
python -m ptolemies.cli crawl-schedule "Core Frameworks Update"

# Run the Monthly Library Update
python -m ptolemies.cli crawl-schedule "Monthly Library Update"

# Crawl a specific URL
python -m ptolemies.cli crawl-url https://ai.pydantic.dev/ --depth 3 --tags pydantic,llm,tools --category "Core Frameworks"
```