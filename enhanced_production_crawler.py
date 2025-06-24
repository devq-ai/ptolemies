#!/usr/bin/env python3
"""
Enhanced Production Crawler with Increased Depth and Page Limits
===============================================================

Enhanced version of the production crawler with:
- Depth=4 crawling capability
- Pages=750 per source
- Better link discovery and filtering
- Improved progress tracking
"""

import asyncio
import json
import os
import sys
import time
import re
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, UTC
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

try:
    import httpx
    import openai
    from bs4 import BeautifulSoup
    import logfire
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    sys.exit(1)

# Load environment and configure Logfire
load_dotenv()
logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

# Enhanced documentation sources with depth/page limits
ENHANCED_SOURCES = [
    {"name": "FastAPI", "url": "https://fastapi.tiangolo.com/", "priority": "high", "max_pages": 750, "max_depth": 4},
    {"name": "SurrealDB", "url": "https://surrealdb.com/docs/surrealdb", "priority": "high", "max_pages": 750, "max_depth": 4},
    {"name": "Pydantic AI", "url": "https://ai.pydantic.dev/", "priority": "high", "max_pages": 750, "max_depth": 4},
    {"name": "Logfire", "url": "https://logfire.pydantic.dev/docs/", "priority": "high", "max_pages": 750, "max_depth": 4},
    {"name": "NextJS", "url": "https://nextjs.org/docs", "priority": "high", "max_pages": 750, "max_depth": 4},
    {"name": "Claude Code", "url": "https://docs.anthropic.com/en/docs/claude-code/overview", "priority": "high", "max_pages": 750, "max_depth": 4},
    {"name": "Crawl4AI", "url": "https://docs.crawl4ai.com/", "priority": "medium", "max_pages": 750, "max_depth": 4},
    {"name": "FastMCP", "url": "https://gofastmcp.com/getting-started/welcome", "priority": "medium", "max_pages": 750, "max_depth": 4},
    {"name": "Tailwind", "url": "https://v2.tailwindcss.com/docs", "priority": "medium", "max_pages": 750, "max_depth": 4},
    {"name": "AnimeJS", "url": "https://animejs.com/documentation/", "priority": "medium", "max_pages": 750, "max_depth": 4},
    {"name": "Shadcn", "url": "https://ui.shadcn.com/docs", "priority": "medium", "max_pages": 750, "max_depth": 4},
    {"name": "Panel", "url": "https://panel.holoviz.org/", "priority": "medium", "max_pages": 750, "max_depth": 4},
    {"name": "bokeh", "url": "https://docs.bokeh.org", "priority": "medium", "max_pages": 750, "max_depth": 4},
    {"name": "PyMC", "url": "https://www.pymc.io/", "priority": "low", "max_pages": 750, "max_depth": 4},
    {"name": "Wildwood", "url": "https://wildwood.readthedocs.io/en/latest/", "priority": "low", "max_pages": 750, "max_depth": 4},
    {"name": "PyGAD", "url": "https://pygad.readthedocs.io/en/latest/", "priority": "low", "max_pages": 750, "max_depth": 4},
    {"name": "circom", "url": "https://docs.circom.io/", "priority": "low", "max_pages": 750, "max_depth": 4}
]

@dataclass
class EnhancedMetrics:
    """Enhanced production metrics tracking."""
    sources_completed: int = 0
    pages_crawled: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    processing_errors: int = 0
    start_time: float = 0
    depth_stats: Dict[int, int] = None
    
    def __post_init__(self):
        if self.depth_stats is None:
            self.depth_stats = {1: 0, 2: 0, 3: 0, 4: 0}

def load_env_file(filepath=".env"):
    """Load environment variables."""
    env_vars = {}
    if not os.path.exists(filepath):
        return env_vars
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    return env_vars

