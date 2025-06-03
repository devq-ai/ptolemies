# Ptolemies Knowledge Base

Ptolemies is a knowledge management system for storing and retrieving URLs and their content in a SurrealDB database.

**Status**: Successfully stored 456 knowledge items from 606 processed URLs across 8 domains.

## Setup

1. Install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Set up SurrealDB:
   ```bash
   # Start SurrealDB (if not already running)
   surreal start --log info --user root --pass root --bind 0.0.0.0:8000 memory
   
   # Initialize schema (only needed once)
   python -m src.ptolemies.scripts.setup-schema
   ```

3. Configure environment variables (create a `.env` file):
   ```
   SURREALDB_URL=http://localhost:8000
   SURREALDB_NAMESPACE=ptolemies
   SURREALDB_DATABASE=knowledge
   SURREALDB_USERNAME=root
   SURREALDB_PASSWORD=root
   ```

## Usage

### Storing URLs in SurrealDB

The system can store URLs from the crawl results:

```bash
python -m src.ptolemies.cli
```

This will:
1. Read crawled URLs from `crawl_results.md`
2. Store them in SurrealDB as knowledge items
3. Add appropriate metadata and tags

### Crawling Websites

To crawl websites and generate the markdown file:

```bash
python crawl-to-markdown.py
```

## Directory Structure

- `crawl_results.md` - Contains 662 URLs from 8 domains
- `db_client.py` - Client for storing URLs in SurrealDB
- `setup-schema.py` - Sets up the SurrealDB schema
- `data/` - Configuration files including crawl targets
- `docs/` - Documentation and specifications

## Documentation

See the `docs/` directory for detailed documentation, including:
- System specifications
- SurrealDB integration details
- Crawl target configuration