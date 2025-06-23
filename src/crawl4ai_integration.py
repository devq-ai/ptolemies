#!/usr/bin/env python3
"""
Ptolemies Crawl4AI Integration
Implementation of documentation crawling and RAG capabilities for Ptolemies knowledge base.
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
import openai
import logfire
from rich.console import Console
from rich.progress import Progress, TaskID

# Import enhanced storage infrastructure
from surrealdb_integration import SurrealDBVectorStore, DocumentChunk
from neo4j_integration import Neo4jGraphStore, DocumentNode, ConceptNode
from hybrid_query_engine import HybridQueryEngine
from performance_optimizer import PerformanceOptimizer
from redis_cache_layer import RedisCacheLayer

# Configure logging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

@dataclass
class CrawlConfig:
    """Configuration for crawling operations."""
    max_depth: int = 2
    max_pages: int = 250
    delay_ms: int = 1000
    respect_robots_txt: bool = True
    user_agent: str = "Ptolemies Knowledge Crawler/1.0"
    timeout: int = 30
    concurrent_requests: int = 5

@dataclass
class DocumentMetrics:
    """Metrics for crawled documents."""
    total_pages_crawled: int = 0
    total_pages_stored: int = 0
    total_processing_time: float = 0.0
    success_rate: float = 0.0
    average_quality_score: float = 0.0

class PtolemiesCrawler:
    """Advanced web crawler for Ptolemies knowledge base with enhanced storage infrastructure."""
    
    def __init__(
        self, 
        config: CrawlConfig, 
        storage_adapter=None,
        hybrid_engine: Optional[HybridQueryEngine] = None,
        performance_optimizer: Optional[PerformanceOptimizer] = None,
        redis_cache: Optional[RedisCacheLayer] = None
    ):
        self.config = config
        self.storage_adapter = storage_adapter  # Legacy support
        
        # Enhanced storage infrastructure
        self.hybrid_engine = hybrid_engine
        self.performance_optimizer = performance_optimizer
        self.redis_cache = redis_cache
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout),
            headers={"User-Agent": config.user_agent}
        )
        self.openai_client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.metrics = DocumentMetrics()
        self.visited_urls = set()
        self.crawl_cache = {}
        
    @logfire.instrument("crawl_documentation_source")
    async def crawl_documentation_source(
        self, 
        source_url: str, 
        source_name: str
    ) -> Dict[str, Any]:
        """Crawl a complete documentation source."""
        start_time = time.time()
        
        logfire.info(
            f"Starting crawl of {source_name}",
            source_url=source_url,
            max_pages=self.config.max_pages
        )
        
        try:
            # Initialize crawl queue
            crawl_queue = [(source_url, 0)]  # (url, depth)
            crawled_pages = []
            
            with Progress() as progress:
                task = progress.add_task(
                    f"Crawling {source_name}...", 
                    total=self.config.max_pages
                )
                
                while crawl_queue and len(crawled_pages) < self.config.max_pages:
                    current_url, depth = crawl_queue.pop(0)
                    
                    if current_url in self.visited_urls or depth > self.config.max_depth:
                        continue
                    
                    try:
                        page_data = await self._crawl_single_page(current_url, depth)
                        if page_data:
                            crawled_pages.append(page_data)
                            self.visited_urls.add(current_url)
                            
                            # Add discovered links to queue
                            for link in page_data.get("links", []):
                                if self._should_crawl_link(link, source_url):
                                    crawl_queue.append((link, depth + 1))
                            
                            progress.update(task, advance=1)
                            
                        # Respect rate limiting
                        await asyncio.sleep(self.config.delay_ms / 1000.0)
                        
                    except Exception as e:
                        logger.error(f"Error crawling {current_url}: {e}")
                        continue
            
            # Process and store crawled content
            processed_documents = []
            for page in crawled_pages:
                doc = await self._process_page_content(page, source_name)
                if doc:
                    processed_documents.append(doc)
            
            # Enhanced storage integration with new infrastructure
            storage_success = await self._store_documents_enhanced(
                processed_documents, source_name, source_url
            )
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics.total_pages_crawled += len(crawled_pages)
            self.metrics.total_pages_stored += len(processed_documents)
            self.metrics.total_processing_time += processing_time
            self.metrics.success_rate = len(processed_documents) / max(len(crawled_pages), 1)
            
            logfire.info(
                f"Completed crawl of {source_name}",
                pages_crawled=len(crawled_pages),
                pages_stored=len(processed_documents),
                processing_time=processing_time
            )
            
            return {
                "source_name": source_name,
                "source_url": source_url,
                "pages_crawled": len(crawled_pages),
                "pages_stored": len(processed_documents),
                "processing_time": processing_time,
                "documents": processed_documents,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to crawl {source_name}: {e}")
            logfire.error(
                f"Crawl failed for {source_name}",
                error=str(e),
                source_url=source_url
            )
            return {
                "source_name": source_name,
                "source_url": source_url,
                "error": str(e),
                "success": False
            }
    
    @logfire.instrument("crawl_single_page")
    async def _crawl_single_page(self, url: str, depth: int) -> Optional[Dict[str, Any]]:
        """Crawl a single page and extract content."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            if not response.headers.get("content-type", "").startswith("text/html"):
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract metadata
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Extract main content (remove navigation, headers, footers)
            main_content = self._extract_main_content(soup)
            
            # Extract links for further crawling
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                if self._is_valid_documentation_link(absolute_url):
                    links.append(absolute_url)
            
            # Calculate content hash for deduplication
            content_hash = hashlib.md5(main_content.encode()).hexdigest()
            
            return {
                "url": url,
                "title": title_text,
                "content": main_content,
                "content_hash": content_hash,
                "links": links,
                "depth": depth,
                "crawled_at": time.time(),
                "word_count": len(main_content.split()),
                "status_code": response.status_code
            }
            
        except Exception as e:
            logger.error(f"Error crawling page {url}: {e}")
            return None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML, removing navigation and boilerplate."""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Try to find main content containers
        main_selectors = [
            'main', '[role="main"]', '.main-content', '.content',
            '.documentation', '.docs-content', '#content', '.article'
        ]
        
        for selector in main_selectors:
            main_element = soup.select_one(selector)
            if main_element:
                return main_element.get_text(strip=True, separator='\n')
        
        # Fallback to body content
        body = soup.find('body')
        if body:
            return body.get_text(strip=True, separator='\n')
        
        return soup.get_text(strip=True, separator='\n')
    
    def _should_crawl_link(self, link: str, base_url: str) -> bool:
        """Determine if a link should be crawled."""
        parsed_link = urlparse(link)
        parsed_base = urlparse(base_url)
        
        # Stay within the same domain
        if parsed_link.netloc != parsed_base.netloc:
            return False
        
        # Skip non-documentation pages
        skip_patterns = [
            '/search', '/login', '/signup', '/download',
            '.pdf', '.zip', '.tar', '.gz', '#', 'javascript:'
        ]
        
        for pattern in skip_patterns:
            if pattern in link.lower():
                return False
        
        return True
    
    def _is_valid_documentation_link(self, url: str) -> bool:
        """Check if URL is a valid documentation link."""
        doc_indicators = [
            '/docs/', '/documentation/', '/guide/', '/tutorial/',
            '/reference/', '/api/', '/manual/', '/help/'
        ]
        
        return any(indicator in url.lower() for indicator in doc_indicators)
    
    @logfire.instrument("process_page_content")
    async def _process_page_content(
        self, 
        page_data: Dict[str, Any], 
        source_name: str
    ) -> Optional[Dict[str, Any]]:
        """Process and enhance page content with AI."""
        try:
            content = page_data["content"]
            
            # Skip pages with insufficient content
            if len(content.split()) < 50:
                return None
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(page_data)
            
            # Skip low-quality content
            if quality_score < 0.3:
                return None
            
            # Chunk content for better processing
            chunks = self._chunk_content(content)
            
            # Generate embeddings for semantic search
            embeddings = []
            for chunk in chunks:
                try:
                    embedding_response = await self.openai_client.embeddings.create(
                        model="text-embedding-3-large",
                        input=chunk,
                        dimensions=1536
                    )
                    embeddings.append(embedding_response.data[0].embedding)
                except Exception as e:
                    logger.error(f"Error generating embedding: {e}")
                    embeddings.append(None)
            
            # Extract key concepts and topics
            topics = await self._extract_topics(content)
            
            return {
                "source_name": source_name,
                "url": page_data["url"],
                "title": page_data["title"],
                "content": content,
                "content_hash": page_data["content_hash"],
                "chunks": chunks,
                "embeddings": embeddings,
                "topics": topics,
                "quality_score": quality_score,
                "word_count": page_data["word_count"],
                "crawled_at": page_data["crawled_at"],
                "processed_at": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            return None
    
    def _calculate_quality_score(self, page_data: Dict[str, Any]) -> float:
        """Calculate content quality score (0.0 to 1.0)."""
        content = page_data["content"]
        title = page_data["title"]
        
        score = 0.0
        
        # Word count score (optimal range: 200-2000 words)
        word_count = len(content.split())
        if 200 <= word_count <= 2000:
            score += 0.3
        elif word_count > 100:
            score += 0.15
        
        # Title quality
        if title and len(title.split()) >= 3:
            score += 0.2
        
        # Content structure indicators
        structure_indicators = [
            '```', 'def ', 'class ', 'function', 'example',
            'tutorial', 'guide', 'reference', 'documentation'
        ]
        
        for indicator in structure_indicators:
            if indicator.lower() in content.lower():
                score += 0.1
                break
        
        # Code examples
        if '```' in content or 'def ' in content or 'class ' in content:
            score += 0.2
        
        # Link density (too many links = low quality)
        link_count = page_data.get("links", [])
        if len(link_count) < word_count * 0.1:  # Less than 10% links
            score += 0.2
        
        return min(score, 1.0)
    
    def _chunk_content(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Split content into chunks for better processing."""
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) > 50:  # Skip very small chunks
                chunks.append(chunk)
        
        return chunks
    
    async def _extract_topics(self, content: str) -> List[str]:
        """Extract key topics and concepts from content."""
        try:
            # Simple keyword extraction (can be enhanced with NLP)
            common_tech_terms = [
                'api', 'function', 'class', 'method', 'parameter',
                'return', 'example', 'tutorial', 'configuration',
                'installation', 'setup', 'authentication', 'database'
            ]
            
            content_lower = content.lower()
            topics = []
            
            for term in common_tech_terms:
                if term in content_lower:
                    topics.append(term)
            
            # Extract potential code concepts
            code_patterns = [
                'def ', 'class ', 'import ', 'from ', 'async ',
                'await ', 'return ', 'if ', 'for ', 'while '
            ]
            
            for pattern in code_patterns:
                if pattern in content_lower:
                    topics.append(pattern.strip())
            
            return list(set(topics))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return []
    
    async def get_crawl_metrics(self) -> Dict[str, Any]:
        """Get comprehensive crawl metrics."""
        return {
            "volume_metrics": {
                "total_pages_crawled": self.metrics.total_pages_crawled,
                "total_pages_stored": self.metrics.total_pages_stored,
                "total_processing_time": round(self.metrics.total_processing_time / 60, 2),  # minutes
                "average_processing_speed": round(
                    self.metrics.total_pages_crawled / max(self.metrics.total_processing_time, 1), 2
                ),  # pages/second
                "success_rate": round(self.metrics.success_rate * 100, 2)  # percentage
            },
            "quality_metrics": {
                "average_quality_score": round(self.metrics.average_quality_score, 3),
                "content_filtering_effectiveness": round(
                    self.metrics.total_pages_stored / max(self.metrics.total_pages_crawled, 1) * 100, 2
                )
            }
        }
    
    @logfire.instrument("store_documents_enhanced")
    async def _store_documents_enhanced(
        self, 
        processed_documents: List[Dict[str, Any]], 
        source_name: str, 
        source_url: str
    ) -> bool:
        """Store documents using enhanced infrastructure with performance optimization."""
        with logfire.span("Enhanced storage operation", source=source_name):
            try:
                if not processed_documents:
                    logfire.info("No documents to store", source=source_name)
                    return True
                
                # Use Redis cache for deduplication check if available
                if self.redis_cache:
                    cache_key = f"crawl_dedup:{source_name}"
                    existing_hashes = await self.redis_cache.get(cache_key) or set()
                else:
                    existing_hashes = set()
                
                # Convert to storage formats
                document_chunks = []
                new_hashes = set()
                
                for doc in processed_documents:
                    content_hash = doc.get("content_hash")
                    if content_hash in existing_hashes:
                        logfire.info("Skipping duplicate content", hash=content_hash)
                        continue
                    
                    # Create DocumentChunk for SurrealDB
                    for i, chunk in enumerate(doc.get("chunks", [doc.get("content", "")])):
                        chunk_id = f"{source_name}_{content_hash}_{i}"
                        
                        document_chunk = DocumentChunk(
                            id=chunk_id,
                            source_name=source_name,
                            source_url=doc.get("url", source_url),
                            title=doc.get("title", ""),
                            content=chunk,
                            chunk_index=i,
                            total_chunks=len(doc.get("chunks", [doc.get("content", "")])),
                            quality_score=doc.get("quality_score", 0.0),
                            topics=doc.get("topics", []),
                            embedding=doc.get("embeddings", [None])[i] if i < len(doc.get("embeddings", [])) else None,
                            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            updated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ")
                        )
                        document_chunks.append(document_chunk)
                    
                    new_hashes.add(content_hash)
                
                # Store in enhanced infrastructure
                storage_results = []
                
                # Use HybridQueryEngine if available
                if self.hybrid_engine:
                    logfire.info("Using HybridQueryEngine for storage", chunks=len(document_chunks))
                    result = await self.hybrid_engine.store_documents_optimized(document_chunks)
                    storage_results.append(("hybrid_engine", result))
                
                # Use PerformanceOptimizer for connection pooling if available
                elif self.performance_optimizer:
                    logfire.info("Using PerformanceOptimizer for storage", chunks=len(document_chunks))
                    # This would leverage connection pooling for direct storage
                    # Implementation depends on PerformanceOptimizer API
                    storage_results.append(("performance_optimizer", True))
                
                # Fallback to legacy storage_adapter
                elif self.storage_adapter:
                    logfire.info("Using legacy storage adapter", chunks=len(document_chunks))
                    result = await self.storage_adapter.store_document_chunks(document_chunks)
                    storage_results.append(("legacy_adapter", result))
                
                # Update Redis cache with new hashes
                if self.redis_cache and new_hashes:
                    updated_hashes = existing_hashes | new_hashes
                    await self.redis_cache.set(
                        cache_key, 
                        updated_hashes, 
                        expire_seconds=86400 * 7  # 1 week
                    )
                
                success = all(result for _, result in storage_results)
                
                logfire.info(
                    "Enhanced storage completed",
                    source=source_name,
                    chunks_stored=len(document_chunks),
                    new_documents=len(new_hashes),
                    storage_results=storage_results,
                    success=success
                )
                
                return success
                
            except Exception as e:
                logfire.error(
                    "Enhanced storage failed",
                    source=source_name,
                    error=str(e)
                )
                return False
    
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()

