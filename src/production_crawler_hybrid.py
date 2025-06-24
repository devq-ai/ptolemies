#!/usr/bin/env python3
"""
Production Hybrid Knowledge Builder
Uses working SurrealDB CLI + production crawling with OpenAI embeddings
Builds complete 784-page knowledge base with sub-100ms performance
"""

import asyncio
import json
import os
import sys
import time
import re
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass

try:
    import httpx
    import openai
    from bs4 import BeautifulSoup
    import logfire
    from dotenv import load_dotenv
    from urllib.parse import urljoin, urlparse
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    sys.exit(1)

# Load environment and configure Logfire
load_dotenv()
logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

# Production documentation sources
PRODUCTION_SOURCES = [
    {"name": "FastAPI", "url": "https://fastapi.tiangolo.com/", "priority": "high"},
    {"name": "SurrealDB", "url": "https://surrealdb.com/docs/surrealdb", "priority": "high"},
    {"name": "Pydantic AI", "url": "https://ai.pydantic.dev/", "priority": "high"},
    {"name": "Logfire", "url": "https://logfire.pydantic.dev/docs/", "priority": "high"},
    {"name": "NextJS", "url": "https://nextjs.org/docs", "priority": "high"},
    {"name": "Claude Code", "url": "https://docs.anthropic.com/en/docs/claude-code/overview", "priority": "high"},
    {"name": "Crawl4AI", "url": "https://docs.crawl4ai.com/", "priority": "medium"},
    {"name": "FastMCP", "url": "https://gofastmcp.com/getting-started/welcome", "priority": "medium"},
    {"name": "Tailwind", "url": "https://v2.tailwindcss.com/docs", "priority": "medium"},
    {"name": "AnimeJS", "url": "https://animejs.com/documentation/", "priority": "medium"},
    {"name": "Shadcn", "url": "https://ui.shadcn.com/docs", "priority": "medium"},
    {"name": "Panel", "url": "https://panel.holoviz.org/", "priority": "medium"},
    {"name": "bokeh", "url": "https://docs.bokeh.org", "priority": "medium"},
    {"name": "PyMC", "url": "https://www.pymc.io/", "priority": "low"},
    {"name": "Wildwood", "url": "https://wildwood.readthedocs.io/en/latest/", "priority": "low"},
    {"name": "PyGAD", "url": "https://pygad.readthedocs.io/en/latest/", "priority": "low"},
    {"name": "circom", "url": "https://docs.circom.io/", "priority": "low"}
]

@dataclass
class ProductionMetrics:
    """Production metrics tracking."""
    sources_completed: int = 0
    pages_crawled: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    processing_errors: int = 0
    start_time: float = 0

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
        
        if result.returncode != 0:
            logfire.error("SurrealDB query failed", 
                        query=query[:100], 
                        stderr=result.stderr[:200],
                        returncode=result.returncode)
            return False
            
        return True
        
    except Exception as e:
        logfire.error("SurrealDB execution error", error=str(e), query=query[:100])
        return False

