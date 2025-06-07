#!/usr/bin/env python3
"""
Real Crawl4AI Integration for Ptolemies Knowledge Base

This module provides REAL web crawling functionality using the crawl4ai library
to replace the simulation code. Implements true depth-3 crawling with proper
link discovery, content extraction, and politeness controls.

Features:
- True depth-3 breadth-first crawling
- Intelligent link discovery and filtering
- Content quality assessment
- Rate limiting and politeness
- Robust error handling and recovery
- Progress tracking and reporting

Usage:
    from ptolemies.integrations.crawl4ai.real_crawler import RealCrawlManager
    
    crawler = RealCrawlManager()
    result = await crawler.crawl_url("https://example.com", depth=3)
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse, urlunparse
from collections import deque, defaultdict
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class CrawlResult:
    """Result of crawling a single page."""
    url: str
    title: str
    content: str
    clean_text: str
    links: List[str]
    depth: int
    timestamp: str
    status: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class CrawlStats:
    """Statistics for a crawl operation."""
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    total_content_bytes: int = 0
    start_time: float = 0
    end_time: float = 0
    duration_seconds: float = 0
    pages_per_second: float = 0

class RealCrawlManager:
    """Real web crawler using crawl4ai library for depth-3 crawling."""
    
    def __init__(self, 
                 max_pages_per_domain: int = 100,
                 delay_between_requests: float = 1.0,
                 max_concurrent_requests: int = 3,
                 timeout_seconds: int = 30):
        """Initialize the real crawler.
        
        Args:
            max_pages_per_domain: Maximum pages to crawl per domain
            delay_between_requests: Delay between requests in seconds
            max_concurrent_requests: Maximum concurrent requests
            timeout_seconds: Request timeout in seconds
        """
        self.max_pages_per_domain = max_pages_per_domain
        self.delay_between_requests = delay_between_requests
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout_seconds = timeout_seconds
        
        self.logger = logging.getLogger("ptolemies.integrations.crawl4ai.real")
        
        # Crawl state
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.crawl_queue: deque = deque()
        self.results: List[CrawlResult] = []
        self.stats = CrawlStats()
        
        # Configure crawl4ai
        self.crawler_config = {
            "headless": True,
            "browser_type": "chromium",
            "verbose": False,
            "delay_before_return_html": 2.0,
            "timeout": timeout_seconds * 1000,  # Convert to milliseconds
        }
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent comparison."""
        parsed = urlparse(url)
        # Remove fragment and normalize
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip('/') if parsed.path != '/' else '/',
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        return normalized
    
    def _is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL is valid for crawling."""
        try:
            parsed = urlparse(url)
            
            # Must be HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Must be same domain
            if parsed.netloc.lower() != base_domain.lower():
                return False
            
            # Skip common non-content URLs
            skip_patterns = [
                r'\.(?:pdf|jpg|jpeg|png|gif|svg|ico|css|js|woff|woff2|ttf)$',
                r'/(?:search|login|register|logout|admin|api)/',
                r'#',  # Fragment-only links
                r'mailto:',
                r'tel:',
                r'javascript:',
            ]
            
            url_lower = url.lower()
            for pattern in skip_patterns:
                if re.search(pattern, url_lower):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and filter links from HTML content."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            base_domain = urlparse(base_url).netloc
            
            links = []
            
            # Find all anchor tags with href
            for anchor in soup.find_all('a', href=True):
                href = anchor['href'].strip()
                
                if not href:
                    continue
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                normalized_url = self._normalize_url(absolute_url)
                
                # Validate and filter
                if self._is_valid_url(normalized_url, base_domain):
                    links.append(normalized_url)
            
            # Remove duplicates while preserving order
            unique_links = []
            seen = set()
            for link in links:
                if link not in seen:
                    unique_links.append(link)
                    seen.add(link)
            
            return unique_links
            
        except Exception as e:
            self.logger.warning(f"Error extracting links from {base_url}: {e}")
            return []
    
    def _extract_clean_text(self, html: str) -> str:
        """Extract clean text content from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            self.logger.warning(f"Error extracting clean text: {e}")
            return ""
    
    def _assess_content_quality(self, content: str, title: str) -> float:
        """Assess the quality of crawled content (0.0 to 1.0)."""
        try:
            score = 0.0
            
            # Length score (more content is generally better)
            if len(content) > 5000:
                score += 0.3
            elif len(content) > 1000:
                score += 0.2
            elif len(content) > 500:
                score += 0.1
            
            # Title score
            if title and len(title.strip()) > 0:
                score += 0.2
            
            # Structure score (presence of common content indicators)
            content_lower = content.lower()
            if any(word in content_lower for word in ['documentation', 'guide', 'tutorial', 'reference']):
                score += 0.2
            
            # Code/technical content score
            if any(word in content_lower for word in ['function', 'class', 'method', 'example', 'code']):
                score += 0.2
            
            # Avoid low-quality content
            if any(word in content_lower for word in ['404', 'not found', 'error', 'sorry']):
                score -= 0.3
            
            return min(1.0, max(0.0, score))
            
        except Exception:
            return 0.5  # Default neutral score
    
    async def _crawl_single_page(self, url: str, depth: int) -> Optional[CrawlResult]:
        """Crawl a single page and extract content."""
        try:
            self.logger.info(f"  📄 Crawling (depth {depth}): {url}")
            
            # Use crawl4ai for robust content extraction
            async with AsyncWebCrawler(**self.crawler_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    extraction_strategy=LLMExtractionStrategy(
                        provider="openai",
                        api_token=None,  # Will use environment variable
                        instruction="Extract the main content, removing navigation and footer elements"
                    ) if False else None,  # Disable LLM extraction for now
                    bypass_cache=True,
                    process_iframes=False,
                    remove_overlay_elements=True
                )
                
                if not result.success:
                    raise Exception(f"Crawl4AI failed: {result.error_message}")
                
                # Extract title
                soup = BeautifulSoup(result.html, 'html.parser')
                title = ""
                if soup.title:
                    title = soup.title.string.strip() if soup.title.string else ""
                
                # Extract links for further crawling
                links = self._extract_links(result.html, url)
                
                # Get clean text
                clean_text = self._extract_clean_text(result.html)
                
                # Assess content quality
                quality_score = self._assess_content_quality(clean_text, title)
                
                crawl_result = CrawlResult(
                    url=url,
                    title=title,
                    content=result.html,
                    clean_text=clean_text,
                    links=links,
                    depth=depth,
                    timestamp=datetime.now().isoformat(),
                    status="success",
                    metadata={
                        "quality_score": quality_score,
                        "content_length": len(result.html),
                        "clean_text_length": len(clean_text),
                        "links_found": len(links),
                        "crawl4ai_metadata": {
                            "links": result.links,
                            "media": result.media,
                        }
                    }
                )
                
                self.logger.info(f"    ✅ Success: {len(clean_text)} chars, {len(links)} links, quality {quality_score:.2f}")
                return crawl_result
                
        except Exception as e:
            error_msg = str(e)
            self.logger.warning(f"    ❌ Failed to crawl {url}: {error_msg}")
            
            return CrawlResult(
                url=url,
                title="",
                content="",
                clean_text="",
                links=[],
                depth=depth,
                timestamp=datetime.now().isoformat(),
                status="failed",
                error=error_msg
            )
    
    async def crawl_url(self, 
                       url: str, 
                       depth: int = 3,
                       **kwargs) -> Dict[str, Any]:
        """Crawl a URL and its linked pages to specified depth.
        
        Args:
            url: The base URL to start crawling
            depth: Maximum depth to crawl (1 = only base URL, 3 = three levels)
            **kwargs: Additional parameters (for compatibility)
            
        Returns:
            Dictionary with crawl results and statistics
        """
        self.logger.info(f"🕷️  Starting real depth-{depth} crawl: {url}")
        
        # Initialize crawl state
        self.visited_urls.clear()
        self.failed_urls.clear()
        self.crawl_queue.clear()
        self.results.clear()
        self.stats = CrawlStats()
        self.stats.start_time = time.time()
        
        # Get base domain for filtering
        base_domain = urlparse(url).netloc
        
        # Add initial URL to queue
        self.crawl_queue.append((self._normalize_url(url), 0))
        
        try:
            while self.crawl_queue and len(self.results) < self.max_pages_per_domain:
                current_url, current_depth = self.crawl_queue.popleft()
                
                # Skip if already visited or depth exceeded
                if current_url in self.visited_urls or current_depth > depth:
                    continue
                
                self.visited_urls.add(current_url)
                
                # Crawl the page
                result = await self._crawl_single_page(current_url, current_depth)
                
                if result:
                    self.results.append(result)
                    
                    if result.status == "success":
                        self.stats.successful_pages += 1
                        self.stats.total_content_bytes += len(result.content)
                        
                        # Add discovered links to queue for next depth level
                        if current_depth < depth:
                            for link in result.links:
                                normalized_link = self._normalize_url(link)
                                if (normalized_link not in self.visited_urls and 
                                    normalized_link not in self.failed_urls):
                                    self.crawl_queue.append((normalized_link, current_depth + 1))
                    else:
                        self.stats.failed_pages += 1
                        self.failed_urls.add(current_url)
                
                self.stats.total_pages += 1
                
                # Progress update
                if self.stats.total_pages % 10 == 0:
                    self.logger.info(f"  📊 Progress: {self.stats.successful_pages} successful, {len(self.crawl_queue)} queued")
                
                # Politeness delay
                if self.delay_between_requests > 0:
                    await asyncio.sleep(self.delay_between_requests)
            
            # Finalize statistics
            self.stats.end_time = time.time()
            self.stats.duration_seconds = self.stats.end_time - self.stats.start_time
            if self.stats.duration_seconds > 0:
                self.stats.pages_per_second = self.stats.successful_pages / self.stats.duration_seconds
            
            # Prepare results
            successful_results = [r for r in self.results if r.status == "success"]
            
            crawl_summary = {
                "pages": [
                    {
                        "url": result.url,
                        "title": result.title,
                        "content": result.content,
                        "depth": result.depth,
                        "timestamp": result.timestamp,
                        "metadata": result.metadata or {}
                    }
                    for result in successful_results
                ],
                "stats": {
                    "pages_crawled": self.stats.successful_pages,
                    "pages_failed": self.stats.failed_pages,
                    "total_content_bytes": self.stats.total_content_bytes,
                    "duration_seconds": self.stats.duration_seconds,
                    "pages_per_second": self.stats.pages_per_second,
                    "depth_achieved": depth,
                    "base_url": url,
                    "domain": base_domain
                },
                "failed_urls": list(self.failed_urls),
                "metadata": {
                    "crawler": "real_crawl4ai",
                    "version": "1.0.0",
                    "timestamp": datetime.now().isoformat(),
                    "configuration": {
                        "max_pages": self.max_pages_per_domain,
                        "delay_seconds": self.delay_between_requests,
                        "timeout_seconds": self.timeout_seconds
                    }
                }
            }
            
            self.logger.info(f"✅ Crawl completed: {self.stats.successful_pages} pages in {self.stats.duration_seconds:.1f}s")
            
            return crawl_summary
            
        except Exception as e:
            self.logger.error(f"❌ Crawl failed with error: {e}")
            raise
    
    async def process_results(self, crawl_results: Dict[str, Any]) -> List[str]:
        """Process crawl results and store in knowledge base.
        
        Args:
            crawl_results: Results from crawl_url()
            
        Returns:
            List of created knowledge item IDs
        """
        self.logger.info(f"💾 Processing {len(crawl_results.get('pages', []))} crawled pages...")
        
        try:
            # Import here to avoid circular imports
            from ptolemies.db.surrealdb_client import SurrealDBClient
            from ptolemies.models.knowledge_item import KnowledgeItemCreate
            
            db_client = SurrealDBClient()
            await db_client.connect()
            
            item_ids = []
            
            for page_data in crawl_results.get("pages", []):
                try:
                    # Create knowledge item
                    item_create = KnowledgeItemCreate(
                        title=page_data.get("title", "Unknown"),
                        content=page_data.get("content", ""),
                        content_type="text/html",
                        metadata={
                            "crawl_timestamp": page_data.get("timestamp"),
                            "crawl_depth": page_data.get("depth", 0),
                            "crawl_metadata": page_data.get("metadata", {}),
                            "base_crawl_url": crawl_results.get("stats", {}).get("base_url"),
                            "crawler_version": "real_crawl4ai_v1.0.0"
                        },
                        tags=["crawled", "depth-3", "real-crawler"],
                        source=page_data.get("url", "")
                    )
                    
                    # Save to database
                    item = await db_client.create_knowledge_item(item_create)
                    item_ids.append(item.id)
                    
                    self.logger.debug(f"  ✅ Stored: {page_data.get('url', 'Unknown')}")
                    
                except Exception as e:
                    self.logger.error(f"  ❌ Failed to store {page_data.get('url', 'Unknown')}: {e}")
            
            await db_client.disconnect()
            
            self.logger.info(f"✅ Successfully stored {len(item_ids)} knowledge items")
            return item_ids
            
        except Exception as e:
            self.logger.error(f"❌ Failed to process crawl results: {e}")
            return []

# Compatibility wrapper to replace the simulation crawler
class CrawlManager(RealCrawlManager):
    """Drop-in replacement for the simulation CrawlManager."""
    
    def __init__(self, mcp_endpoint: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize with compatibility for existing code."""
        super().__init__()
        self.logger.info("🔧 Using REAL crawler instead of simulation")
        
        # Log that MCP parameters are ignored in favor of direct crawling
        if mcp_endpoint or api_key:
            self.logger.info("ℹ️  MCP endpoint/API key parameters ignored - using direct crawling")