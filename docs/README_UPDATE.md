# Updating Ptolemies Knowledge Base Content

This guide explains how to properly update the content in your Ptolemies Knowledge Base using the Crawl4AI content extraction approach.

## The Solution

The Crawl4AI MCP server implementation shows that webpage content should be stored directly in the `knowledge_item` table with `content_type: "text/html"`. It doesn't use a separate "webpages" table. 

Key points:
1. Crawl4AI uses the [trafilatura](https://github.com/adbar/trafilatura) library to extract clean content from HTML
2. The processed content is stored directly in the `knowledge_item.content` field
3. The `content_type` is set to "text/html" to indicate web content

## Steps to Update Content

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the update script:
   ```bash
   python update_content_crawl4ai.py
   ```

This will:
1. Retrieve all knowledge items from the database that need content updates
2. Fetch the content from each URL using the same extraction technique as Crawl4AI
3. Update the knowledge items with the processed content

## Technical Details

### Content Extraction

Content is extracted using the trafilatura library, with fallbacks to BeautifulSoup when needed:

```python
# Primary extraction with trafilatura
extracted_text = trafilatura.extract(
    html, 
    include_comments=False,
    include_tables=True,
    include_images=True,
    include_links=True
)

# Fallback to BeautifulSoup if needed
if not extracted_text:
    soup = BeautifulSoup(html, 'html.parser')
    # ... extraction logic ...
```

### Database Update

Knowledge items are updated in SurrealDB with:

```sql
UPDATE $id SET 
    content = $content,
    content_type = 'text/html',
    updated_at = time::now()
;
```

## Integration with the MCP Server

If you're using the MCP server for Crawl4AI, you can set it up following the instructions in:
`/Users/dionedge/devqai/mcp/mcp-servers/crawl4ai-mcp/README.md`

The MCP server includes a comprehensive pipeline for crawling, content extraction, and knowledge base integration.