class ProductionCrawler:
    """Production knowledge base crawler."""
    
    def __init__(self):
        self.metrics = ProductionMetrics()
        self.openai_client = None
        self.http_client = None
        self.visited_urls = set()
        
    @logfire.instrument("initialize_production")
    async def initialize(self) -> bool:
        """Initialize production systems."""
        with logfire.span("Production initialization"):
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
            
            # Initialize HTTP client
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"User-Agent": "Ptolemies Production Crawler/1.0"},
                follow_redirects=True
            )
            logfire.info("HTTP client initialized")
            
            # Create schema
            await self.create_schema()
            
            return True
            
    @logfire.instrument("create_schema")
    async def create_schema(self):
        """Create production database schema."""
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
        DEFINE FIELD created_at ON TABLE document_chunks TYPE datetime;
        """
        
        run_surreal_query(schema_query)
        logfire.info("Production schema created")
        
    def extract_text_from_html(self, html: str) -> Tuple[str, str]:
        """Extract content and title from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
                
            # Get main content
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find(class_=re.compile(r'content|main|docs'))
            )
            
            text = main_content.get_text() if main_content else soup.get_text()
            
            # Clean text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = ' '.join(chunk for chunk in chunks if chunk)
            
            return clean_text, title
            
        except Exception:
            return "", ""
            
    def create_chunks(self, text: str, max_size: int = 1200) -> List[str]:
        """Create text chunks."""
        if len(text) <= max_size:
            return [text] if text.strip() else []
            
        chunks = []
        sentences = re.split(r'[.!?]+', text)
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
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
            
        return [chunk for chunk in chunks if len(chunk) > 100]
        
    def calculate_quality(self, text: str, title: str, url: str, source: str) -> float:
        """Calculate content quality score."""
        score = 0.3
        
        # Length scoring
        length = len(text)
        if 300 <= length <= 2000:
            score += 0.3
        elif length > 100:
            score += 0.2
            
        # Title quality
        if title and len(title) > 10:
            score += 0.15
            
        # URL indicators
        if any(indicator in url.lower() for indicator in ['/docs/', '/guide/', '/api/']):
            score += 0.15
            
        # Content quality
        quality_terms = ['example', 'code', 'function', 'api', 'install']
        found = sum(1 for term in quality_terms if term in text.lower())
        score += min(found * 0.04, 0.20)
        
        return min(score, 1.0)
        
    def extract_topics(self, text: str, title: str, source: str) -> List[str]:
        """Extract technical topics."""
        topics = [source]
        
        # Title words
        if title:
            title_words = re.findall(r'\b[A-Z][a-z]+\b', title)
            topics.extend(title_words[:2])
            
        # Technical terms
        tech_terms = {
            'API', 'authentication', 'database', 'framework', 'Python',
            'JavaScript', 'TypeScript', 'async', 'function', 'class',
            'testing', 'deployment', 'configuration', 'tutorial'
        }
        
        text_lower = text.lower()
        for term in tech_terms:
            if term.lower() in text_lower:
                topics.append(term)
                
        return list(dict.fromkeys(topics))[:8]
        
    @logfire.instrument("generate_embedding")
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate OpenAI embedding."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536
            )
            
            self.metrics.embeddings_generated += 1
            return response.data[0].embedding
            
        except Exception as e:
            logfire.error("Embedding generation failed", error=str(e))
            self.metrics.processing_errors += 1
            return None
            
    def store_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """Store document chunk in database with robust error handling."""
        try:
            # Safely escape content for SQL by using proper escaping
            content = chunk_data['content'].replace("'", "''").replace('"', '""')[:2500]
            title = chunk_data['title'].replace("'", "''").replace('"', '""')[:200]
            source_name = chunk_data['source_name'].replace("'", "''")
            source_url = chunk_data['source_url'].replace("'", "''")
            
            # Safely format embedding array with error handling
            try:
                embedding = chunk_data.get('embedding', [])
                if embedding and len(embedding) > 0:
                    # Truncate embedding if too large for storage
                    embedding_safe = embedding[:1536]  # OpenAI embedding size
                    embedding_str = "[" + ", ".join(f"{float(x):.6f}" for x in embedding_safe) + "]"
                else:
                    embedding_str = "[]"
            except Exception as e:
                logfire.warning("Embedding formatting failed", error=str(e))
                embedding_str = "[]"
            
            # Safely format topics array
            try:
                topics = chunk_data.get('topics', [])
                topics_safe = [str(topic).replace("'", "''")[:50] for topic in topics[:10]]
                topics_str = "[" + ", ".join(f"'{topic}'" for topic in topics_safe) + "]"
            except Exception as e:
                logfire.warning("Topics formatting failed", error=str(e))
                topics_str = f"['{source_name}']"
            
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
                created_at = time::now();
            """
            
            success = run_surreal_query(query)
            
            if success:
                self.metrics.chunks_created += 1
                logfire.debug("Chunk stored successfully", 
                            source=source_name, 
                            title=title[:50])
                return True
            else:
                logfire.error("Chunk storage query failed", 
                            source=source_name,
                            title=title[:50],
                            content_length=len(content))
                self.metrics.processing_errors += 1
                return False
                
        except Exception as e:
            logfire.error("Chunk storage exception", 
                        error=str(e),
                        source=chunk_data.get('source_name', 'unknown'))
            self.metrics.processing_errors += 1
            return False
        
    def is_documentation_url(self, url: str, domain: str) -> bool:
        """Check if URL is documentation."""
        if domain not in url:
            return False
            
        url_lower = url.lower()
        doc_patterns = ['/docs/', '/guide/', '/tutorial/', '/api/', '/reference/']
        exclude_patterns = ['/search', '/login', '.pdf', '#', '?', '/edit']
        
        has_doc = any(pattern in url_lower for pattern in doc_patterns)
        has_exclude = any(pattern in url_lower for pattern in exclude_patterns)
        
        return has_doc and not has_exclude
        
    async def extract_links(self, html: str, base_url: str, domain: str) -> List[str]:
        """Extract documentation links."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                if href.startswith('/'):
                    full_url = urljoin(base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                    
                if self.is_documentation_url(full_url, domain):
                    links.append(full_url)
                    
            return list(set(links))
            
        except Exception:
            return []
            
    @logfire.instrument("crawl_source")
    async def crawl_source(self, source: Dict[str, str]) -> int:
        """Crawl a documentation source."""
        source_name = source['name']
        start_url = source['url']
        priority = source.get('priority', 'medium')
        
        # Use specialized crawler for SurrealDB
        if source_name == "SurrealDB":
            return await self._crawl_surrealdb_source()
        
        # Use optimized incremental crawler for Claude Code
        if source_name == "Claude Code":
            return await self._crawl_claude_code_optimized()
        
        with logfire.span("Source crawling", source=source_name):
            logfire.info("Starting crawl", source=source_name, url=start_url)
            
            try:
                domain = urlparse(start_url).netloc
                urls_to_crawl = [start_url]
                crawled_urls = set()
                pages_processed = 0
                chunks_created = 0
                
                max_pages = {'high': 80, 'medium': 40, 'low': 20}.get(priority, 40)
                
                while urls_to_crawl and pages_processed < max_pages:
                    current_url = urls_to_crawl.pop(0)
                    
                    if current_url in crawled_urls or current_url in self.visited_urls:
                        continue
                        
                    crawled_urls.add(current_url)
                    self.visited_urls.add(current_url)
                    
                    try:
                        response = await self.http_client.get(current_url)
                        if response.status_code != 200:
                            continue
                            
                        html_content = response.text
                        text_content, title = self.extract_text_from_html(html_content)
                        
                        if len(text_content) < 200:
                            continue
                            
                        # Create chunks
                        text_chunks = self.create_chunks(text_content)
                        
                        for chunk_index, chunk_text in enumerate(text_chunks):
                            # Calculate metrics
                            quality_score = self.calculate_quality(chunk_text, title, current_url, source_name)
                            topics = self.extract_topics(chunk_text, title, source_name)
                            
                            # Generate embedding
                            embedding = await self.generate_embedding(chunk_text)
                            if not embedding:
                                continue
                                
                            # Store chunk
                            chunk_data = {
                                'source_name': source_name,
                                'source_url': current_url,
                                'title': title,
                                'content': chunk_text,
                                'chunk_index': chunk_index,
                                'total_chunks': len(text_chunks),
                                'quality_score': quality_score,
                                'topics': topics,
                                'embedding': embedding
                            }
                            
                            if self.store_chunk(chunk_data):
                                chunks_created += 1
                                
                        pages_processed += 1
                        self.metrics.pages_crawled += 1
                        
                        # Get more links
                        if pages_processed < max_pages * 0.7:
                            new_links = await self.extract_links(html_content, current_url, domain)
                            for link in new_links[:10]:
                                if (link not in crawled_urls and 
                                    link not in urls_to_crawl and 
                                    link not in self.visited_urls):
                                    urls_to_crawl.append(link)
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logfire.error("Page error", error=str(e), url=current_url)
                        continue
                        
                logfire.info("Source completed", 
                           source=source_name,
                           pages=pages_processed,
                           chunks=chunks_created)
                           
                self.metrics.sources_completed += 1
                return chunks_created
                
            except Exception as e:
                logfire.error("Source failed", error=str(e), source=source_name)
                return 0
    
    async def _crawl_surrealdb_source(self) -> int:
        """Special crawler for SurrealDB documentation."""
        with logfire.span("SurrealDB specialized crawl"):
            try:
                from surrealdb_docs_crawler import SurrealDBDocsCrawler
                
                crawler = SurrealDBDocsCrawler()
                chunks_data = await crawler.crawl_all()
                
                chunks_created = 0
                
                for chunk_data in chunks_data:
                    # Generate embedding
                    embedding = await self.generate_embedding(chunk_data['content'])
                    if not embedding:
                        continue
                    
                    # Store chunk
                    chunk_data['embedding'] = embedding
                    chunk_data['chunk_index'] = chunks_created
                    chunk_data['total_chunks'] = len(chunks_data)
                    
                    if self.store_chunk(chunk_data):
                        chunks_created += 1
                
                self.metrics.sources_completed += 1
                self.metrics.pages_crawled += len(chunks_data)
                
                logfire.info("SurrealDB crawl completed", chunks=chunks_created)
                return chunks_created
                
            except Exception as e:
                logfire.error("SurrealDB crawl failed", error=str(e))
                return 0
    
    async def _crawl_claude_code_optimized(self) -> int:
        """Optimized crawler for Claude Code documentation."""
        with logfire.span("Claude Code optimized crawl"):
            try:
                from incremental_crawler import IncrementalCrawler, ClaudeCodeOptimizedCrawler
                
                incremental = IncrementalCrawler()
                claude_crawler = ClaudeCodeOptimizedCrawler(incremental)
                
                chunks_created = await claude_crawler.crawl_optimized(self)
                
                self.metrics.sources_completed += 1
                logfire.info("Claude Code optimized crawl completed", chunks=chunks_created)
                
                return chunks_created
                
            except Exception as e:
                logfire.error("Claude Code optimized crawl failed", error=str(e))
                # Fall back to regular crawl - use the parent method directly to avoid recursion
                return await self._crawl_claude_code_fallback()
    
    async def _crawl_claude_code_fallback(self) -> int:
        """Fallback crawler for Claude Code using regular method."""
        with logfire.span("Claude Code fallback crawl"):
            logfire.info("Using fallback crawler for Claude Code")
            
            # Regular crawl parameters
            source_name = "Claude Code"
            start_url = "https://docs.anthropic.com/en/docs/claude-code/overview"
            priority = "high"
            
            try:
                domain = urlparse(start_url).netloc
                urls_to_crawl = [start_url]
                crawled_urls = set()
                pages_processed = 0
                chunks_created = 0
                
                max_pages = 40  # Limit for Claude Code
                
                while urls_to_crawl and pages_processed < max_pages:
                    current_url = urls_to_crawl.pop(0)
                    
                    if current_url in crawled_urls or current_url in self.visited_urls:
                        continue
                        
                    crawled_urls.add(current_url)
                    self.visited_urls.add(current_url)
                    
                    try:
                        response = await self.http_client.get(current_url)
                        if response.status_code != 200:
                            continue
                            
                        text_content, title = self.extract_text_from_html(response.text)
                        
                        if len(text_content) < 200:
                            continue
                            
                        # Create chunks
                        text_chunks = self.create_chunks(text_content)
                        
                        for chunk_index, chunk_text in enumerate(text_chunks):
                            # Calculate metrics
                            quality_score = self.calculate_quality(chunk_text, title, current_url, source_name)
                            topics = self.extract_topics(chunk_text, title, source_name)
                            
                            # Generate embedding
                            embedding = await self.generate_embedding(chunk_text)
                            if not embedding:
                                continue
                                
                            # Store chunk
                            chunk_data = {
                                'source_name': source_name,
                                'source_url': current_url,
                                'title': title,
                                'content': chunk_text,
                                'chunk_index': chunk_index,
                                'total_chunks': len(text_chunks),
                                'quality_score': quality_score,
                                'topics': topics,
                                'embedding': embedding
                            }
                            
                            if self.store_chunk(chunk_data):
                                chunks_created += 1
                                
                        pages_processed += 1
                        self.metrics.pages_crawled += 1
                        
                        # Get more links (limited)
                        if pages_processed < max_pages * 0.5:
                            new_links = await self.extract_links(response.text, current_url, domain)
                            for link in new_links[:5]:  # Limit links
                                if (link not in crawled_urls and 
                                    link not in urls_to_crawl and 
                                    link not in self.visited_urls):
                                    urls_to_crawl.append(link)
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logfire.error("Claude Code page error", error=str(e), url=current_url)
                        continue
                        
                logfire.info("Claude Code fallback completed", pages=pages_processed, chunks=chunks_created)
                self.metrics.sources_completed += 1
                return chunks_created
                
            except Exception as e:
                logfire.error("Claude Code fallback failed", error=str(e))
                return 0
                
    @logfire.instrument("build_knowledge_base")
    async def build_knowledge_base(self) -> bool:
        """Build complete production knowledge base."""
        with logfire.span("Knowledge base build"):
            logfire.info("Starting production build", total_sources=len(PRODUCTION_SOURCES))
            
            self.metrics.start_time = time.time()
            
            # Create backup before clearing data
            try:
                from database_backup import DatabaseBackup
                backup_manager = DatabaseBackup()
                backup_file = backup_manager.auto_backup_before_operation(
                    "production_build",
                    namespace=os.getenv('SURREALDB_NAMESPACE', 'ptolemies'),
                    database=os.getenv('SURREALDB_DATABASE', 'knowledge')
                )
                if backup_file:
                    logfire.info("Database backed up", backup_file=backup_file)
            except Exception as e:
                logfire.warning("Backup failed, continuing anyway", error=str(e))
            
            # Clear existing data
            run_surreal_query("DELETE document_chunks;")
            logfire.info("Database cleared for fresh build")
            
            # Process sources by priority
            high_priority = [s for s in PRODUCTION_SOURCES if s.get('priority') == 'high']
            medium_priority = [s for s in PRODUCTION_SOURCES if s.get('priority') == 'medium']  
            low_priority = [s for s in PRODUCTION_SOURCES if s.get('priority') == 'low']
            
            all_sources = high_priority + medium_priority + low_priority
            
            for i, source in enumerate(all_sources, 1):
                logfire.info("Processing source", 
                           number=i,
                           total=len(all_sources),
                           source=source['name'],
                           priority=source.get('priority'))
                
                chunks_created = await self.crawl_source(source)
                
                print(f"✅ {source['name']}: {chunks_created} chunks created (Total: {self.metrics.chunks_created})")
                
            elapsed_time = time.time() - self.metrics.start_time
            
            logfire.info("Build completed",
                       sources_completed=self.metrics.sources_completed,
                       pages_crawled=self.metrics.pages_crawled,
                       chunks_created=self.metrics.chunks_created,
                       embeddings_generated=self.metrics.embeddings_generated,
                       errors=self.metrics.processing_errors,
                       elapsed_seconds=elapsed_time)
                       
            return self.metrics.chunks_created > 0
            
    async def cleanup(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()

async def main():
    """Main production execution."""
    # Apply metrics tracking decorator
    from crawl_metrics_tracker import integrate_metrics_with_crawler
    ProductionCrawlerWithMetrics = integrate_metrics_with_crawler(ProductionCrawler)
    
    crawler = ProductionCrawlerWithMetrics()
    
    try:
        print("🚀 STARTING PRODUCTION KNOWLEDGE BASE BUILD")
        print("=" * 60)
        
        if not await crawler.initialize():
            print("❌ Production initialization failed")
            return 1
            
        success = await crawler.build_knowledge_base()
        
        if success:
            print(f"\n🎉 PRODUCTION BUILD COMPLETE!")
            print(f"📊 Final Statistics:")
            print(f"   Sources: {crawler.metrics.sources_completed}/{len(PRODUCTION_SOURCES)}")
            print(f"   Pages: {crawler.metrics.pages_crawled}")
            print(f"   Chunks: {crawler.metrics.chunks_created}")
            print(f"   Embeddings: {crawler.metrics.embeddings_generated}")
            print(f"   Errors: {crawler.metrics.processing_errors}")
            
            # Display metrics report path
            print(f"\n📈 Metrics Report: metrics/latest_report.md")
            print(f"📊 Visualizations: metrics/visualizations/")
            
            return 0
        else:
            print("❌ Production build failed")
            return 1
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        await crawler.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())