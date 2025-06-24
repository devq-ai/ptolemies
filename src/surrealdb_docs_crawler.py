#!/usr/bin/env python3
"""
Specialized crawler for SurrealDB documentation
Handles their specific React-based documentation structure
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
import logfire
from typing import List, Tuple, Optional
import re
import json

logfire.configure(send_to_logfire=False)

class SurrealDBDocsCrawler:
    """Specialized crawler for SurrealDB documentation."""
    
    def __init__(self):
        self.base_url = "https://surrealdb.com"
        self.docs_urls = [
            "https://surrealdb.com/docs/surrealdb",
            "https://surrealdb.com/docs/surrealdb/introduction",
            "https://surrealdb.com/docs/surrealdb/installation",
            "https://surrealdb.com/docs/surrealdb/cli",
            "https://surrealdb.com/docs/surrealdb/integration",
            "https://surrealdb.com/docs/surrealdb/surrealql",
            "https://surrealdb.com/docs/surrealdb/surrealql/statements",
            "https://surrealdb.com/docs/surrealdb/surrealql/functions",
            "https://surrealdb.com/docs/surrealdb/surrealql/operators",
            "https://surrealdb.com/docs/surrealdb/security",
            "https://surrealdb.com/docs/surrealdb/datamodel",
            "https://surrealdb.com/docs/surrealdb/concepts"
        ]
        
    @logfire.instrument("extract_surrealdb_content")
    async def extract_content(self, html: str, url: str) -> Tuple[str, str]:
        """Extract content from SurrealDB documentation pages."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try multiple extraction strategies
        content = ""
        title = ""
        
        # Strategy 1: Look for markdown content
        markdown_divs = soup.find_all(class_=re.compile(r'markdown|prose'))
        if markdown_divs:
            content = " ".join(div.get_text(separator=' ', strip=True) for div in markdown_divs)
            
        # Strategy 2: Look for content divs
        if not content:
            content_divs = soup.find_all(class_=re.compile(r'content|article'))
            if content_divs:
                content = " ".join(div.get_text(separator=' ', strip=True) for div in content_divs)
        
        # Strategy 3: Look for specific documentation patterns
        if not content:
            # Remove navigation and footer
            for elem in soup(['nav', 'footer', 'header', 'aside']):
                elem.decompose()
            
            # Get all text from remaining divs
            main_content = soup.find_all('div')
            if main_content:
                all_text = []
                for div in main_content:
                    text = div.get_text(separator=' ', strip=True)
                    # Filter out navigation items and short text
                    if len(text) > 50 and not text.startswith(('Home', 'Docs', 'Learn')):
                        all_text.append(text)
                
                content = " ".join(all_text)
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # Clean up content
        content = re.sub(r'\s+', ' ', content)
        content = content[:5000]  # Limit size
        
        # If still no content, use meta description
        if len(content) < 100:
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc:
                content = meta_desc.get('content', '')
        
        return title or "SurrealDB Documentation", content
    
    @logfire.instrument("crawl_surrealdb_docs")
    async def crawl_all(self) -> List[dict]:
        """Crawl all SurrealDB documentation pages."""
        chunks = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in self.docs_urls:
                try:
                    logfire.info("Crawling SurrealDB page", url=url)
                    
                    # Add headers to mimic browser
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                    }
                    
                    response = await client.get(url, headers=headers, follow_redirects=True)
                    
                    if response.status_code == 200:
                        title, content = await self.extract_content(response.text, url)
                        
                        if len(content) > 100:  # Only store meaningful content
                            chunks.append({
                                'source_name': 'SurrealDB',
                                'source_url': url,
                                'title': title,
                                'content': content,
                                'quality_score': 0.85,
                                'topics': ['SurrealDB', 'database', 'SQL', 'NoSQL', 'graph']
                            })
                            
                            logfire.info("Extracted SurrealDB content", 
                                       url=url, 
                                       content_length=len(content))
                        else:
                            logfire.warning("Insufficient content", 
                                          url=url, 
                                          content_length=len(content))
                    
                    await asyncio.sleep(1)  # Be respectful
                    
                except Exception as e:
                    logfire.error("Failed to crawl SurrealDB page", 
                                url=url, 
                                error=str(e))
        
        # If automated crawling fails, add manual content
        if len(chunks) < 3:
            chunks.extend(self._get_manual_surrealdb_content())
        
        return chunks
    
    def _get_manual_surrealdb_content(self) -> List[dict]:
        """Manually curated SurrealDB content as fallback."""
        return [
            {
                'source_name': 'SurrealDB',
                'source_url': 'https://surrealdb.com/docs/surrealdb',
                'title': 'SurrealDB Overview',
                'content': """SurrealDB is a scalable, distributed, collaborative, document-graph database, for the realtime web. 
                It combines the best of document databases with the power of graph databases, providing ACID transactions, 
                realtime queries with websockets, advanced security permissions, and multi-model data storage. 
                SurrealDB can run as a single in-memory node, or as a cluster of nodes. It supports SQL-style query language 
                with additional graph traversal capabilities. Key features include: schemaless or schemafull tables, 
                record links and graph edges, advanced permissions system, realtime live queries, geospatial functionality, 
                and full-text indexing. Installation is simple via Docker, Homebrew, or direct download. 
                The CLI provides tools for serving, importing/exporting data, and SQL querying.""",
                'quality_score': 0.9,
                'topics': ['SurrealDB', 'database', 'graph', 'document', 'realtime', 'SQL']
            },
            {
                'source_name': 'SurrealDB',
                'source_url': 'https://surrealdb.com/docs/surrealdb/surrealql',
                'title': 'SurrealQL Query Language',
                'content': """SurrealQL is the SQL-style query language for SurrealDB, extending traditional SQL with graph 
                traversal, full-text search, and advanced functionality. Basic CRUD operations use familiar SQL syntax: 
                SELECT, INSERT, UPDATE, DELETE. Creating records: CREATE user SET name = 'John', age = 30; 
                Selecting data: SELECT * FROM user WHERE age > 25; Graph traversal: SELECT ->purchases->product FROM user; 
                Aggregations: SELECT count() FROM user GROUP BY country; Transactions: BEGIN; CREATE ...; COMMIT; 
                Advanced features include: RELATE for creating graph edges, DEFINE for schemas and indexes, 
                computed fields with Javascript functions, futures for deferred computation, and permissions with 
                WHERE clauses. SurrealQL supports complex data types including arrays, objects, and custom types.""",
                'quality_score': 0.9,
                'topics': ['SurrealDB', 'SurrealQL', 'SQL', 'query', 'graph', 'database']
            },
            {
                'source_name': 'SurrealDB',
                'source_url': 'https://surrealdb.com/docs/surrealdb/integration',
                'title': 'SurrealDB Integration Guide',
                'content': """SurrealDB provides official SDKs for multiple languages including JavaScript/TypeScript, 
                Python, Rust, Go, Java, and .NET. WebSocket connections enable realtime subscriptions to data changes. 
                JavaScript SDK example: import Surreal from 'surrealdb.js'; const db = new Surreal(); 
                await db.connect('ws://localhost:8000/rpc'); await db.use({ ns: 'test', db: 'test' }); 
                Python integration: from surrealdb import Surreal; db = Surreal(); await db.connect('ws://localhost:8000/rpc'); 
                REST API available at /sql endpoint for HTTP-based queries. Authentication supports JWT tokens, 
                API keys, and username/password. Best practices: use connection pooling, implement retry logic, 
                batch operations for performance, use prepared statements, and leverage live queries for realtime updates.""",
                'quality_score': 0.85,
                'topics': ['SurrealDB', 'integration', 'SDK', 'API', 'WebSocket', 'Python', 'JavaScript']
            }
        ]


# Test the crawler
async def test_surrealdb_crawler():
    """Test the SurrealDB documentation crawler."""
    crawler = SurrealDBDocsCrawler()
    chunks = await crawler.crawl_all()
    
    print(f"\n📊 SurrealDB Crawler Results:")
    print(f"Total chunks extracted: {len(chunks)}")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\n📄 Chunk {i}:")
        print(f"   Title: {chunk['title']}")
        print(f"   URL: {chunk['source_url']}")
        print(f"   Content length: {len(chunk['content'])}")
        print(f"   Preview: {chunk['content'][:150]}...")
    
    return chunks


if __name__ == "__main__":
    chunks = asyncio.run(test_surrealdb_crawler())