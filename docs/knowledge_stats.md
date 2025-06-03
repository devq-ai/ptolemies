# Knowledge Base Statistics

## SurrealDB Knowledge Items

As of June 1, 2025, the SurrealDB knowledge base contains:

- **456 Knowledge Items** stored from crawled URLs
- **8 Domains** crawled, including:
  - https://ai.pydantic.dev/
  - https://www.pymc.io/
  - https://wildwood.readthedocs.io/
  - https://logfire.pydantic.dev/docs/
  - https://docs.crawl4ai.com/
  - https://surrealdb.com/docs/surrealdb
  - https://help.getzep.com/concepts
  - https://fastapi.tiangolo.com/

Each knowledge item contains:
- URL
- Title
- Content
- Tags (domain, depth, source category)
- Metadata (crawl date, path, domain)

## Database Schema

The knowledge_item table uses the following schema:

```sql
DEFINE TABLE knowledge_item SCHEMALESS;
DEFINE INDEX knowledge_item_title ON TABLE knowledge_item COLUMNS title;
DEFINE INDEX knowledge_item_source ON TABLE knowledge_item COLUMNS source;
DEFINE INDEX knowledge_item_category ON TABLE knowledge_item COLUMNS category;
```

## Data Integrity

All URLs are stored with unique IDs generated from MD5 hashes of the original URL, ensuring:
- No duplicate entries
- Reliable lookups
- Consistent storage regardless of URL complexity

## Storage Efficiency

The 456 knowledge items were stored in 13 batches of 50 URLs each, with:
- Total processing time: ~0.13 seconds
- Average batch processing time: 0.01 seconds
- Nearly 100% success rate (all 606 URLs processed, 456 stored as unique items)

The difference between processed URLs (606) and stored items (456) is likely due to duplicate URLs with different anchors (#) or trailing slashes.