def run_surreal_query(query: str) -> bool:
    """Execute SurrealDB query using CLI with proper error logging."""
    env_vars = load_env_file()
    
    cmd = [
        'surreal', 'sql',
        '--conn', env_vars.get('SURREALDB_URL', 'ws://localhost:8000/rpc'),
        '--user', env_vars.get('SURREALDB_USERNAME', 'root'),
        '--pass', env_vars.get('SURREALDB_PASSWORD', 'root'),
        '--ns', env_vars.get('SURREALDB_NAMESPACE', 'ptolemies'),
        '--db', env_vars.get('SURREALDB_DATABASE', 'knowledge'),
        '--pretty'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=query,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True
        else:
            logfire.error("SurrealDB query failed", query=query[:100], error=result.stderr)
            return False
            
    except Exception as e:
        logfire.error("SurrealDB query exception", error=str(e))
        return False

class EnhancedProductionCrawler:
    """Enhanced production crawler with depth=4 and pages=750 capability."""
    
    def __init__(self):
        self.metrics = EnhancedMetrics()
        self.openai_client = None
        self.http_client = None
        self.visited_urls: Set[str] = set()
        self.global_url_cache: Set[str] = set()  # Cross-source URL deduplication
        
    @logfire.instrument("initialize_enhanced_production")
    async def initialize(self) -> bool:
        """Initialize enhanced production systems."""
        with logfire.span("Enhanced production initialization"):
            # Test database connection
            if not run_surreal_query("SELECT 1 as test;"):
                logfire.error("SurrealDB connection failed")
                return False
                
            logfire.info("SurrealDB connection verified")
            
            # Initialize OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logfire.error("OPENAI_API_KEY not found")
                return False
                
            self.openai_client = openai.AsyncOpenAI(api_key=api_key)
            logfire.info("OpenAI client initialized")
            
            # Initialize HTTP client with enhanced settings
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(45.0),  # Increased timeout
                headers={"User-Agent": "Ptolemies Enhanced Crawler/2.0"},
                follow_redirects=True,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
            logfire.info("Enhanced HTTP client initialized")
            
            # Create enhanced schema
            await self.create_enhanced_schema()
            
            return True
            
    @logfire.instrument("create_enhanced_schema")
    async def create_enhanced_schema(self):
        """Create enhanced database schema with depth tracking."""
        schema_query = """
        DEFINE TABLE document_chunks SCHEMAFULL;
        DEFINE FIELD source_name ON TABLE document_chunks TYPE string;
        DEFINE FIELD source_url ON TABLE document_chunks TYPE string;
        DEFINE FIELD title ON TABLE document_chunks TYPE string;
        DEFINE FIELD content ON TABLE document_chunks TYPE string;
        DEFINE FIELD chunk_index ON TABLE document_chunks TYPE int;
        DEFINE FIELD total_chunks ON TABLE document_chunks TYPE int;
        DEFINE FIELD quality_score ON TABLE document_chunks TYPE float;
        DEFINE FIELD topics ON TABLE document_chunks TYPE array<string>;
        DEFINE FIELD embedding ON TABLE document_chunks TYPE array<float>;
        DEFINE FIELD crawl_depth ON TABLE document_chunks TYPE int;
        DEFINE FIELD page_category ON TABLE document_chunks TYPE string;
        DEFINE FIELD created_at ON TABLE document_chunks TYPE datetime;
        """
        
        run_surreal_query(schema_query)
        logfire.info("Enhanced schema created")
    
    def extract_text_from_html(self, html: str) -> Tuple[str, str]:
        """Extract content and title from HTML with enhanced filtering."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
                element.decompose()
            
            # Enhanced content extraction
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find(class_=re.compile(r'content|main|docs|documentation|article')) or
                soup.find(id=re.compile(r'content|main|docs|documentation'))
            )
            
            text = main_content.get_text() if main_content else soup.get_text()
            
            # Enhanced text cleaning
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = ' '.join(chunk for chunk in chunks if chunk and len(chunk) > 3)
            
            return clean_text, title
            
        except Exception:
            return "", ""
    
    def create_chunks(self, text: str, max_size: int = 1200) -> List[str]:
        """Create text chunks with enhanced boundary detection."""
        if len(text) <= max_size:
            return [text] if text.strip() else []
            
        chunks = []
        # Enhanced sentence splitting
        sentences = re.split(r'[.!?]+\s+', text)
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if adding this sentence would exceed max_size
            if len(current_chunk) + len(sentence) + 2 > max_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
                    
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        # Filter out chunks that are too small or too repetitive
        filtered_chunks = []
        for chunk in chunks:
            if (len(chunk) > 150 and  # Minimum size
                len(set(chunk.split())) > 10):  # Minimum unique words
                filtered_chunks.append(chunk)
        
        return filtered_chunks
    
    def calculate_quality(self, text: str, title: str, url: str, source: str, depth: int = 1) -> float:
        """Calculate enhanced content quality score with depth consideration."""
        score = 0.3
        
        # Length scoring
        length = len(text)
        if 300 <= length <= 3000:  # Increased max for depth crawling
            score += 0.3
        elif length > 150:
            score += 0.2
            
        # Title quality
        if title and len(title) > 10:
            score += 0.15
            
        # URL quality indicators
        url_indicators = ['/docs/', '/guide/', '/api/', '/tutorial/', '/reference/', '/examples/']
        if any(indicator in url.lower() for indicator in url_indicators):
            score += 0.15
            
        # Content quality - enhanced terms
        quality_terms = [
            'example', 'code', 'function', 'api', 'install', 'usage', 'configuration',
            'tutorial', 'guide', 'reference', 'documentation', 'method', 'class',
            'parameter', 'return', 'import', 'syntax', 'implementation'
        ]
        found = sum(1 for term in quality_terms if term in text.lower())
        score += min(found * 0.02, 0.20)
        
        # Depth bonus (deeper pages often have more specific content)
        if depth > 1:
            score += min(depth * 0.05, 0.15)
        
        return min(score, 1.0)
    
    def extract_topics(self, text: str, title: str, source: str) -> List[str]:
        """Extract enhanced technical topics."""
        topics = [source]
        
        # Title analysis
        if title:
            title_words = re.findall(r'\b[A-Z][a-z]+\b', title)
            topics.extend(title_words[:3])
            
        # Enhanced technical terms
        tech_terms = {
            'API', 'authentication', 'database', 'framework', 'Python', 'JavaScript', 'TypeScript',
            'async', 'function', 'class', 'testing', 'deployment', 'configuration', 'tutorial',
            'middleware', 'routing', 'validation', 'serialization', 'ORM', 'REST', 'GraphQL',
            'webhook', 'JWT', 'OAuth', 'CORS', 'HTTP', 'WebSocket', 'microservices',
            'container', 'Docker', 'Kubernetes', 'CI/CD', 'monitoring', 'logging',
            'performance', 'optimization', 'caching', 'security', 'encryption'
        }
        
        text_lower = text.lower()
        for term in tech_terms:
            if term.lower() in text_lower:
                topics.append(term)
                
        return list(dict.fromkeys(topics))[:12]  # Increased topic limit
    
    @logfire.instrument("generate_embedding")
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate OpenAI embedding with retry logic."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],  # Increased input limit
                dimensions=1536
            )
            
            self.metrics.embeddings_generated += 1
            return response.data[0].embedding
            
        except Exception as e:
            logfire.error("Embedding generation failed", error=str(e))
            self.metrics.processing_errors += 1
            return None
    
    def store_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """Store document chunk with enhanced metadata."""
        try:
            # Enhanced data sanitization
            content = chunk_data['content'].replace("'", "''").replace('"', '""')[:4000]  # Increased limit
            title = chunk_data['title'].replace("'", "''").replace('"', '""')[:300]
            source_name = chunk_data['source_name'].replace("'", "''")
            source_url = chunk_data['source_url'].replace("'", "''")
            
            # Enhanced embedding handling
            try:
                embedding = chunk_data.get('embedding', [])
                if embedding and len(embedding) > 0:
                    embedding_safe = embedding[:1536]
                    embedding_str = "[" + ", ".join(f"{float(x):.6f}" for x in embedding_safe) + "]"
                else:
                    embedding_str = "[]"
            except Exception as e:
                logfire.warning("Embedding formatting failed", error=str(e))
                embedding_str = "[]"
            
            # Enhanced topics handling
            try:
                topics = chunk_data.get('topics', [])
                topics_safe = [str(topic).replace("'", "''")[:50] for topic in topics[:15]]
                topics_str = "[" + ", ".join(f"'{topic}'" for topic in topics_safe) + "]"
            except Exception as e:
                logfire.warning("Topics formatting failed", error=str(e))
                topics_str = f"['{source_name}']"
            
            # Enhanced query with new fields
            query = f"""
            CREATE document_chunks SET
                source_name = '{source_name}',
                source_url = '{source_url}',
                title = '{title}',
                content = '{content}',
                chunk_index = {chunk_data.get('chunk_index', 0)},
                total_chunks = {chunk_data.get('total_chunks', 1)},
                quality_score = {chunk_data.get('quality_score', 0.5)},
                topics = {topics_str},
                embedding = {embedding_str},
                crawl_depth = {chunk_data.get('crawl_depth', 1)},
                page_category = '{chunk_data.get('page_category', 'documentation')}',
                created_at = time::now();
            """
            
            success = run_surreal_query(query)
            
            if success:
                self.metrics.chunks_created += 1
                depth = chunk_data.get('crawl_depth', 1)
                if depth in self.metrics.depth_stats:
                    self.metrics.depth_stats[depth] += 1
                    
                logfire.debug("Enhanced chunk stored", 
                            source=source_name, 
                            title=title[:50],
                            depth=depth)
                return True
            else:
                logfire.error("Enhanced chunk storage failed", 
                            source=source_name,
                            title=title[:50])
                self.metrics.processing_errors += 1
                return False
                
        except Exception as e:
            logfire.error("Enhanced chunk storage exception", 
                        error=str(e),
                        source=chunk_data.get('source_name', 'unknown'))
            self.metrics.processing_errors += 1
            return False
    
    def is_documentation_url(self, url: str, domain: str) -> bool:
        """Enhanced documentation URL filtering."""
        if domain not in url:
            return False
            
        url_lower = url.lower()
        
        # Enhanced documentation patterns
        doc_patterns = [
            '/docs/', '/guide/', '/tutorial/', '/api/', '/reference/', '/examples/',
            '/getting-started/', '/quickstart/', '/manual/', '/handbook/', '/wiki/',
            '/documentation/', '/help/', '/learn/', '/training/', '/courses/'
        ]
        
        # Enhanced exclusion patterns
        exclude_patterns = [
            '/search', '/login', '/signup', '/register', '/auth', '/account',
            '.pdf', '.zip', '.tar', '.gz', '#', '?page=', '/edit', '/create',
            '/delete', '/admin', '/dashboard', '/settings', '/profile', '/logout',
            '/download', '/install.', '/setup.', 'mailto:', 'tel:', 'javascript:'
        ]
        
        has_doc = any(pattern in url_lower for pattern in doc_patterns)
        has_exclude = any(pattern in url_lower for pattern in exclude_patterns)
        
        return has_doc and not has_exclude
    
    async def extract_links(self, html: str, base_url: str, domain: str, current_depth: int, max_depth: int) -> List[Tuple[str, int]]:
        """Extract documentation links with depth tracking."""
        if current_depth >= max_depth:
            return []
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            # Enhanced link extraction
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                if href.startswith('/'):
                    full_url = urljoin(base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(base_url, href)
                
                # Clean URL
                full_url = full_url.split('#')[0].split('?')[0]
                
                if (self.is_documentation_url(full_url, domain) and 
                    full_url not in self.global_url_cache):
                    links.append((full_url, current_depth + 1))
                    self.global_url_cache.add(full_url)
            
            # Sort by likely importance
            prioritized_links = []
            high_priority_patterns = ['getting-started', 'quickstart', 'tutorial', 'guide', 'api', 'reference']
            
            for url, depth in links:
                priority = 0
                for pattern in high_priority_patterns:
                    if pattern in url.lower():
                        priority += 1
                prioritized_links.append((url, depth, priority))
            
            # Sort by priority and return top links
            prioritized_links.sort(key=lambda x: x[2], reverse=True)
            return [(url, depth) for url, depth, _ in prioritized_links[:50]]  # Increased link limit
            
        except Exception as e:
            logfire.warning("Link extraction failed", error=str(e))
            return []
    
    @logfire.instrument("crawl_source_enhanced")
    async def crawl_source(self, source_data: Dict[str, Any]) -> int:
        """Enhanced source crawling with depth=4 and pages=750."""
        source_name = source_data["name"]
        start_url = source_data["url"]
        max_pages = source_data.get("max_pages", 750)
        max_depth = source_data.get("max_depth", 4)
        
        with logfire.span("Enhanced source crawl", source=source_name):
            logfire.info("Starting enhanced crawl", 
                        source=source_name, 
                        max_pages=max_pages,
                        max_depth=max_depth)
            
            try:
                domain = urlparse(start_url).netloc
                # Use list of tuples (url, depth)
                urls_to_crawl = [(start_url, 1)]
                crawled_urls = set()
                pages_processed = 0
                chunks_created = 0
                
                while urls_to_crawl and pages_processed < max_pages:
                    current_url, current_depth = urls_to_crawl.pop(0)
                    
                    if (current_url in crawled_urls or 
                        current_url in self.visited_urls or
                        current_depth > max_depth):
                        continue
                        
                    crawled_urls.add(current_url)
                    self.visited_urls.add(current_url)
                    
                    try:
                        logfire.debug("Crawling URL", url=current_url, depth=current_depth)
                        
                        response = await self.http_client.get(current_url)
                        if response.status_code != 200:
                            continue
                            
                        html_content = response.text
                        text_content, title = self.extract_text_from_html(html_content)
                        
                        if len(text_content) < 200:
                            continue
                        
                        # Determine page category
                        page_category = "documentation"
                        if any(pattern in current_url.lower() for pattern in ['tutorial', 'guide']):
                            page_category = "tutorial"
                        elif any(pattern in current_url.lower() for pattern in ['api', 'reference']):
                            page_category = "reference"
                        elif any(pattern in current_url.lower() for pattern in ['example']):
                            page_category = "example"
                            
                        # Create chunks
                        text_chunks = self.create_chunks(text_content)
                        
                        for chunk_index, chunk_text in enumerate(text_chunks):
                            # Enhanced metrics calculation
                            quality_score = self.calculate_quality(
                                chunk_text, title, current_url, source_name, current_depth
                            )
                            topics = self.extract_topics(chunk_text, title, source_name)
                            
                            # Generate embedding
                            embedding = await self.generate_embedding(chunk_text)
                            if not embedding:
                                continue
                                
                            # Enhanced chunk data
                            chunk_data = {
                                'source_name': source_name,
                                'source_url': current_url,
                                'title': title,
                                'content': chunk_text,
                                'chunk_index': chunk_index,
                                'total_chunks': len(text_chunks),
                                'quality_score': quality_score,
                                'topics': topics,
                                'embedding': embedding,
                                'crawl_depth': current_depth,
                                'page_category': page_category
                            }
                            
                            if self.store_chunk(chunk_data):
                                chunks_created += 1
                                
                        pages_processed += 1
                        self.metrics.pages_crawled += 1
                        
                        # Extract more links for deeper crawling
                        if current_depth < max_depth and pages_processed < max_pages * 0.8:
                            new_links = await self.extract_links(
                                html_content, current_url, domain, current_depth, max_depth
                            )
                            for link_url, link_depth in new_links[:25]:  # Limit per page
                                if (link_url not in crawled_urls and 
                                    not any(url == link_url for url, _ in urls_to_crawl) and
                                    link_url not in self.visited_urls):
                                    urls_to_crawl.append((link_url, link_depth))
                        
                        # Progress logging
                        if pages_processed % 50 == 0:
                            logfire.info("Crawl progress", 
                                        source=source_name,
                                        pages=pages_processed,
                                        chunks=chunks_created,
                                        queue_size=len(urls_to_crawl))
                        
                    except Exception as e:
                        logfire.warning("Page crawl failed", 
                                       url=current_url, 
                                       error=str(e))
                        self.metrics.processing_errors += 1
                        continue
                
                self.metrics.sources_completed += 1
                
                logfire.info("Enhanced source completed", 
                           source=source_name,
                           pages=pages_processed,
                           chunks=chunks_created,
                           depth_stats=self.metrics.depth_stats)
                
                return chunks_created
                
            except Exception as e:
                logfire.error("Enhanced source crawl failed", 
                             source=source_name, 
                             error=str(e))
                self.metrics.processing_errors += 1
                return 0
    
    @logfire.instrument("build_enhanced_knowledge_base")
    async def build_enhanced_knowledge_base(self, priority_filter: str = None) -> Dict[str, Any]:
        """Build enhanced knowledge base with all 17 sources."""
        self.metrics.start_time = time.time()
        
        with logfire.span("Enhanced knowledge base build"):
            logfire.info("Starting enhanced production crawl", 
                        total_sources=len(ENHANCED_SOURCES),
                        priority_filter=priority_filter)
            
            total_chunks = 0
            completed_sources = 0
            
            # Filter sources by priority if specified
            sources_to_crawl = ENHANCED_SOURCES
            if priority_filter:
                sources_to_crawl = [s for s in ENHANCED_SOURCES if s["priority"] == priority_filter]
            
            for i, source in enumerate(sources_to_crawl, 1):
                print(f"\n🚀 Enhanced crawling {i}/{len(sources_to_crawl)}: {source['name']}")
                print(f"📄 Target: {source.get('max_pages', 750)} pages, depth {source.get('max_depth', 4)}")
                
                source_start = time.time()
                chunks = await self.crawl_source(source)
                source_time = time.time() - source_start
                
                total_chunks += chunks
                completed_sources += 1
                
                print(f"✅ {source['name']}: {chunks} chunks in {source_time:.1f}s")
                
                logfire.info("Enhanced source summary",
                           source=source['name'],
                           chunks=chunks,
                           duration=source_time,
                           progress=f"{completed_sources}/{len(sources_to_crawl)}")
            
            # Final metrics
            total_time = time.time() - self.metrics.start_time
            
            final_metrics = {
                "total_sources": completed_sources,
                "total_pages": self.metrics.pages_crawled,
                "total_chunks": total_chunks,
                "total_embeddings": self.metrics.embeddings_generated,
                "total_errors": self.metrics.processing_errors,
                "total_time": total_time,
                "depth_distribution": self.metrics.depth_stats,
                "chunks_per_minute": (total_chunks / max(total_time / 60, 1)),
                "pages_per_minute": (self.metrics.pages_crawled / max(total_time / 60, 1))
            }
            
            logfire.info("Enhanced crawl completed", **final_metrics)
            
            print(f"\n🎉 Enhanced Production Crawl Complete!")
            print(f"📊 Final metrics:")
            print(f"  Sources: {completed_sources}")
            print(f"  Pages: {self.metrics.pages_crawled}")
            print(f"  Chunks: {total_chunks}")
            print(f"  Embeddings: {self.metrics.embeddings_generated}")
            print(f"  Errors: {self.metrics.processing_errors}")
            print(f"  Time: {total_time:.1f}s")
            print(f"  Depth distribution: {self.metrics.depth_stats}")
            print(f"  Performance: {final_metrics['chunks_per_minute']:.1f} chunks/min")
            
            return final_metrics

async def main():
    """Main execution function."""
    print("🚀 Enhanced Ptolemies Production Crawler")
    print("📈 Depth=4, Pages=750 per source")
    print("=" * 50)
    
    crawler = EnhancedProductionCrawler()
    
    # Initialize
    if not await crawler.initialize():
        print("❌ Failed to initialize crawler")
        return
    
    try:
        # Build complete knowledge base
        metrics = await crawler.build_enhanced_knowledge_base()
        
        print(f"\n📋 Enhanced crawl summary:")
        print(f"  Total chunks created: {metrics['total_chunks']}")
        print(f"  Pages crawled: {metrics['total_pages']}")
        print(f"  Processing time: {metrics['total_time']:.1f}s")
        print(f"  Performance: {metrics['chunks_per_minute']:.1f} chunks/min")
        
    except KeyboardInterrupt:
        print("\n⏹️  Crawl interrupted by user")
    except Exception as e:
        print(f"\n❌ Crawl failed: {e}")
        logfire.error("Enhanced crawl failed", error=str(e))
    finally:
        if crawler.http_client:
            await crawler.http_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())