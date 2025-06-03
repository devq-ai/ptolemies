# Ptolemies Webpage Storage Guide

This guide explains how to enhance the Ptolemies Knowledge Base system to properly store and reference full webpage content using Crawl4AI and SurrealDB.

## Architecture Overview

The enhanced architecture involves:

1. **Webpages Table**: A dedicated table in SurrealDB for storing full HTML content of webpages
2. **Knowledge Items**: Now reference the webpages table for complete content access
3. **Crawl4AI Integration**: Properly capturing webpage content during crawling

## Step 1: Update Schema with Webpages Table

Run the following script to create the webpages table and add references in the knowledge_item table:

```bash
python setup-webpages-schema.py
```

This creates:
- A `webpages` table for storing full webpage content
- Indexes for efficient retrieval by URL, domain, and crawl date
- A `webpage_id` field in the knowledge_item table to reference webpages

## Step 2: Store Existing Crawled Pages

To populate the webpages table with existing URLs:

```bash
python store-webpages.py
```

This script:
1. Reads URLs from crawl_results.md
2. Fetches the full HTML content for each URL
3. Stores the content in the webpages table
4. Updates knowledge_item records to reference the webpages

## Step 3: Update the Crawling Process

Modify the crawl-to-markdown.py file to store full HTML content in the webpages table during crawling:

1. When crawling a page, store the full HTML in the webpages table first
2. Create a knowledge_item that references the webpage entry
3. Extract meaningful content for the knowledge_item's content field

Example changes:
```python
# Step 1: Store the webpage in the webpages table
webpage_query = """
CREATE $id CONTENT {
    url: $url,
    html: $html,
    title: $title,
    domain: $domain,
    path: $path,
    crawl_date: $crawl_date,
    depth: $depth,
    target_info: $target_info
};
"""

# Step 2: Create the knowledge item with reference to the webpage
item_query = """
CREATE $id CONTENT {
    title: $title,
    content: $content,
    content_type: $content_type,
    source: $source,
    source_type: $source_type,
    category: $category,
    embedding_id: $embedding_id,
    webpage_id: $webpage_id,  # Reference to the webpage
    version: $version,
    tags: $tags,
    metadata: $metadata,
    created_at: time::now(),
    updated_at: time::now()
};
"""
```

## Step 4: Use Crawl4AI for Content Extraction

For best results with Crawl4AI:

1. Use the Crawl4AI API to extract cleaned content:
   ```python
   result = await crawler.arun(url="https://example.com")
   markdown_content = result.markdown  # Clean markdown for knowledge items
   html_content = result.html  # Full HTML for webpages table
   ```

2. Store both forms of content:
   - Raw HTML in the webpages table for complete preservation
   - Processed markdown in the knowledge_item for AI consumption

## Accessing Webpage Content

To retrieve a knowledge item with its associated webpage:

```sql
SELECT k.id, k.title, k.content, w.html 
FROM knowledge_item AS k
JOIN webpages AS w ON k.webpage_id = w.id
WHERE k.id = "knowledge_item:example";
```

## Benefits of This Approach

1. **Complete Data Preservation**: Raw HTML is stored for reference and future processing
2. **Cleaner Knowledge Items**: Knowledge items contain processed, AI-friendly content
3. **Storage Efficiency**: Prevents duplication by separating large HTML from metadata
4. **Enhanced Functionality**: Enables rebuilding knowledge items with different extraction techniques
5. **Content Evolution**: Allows updating knowledge representation without losing original source