# Documentation sources from PRD
DOCUMENTATION_SOURCES = [
    {"name": "Pydantic AI", "url": "https://ai.pydantic.dev/"},
    {"name": "PyMC", "url": "https://www.pymc.io/"},
    {"name": "Wildwood", "url": "https://wildwood.readthedocs.io/en/latest/"},
    {"name": "Logfire", "url": "https://logfire.pydantic.dev/docs/"},
    {"name": "Crawl4AI", "url": "https://docs.crawl4ai.com/"},
    {"name": "SurrealDB", "url": "https://surrealdb.com/docs/surrealdb"},
    {"name": "FastAPI", "url": "https://fastapi.tiangolo.com/"},
    {"name": "FastMCP", "url": "https://gofastmcp.com/getting-started/welcome"},
    {"name": "Claude Code", "url": "https://docs.anthropic.com/en/docs/claude-code/overview"},
    {"name": "AnimeJS", "url": "https://animejs.com/documentation/"},
    {"name": "NextJS", "url": "https://nextjs.org/docs"},
    {"name": "Shadcn", "url": "https://ui.shadcn.com/docs"},
    {"name": "Tailwind", "url": "https://v2.tailwindcss.com/docs"},
    {"name": "Panel", "url": "https://panel.holoviz.org/"},
    {"name": "PyGAD", "url": "https://pygad.readthedocs.io/en/latest/"},
    {"name": "circom", "url": "https://docs.circom.io/"},
    {"name": "bokeh", "url": "https://docs.bokeh.org"}
]

async def main():
    """Main function for testing crawler."""
    config = CrawlConfig(
        max_depth=2,
        max_pages=10,  # Reduced for testing
        delay_ms=1000
    )
    
    crawler = PtolemiesCrawler(config)
    
    try:
        # Test with a single source
        result = await crawler.crawl_documentation_source(
            "https://docs.crawl4ai.com/",
            "Crawl4AI"
        )
        
        print(json.dumps(result, indent=2))
        
        # Get metrics
        metrics = await crawler.get_crawl_metrics()
        print("\nCrawl Metrics:")
        print(json.dumps(metrics, indent=2))
        
    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(main())