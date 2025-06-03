#!/usr/bin/env python3
"""
Crawl Utility for Ptolemies Knowledge Base

This script provides a command-line utility for crawling web content
and adding it to the Ptolemies Knowledge Base.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

import httpx
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ptolemies.tools.crawl")

# Path to the crawl targets file
TARGETS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/crawl_targets.json")

class Crawler:
    """Web crawler for Ptolemies Knowledge Base."""
    
    def __init__(self, 
                 user_agent: str = "Ptolemies Knowledge Crawler/1.0",
                 respect_robots_txt: bool = True,
                 delay_ms: int = 1000,
                 timeout_s: int = 30):
        """Initialize the crawler.
        
        Args:
            user_agent: User agent string to use for requests
            respect_robots_txt: Whether to respect robots.txt
            delay_ms: Delay between requests in milliseconds
            timeout_s: Request timeout in seconds
        """
        self.user_agent = user_agent
        self.respect_robots_txt = respect_robots_txt
        self.delay_ms = delay_ms
        self.timeout_s = timeout_s
        self.visited_urls: Set[str] = set()
    
    async def crawl(self, 
                   url: str, 
                   depth: int = 2, 
                   max_pages: int = 100,
                   extract_code: bool = True,
                   extract_tables: bool = True) -> Dict[str, Any]:
        """Crawl a URL and its linked pages.
        
        Args:
            url: The URL to crawl
            depth: How deep to follow links (default: 2)
            max_pages: Maximum pages to crawl (default: 100)
            extract_code: Whether to extract code blocks
            extract_tables: Whether to extract tables
                
        Returns:
            Dictionary with crawl results
        """
        self.visited_urls = set()
        pages = []
        start_time = datetime.now()
        
        logger.info(f"Starting crawl of {url} with depth {depth}")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(5)
        
        async def _crawl_url(current_url: str, current_depth: int):
            if current_url in self.visited_urls:
                return
            
            if len(self.visited_urls) >= max_pages:
                return
            
            if current_depth > depth:
                return
            
            # Mark as visited before processing to avoid duplicates
            self.visited_urls.add(current_url)
            
            # Apply rate limiting with semaphore
            async with semaphore:
                try:
                    # Apply delay
                    await asyncio.sleep(self.delay_ms / 1000)
                    
                    logger.debug(f"Crawling {current_url} (depth {current_depth})")
                    
                    # Fetch the page
                    async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                        headers = {"User-Agent": self.user_agent}
                        response = await client.get(current_url, headers=headers, follow_redirects=True)
                        response.raise_for_status()
                        
                        # Process the page content
                        page_data = await self._process_page(
                            current_url,
                            response.text,
                            extract_code=extract_code,
                            extract_tables=extract_tables
                        )
                        
                        pages.append(page_data)
                        
                        # If we're at max depth, don't extract links
                        if current_depth >= depth:
                            return
                        
                        # Extract links and crawl them
                        links = self._extract_links(current_url, response.text)
                        tasks = []
                        
                        for link in links:
                            if link not in self.visited_urls and len(self.visited_urls) < max_pages:
                                tasks.append(_crawl_url(link, current_depth + 1))
                        
                        if tasks:
                            await asyncio.gather(*tasks)
                    
                except Exception as e:
                    logger.error(f"Error crawling {current_url}: {e}")
        
        # Start crawling from the initial URL
        await _crawl_url(url, 1)
        
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Prepare the result
        result = {
            "pages": pages,
            "stats": {
                "pages_crawled": len(pages),
                "total_content_bytes": sum(len(page.get("content", "")) for page in pages),
                "time_ms": int(duration_ms),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        }
        
        logger.info(f"Crawl completed: {len(pages)} pages crawled in {duration_ms:.0f}ms")
        return result
    
    async def _process_page(self, 
                           url: str, 
                           html: str,
                           extract_code: bool = True,
                           extract_tables: bool = True) -> Dict[str, Any]:
        """Process a page and extract its content.
        
        Args:
            url: The URL of the page
            html: The HTML content of the page
            extract_code: Whether to extract code blocks
            extract_tables: Whether to extract tables
            
        Returns:
            Dictionary with processed page data
        """
        # Use trafilatura for main content extraction
        extracted_text = trafilatura.extract(html, include_comments=False, 
                                            include_tables=extract_tables, 
                                            include_images=True,
                                            include_links=True)
        
        # Fallback to BeautifulSoup if trafilatura fails
        if not extracted_text:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to get the article or main content
            main_content = None
            for selector in ['article', 'main', '.content', '#content', '.post', '.article']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if main_content:
                extracted_text = main_content.get_text(separator='\n\n')
            else:
                # Fallback to body
                extracted_text = soup.body.get_text(separator='\n\n') if soup.body else ""
        
        # Extract metadata
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title else ""
        
        # Extract meta description
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        
        # Extract code blocks if requested
        code_blocks = []
        if extract_code:
            for pre in soup.find_all('pre'):
                code = pre.get_text()
                if code and len(code.strip()) > 0:
                    code_blocks.append(code)
        
        # Extract tables if requested
        tables = []
        if extract_tables:
            for table in soup.find_all('table'):
                tables.append(str(table))
        
        # Prepare the page data
        page_data = {
            "url": url,
            "title": title,
            "description": description,
            "content": extracted_text,
            "code_blocks": code_blocks,
            "tables": tables,
            "metadata": {
                "crawl_time": datetime.now().isoformat(),
                "content_type": soup.find('meta', {'http-equiv': 'Content-Type'})['content'] if soup.find('meta', {'http-equiv': 'Content-Type'}) else "text/html"
            }
        }
        
        return page_data
    
    def _extract_links(self, base_url: str, html: str) -> List[str]:
        """Extract links from HTML content.
        
        Args:
            base_url: The base URL for resolving relative links
            html: The HTML content
            
        Returns:
            List of absolute URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        base_domain = urlparse(base_url).netloc
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # Skip fragment links
            if href.startswith('#'):
                continue
            
            # Skip JavaScript links
            if href.startswith('javascript:'):
                continue
            
            # Skip mailto links
            if href.startswith('mailto:'):
                continue
            
            # Make relative URLs absolute
            absolute_url = urljoin(base_url, href)
            
            # Only include links to the same domain
            parsed_url = urlparse(absolute_url)
            if parsed_url.netloc == base_domain:
                # Normalize URL (remove fragments)
                normalized_url = parsed_url._replace(fragment='').geturl()
                links.append(normalized_url)
        
        return links

class KnowledgeImporter:
    """Import crawled content into Ptolemies Knowledge Base."""
    
    def __init__(self):
        """Initialize the knowledge importer."""
        self.db_client = None
    
    async def connect_to_db(self):
        """Connect to SurrealDB."""
        import httpx
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        db_host = os.getenv("SURREALDB_HOST", "localhost")
        db_port = os.getenv("SURREALDB_PORT", "8000")
        db_user = os.getenv("SURREALDB_USER", "root")
        db_pass = os.getenv("SURREALDB_PASS", "root")
        db_ns = os.getenv("SURREALDB_NAMESPACE", "ptolemies")
        db_name = os.getenv("SURREALDB_DATABASE", "knowledge")
        
        url = f"http://{db_host}:{db_port}"
        
        # Create HTTP client for SurrealDB
        self.db_client = httpx.AsyncClient(
            base_url=url,
            auth=(db_user, db_pass),
            timeout=30.0,
            headers={"Content-Type": "application/json"}
        )
        
        # Authenticate and select namespace/database
        payload = {
            "ns": db_ns,
            "db": db_name
        }
        
        response = await self.db_client.post("/use", json=payload)
        response.raise_for_status()
        
        logger.info(f"Connected to SurrealDB at {url}")
    
    async def import_pages(self, pages: List[Dict[str, Any]], 
                          tags: List[str] = None, 
                          category: str = None) -> List[str]:
        """Import crawled pages into the knowledge base.
        
        Args:
            pages: List of crawled pages
            tags: Tags to apply to all knowledge items
            category: Category for all knowledge items
            
        Returns:
            List of created knowledge item IDs
        """
        if not self.db_client:
            await self.connect_to_db()
        
        item_ids = []
        tags = tags or []
        
        for page in pages:
            try:
                # Create a knowledge item from the page
                knowledge_item = {
                    "title": page.get("title", "Untitled"),
                    "content": page.get("content", ""),
                    "source": page.get("url", ""),
                    "source_type": "web",
                    "content_type": "text/html",
                    "tags": tags,
                    "category": category,
                    "metadata": {
                        "crawl_timestamp": datetime.now().isoformat(),
                        "description": page.get("description", ""),
                        "has_code_blocks": len(page.get("code_blocks", [])) > 0,
                        "has_tables": len(page.get("tables", [])) > 0,
                        "page_metadata": page.get("metadata", {})
                    },
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                # Store in SurrealDB
                response = await self.db_client.post(
                    "/key/knowledge_item", 
                    json=knowledge_item
                )
                response.raise_for_status()
                
                result = response.json()
                if result and len(result) > 0:
                    item_id = result[0].get("id")
                    item_ids.append(item_id)
                    logger.debug(f"Created knowledge item: {item_id}")
                
            except Exception as e:
                logger.error(f"Error storing knowledge item: {e}")
        
        logger.info(f"Imported {len(item_ids)} knowledge items")
        return item_ids
    
    async def request_embeddings(self, item_ids: List[str]):
        """Request embedding generation for knowledge items.
        
        Args:
            item_ids: List of knowledge item IDs
        """
        if not item_ids:
            return
            
        if not self.db_client:
            await self.connect_to_db()
        
        # Get embedding configuration
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai")
        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        try:
            # Create SurrealQL query to update items
            query = f"""
            BEGIN TRANSACTION;
            
            LET $items = SELECT * FROM knowledge_item 
                WHERE id IN $item_ids 
                AND (embedding IS NONE OR embedding_model != $model);
                
            FOR $item IN $items {{
                UPDATE $item SET 
                    embedding_requested = true,
                    embedding_model = $model,
                    embedding_provider = $provider,
                    embedding_requested_at = time::now()
                WHERE id = $item.id;
            }}
            
            COMMIT TRANSACTION;
            """
            
            params = {
                "item_ids": item_ids,
                "model": embedding_model,
                "provider": embedding_provider
            }
            
            response = await self.db_client.post("/sql", json={"q": query, "v": params})
            response.raise_for_status()
            
            logger.info(f"Requested embeddings for {len(item_ids)} knowledge items")
            
        except Exception as e:
            logger.error(f"Error requesting embeddings: {e}")

async def crawl_url(url: str, depth: int, tags: List[str], category: str, 
                   extract_code: bool, extract_tables: bool,
                   max_pages: int, respect_robots_txt: bool,
                   delay_ms: int, user_agent: str) -> Dict[str, Any]:
    """Crawl a URL and import the content into the knowledge base."""
    logger.info(f"Crawling {url} (depth: {depth}, category: {category})")
    
    # Create crawler
    crawler = Crawler(
        user_agent=user_agent,
        respect_robots_txt=respect_robots_txt,
        delay_ms=delay_ms
    )
    
    # Crawl the URL
    crawl_result = await crawler.crawl(
        url=url,
        depth=depth,
        max_pages=max_pages,
        extract_code=extract_code,
        extract_tables=extract_tables
    )
    
    # Import the pages
    importer = KnowledgeImporter()
    await importer.connect_to_db()
    
    item_ids = await importer.import_pages(
        pages=crawl_result["pages"],
        tags=tags,
        category=category
    )
    
    # Request embeddings
    await importer.request_embeddings(item_ids)
    
    return {
        "url": url,
        "crawl_stats": crawl_result["stats"],
        "knowledge_items_created": len(item_ids),
        "knowledge_item_ids": item_ids
    }

async def crawl_from_targets(targets_file: str) -> Dict[str, Any]:
    """Crawl content from targets defined in a JSON file."""
    logger.info(f"Crawling content from targets in {targets_file}")
    
    # Load targets file
    with open(targets_file, "r") as f:
        data = json.load(f)
    
    targets = data.get("targets", [])
    default_config = data.get("default_config", {})
    
    if not targets:
        logger.warning("No targets found in targets file")
        return {"status": "error", "message": "No targets found"}
    
    logger.info(f"Found {len(targets)} targets to process")
    
    results = []
    
    for target in targets:
        url = target.get("url")
        if not url:
            logger.warning("Target missing URL, skipping")
            continue
        
        try:
            # Combine default config with target-specific settings
            depth = target.get("depth", 2)
            tags = target.get("tags", [])
            category = target.get("category", "Uncategorized")
            priority = target.get("priority", "medium")
            
            extract_code = target.get("extract_code", default_config.get("extract_code", True))
            extract_tables = target.get("extract_tables", default_config.get("extract_tables", True))
            respect_robots_txt = target.get("respect_robots_txt", default_config.get("respect_robots_txt", True))
            user_agent = target.get("user_agent", default_config.get("user_agent", "Ptolemies Knowledge Crawler/1.0"))
            
            # Adjust max_pages and delay based on priority
            max_pages = {
                "critical": 200,
                "high": 100,
                "medium": 50,
                "low": 20
            }.get(priority, 50)
            
            delay_ms = {
                "critical": 500,
                "high": 1000,
                "medium": 1500,
                "low": 2000
            }.get(priority, 1000)
            
            # Crawl the URL
            result = await crawl_url(
                url=url,
                depth=depth,
                tags=tags,
                category=category,
                extract_code=extract_code,
                extract_tables=extract_tables,
                max_pages=max_pages,
                respect_robots_txt=respect_robots_txt,
                delay_ms=delay_ms,
                user_agent=user_agent
            )
            
            results.append({
                "target_name": target.get("name", url),
                "result": result
            })
            
            logger.info(f"Completed crawl for {url}")
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            results.append({
                "target_name": target.get("name", url),
                "error": str(e)
            })
    
    return {
        "status": "success",
        "targets_processed": len(results),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }

def main():
    """Main entry point for the crawl utility."""
    parser = argparse.ArgumentParser(description="Ptolemies Knowledge Base Crawl Utility")
    
    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Crawl URL command
    url_parser = subparsers.add_parser("url", help="Crawl a URL")
    url_parser.add_argument("url", help="URL to crawl")
    url_parser.add_argument("--depth", type=int, default=2, help="Crawl depth")
    url_parser.add_argument("--tags", nargs="+", default=[], help="Tags to apply")
    url_parser.add_argument("--category", default="Uncategorized", help="Content category")
    url_parser.add_argument("--extract-code", action="store_true", help="Extract code blocks")
    url_parser.add_argument("--extract-tables", action="store_true", help="Extract tables")
    url_parser.add_argument("--max-pages", type=int, default=100, help="Maximum pages to crawl")
    
    # Crawl from targets file command
    targets_parser = subparsers.add_parser("targets", help="Crawl from targets file")
    targets_parser.add_argument(
        "--file", 
        default=TARGETS_FILE,
        help="Path to targets JSON file"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Run the appropriate command
    if args.command == "url":
        result = asyncio.run(crawl_url(
            url=args.url,
            depth=args.depth,
            tags=args.tags,
            category=args.category,
            extract_code=args.extract_code,
            extract_tables=args.extract_tables,
            max_pages=args.max_pages,
            respect_robots_txt=True,
            delay_ms=1000,
            user_agent="Ptolemies Knowledge Crawler/1.0"
        ))
        print(json.dumps(result, indent=2))
        
    elif args.command == "targets":
        if not os.path.exists(args.file):
            logger.error(f"Targets file not found: {args.file}")
            return 1
            
        result = asyncio.run(crawl_from_targets(args.file))
        print(json.dumps(result, indent=2))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())