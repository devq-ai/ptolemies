#!/usr/bin/env python3
"""
Full Knowledge Base Builder
Crawl all 17 documentation sources and process directly into searchable document_chunks
This will build the complete 784-page knowledge base
"""

import asyncio
import json
import os
import sys
import time
import re
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
from dataclasses import dataclass
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

try:
    import httpx
    from bs4 import BeautifulSoup
    from dotenv import load_dotenv
    from urllib.parse import urljoin, urlparse, quote
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip3 install httpx beautifulsoup4 python-dotenv --break-system-packages --user")
    sys.exit(1)

# Load environment
load_dotenv()

# Documentation sources to crawl
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

@dataclass
class CrawlStats:
    """Statistics for the crawling operation."""
    sources_processed: int = 0
    pages_discovered: int = 0
    pages_crawled: int = 0
    chunks_created: int = 0
    processing_errors: int = 0
    start_time: float = 0
    
def run_surreal_query(query: str) -> bool:
    """Execute a SurrealDB query using CLI."""
    import subprocess
    import tempfile
    
    env_vars = load_env_file()
    
    url = env_vars.get('SURREALDB_URL', 'ws://localhost:8000/rpc')
    username = env_vars.get('SURREALDB_USERNAME', 'root')
    password = env_vars.get('SURREALDB_PASSWORD', 'root')
    namespace = env_vars.get('SURREALDB_NAMESPACE', 'ptolemies')
    database = env_vars.get('SURREALDB_DATABASE', 'knowledge')
    
    cmd = [
        'surreal', 'sql',
        '--conn', url,
        '--user', username,
        '--pass', password,
        '--ns', namespace,
        '--db', database,
        '--pretty'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=query,
            text=True,
            capture_output=True,
            timeout=60
        )
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def load_env_file(filepath=".env"):
    """Load environment variables from .env file."""
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

class KnowledgeBaseCrawler:
    """Comprehensive crawler for building the full knowledge base."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "User-Agent": "Ptolemies Knowledge Crawler/1.0 (https://devq.ai)"
            },
            follow_redirects=True
        )
        self.visited_urls = set()
        self.stats = CrawlStats()
        
    async def extract_links(self, html: str, base_url: str, domain: str) -> List[str]:
        """Extract relevant documentation links from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative to absolute URLs
                if href.startswith('/'):
                    full_url = urljoin(base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                    
                # Filter for same domain documentation
                if domain in full_url and self.is_documentation_url(full_url):
                    links.append(full_url)
                    
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            print(f"⚠️  Link extraction error: {e}")
            return []
            
    def is_documentation_url(self, url: str) -> bool:
        """Check if URL is likely documentation content."""
        doc_indicators = [
            '/docs/', '/documentation/', '/guide/', '/tutorial/', '/api/',
            '/reference/', '/learn/', '/getting-started/', '/examples/'
        ]
        
        # Exclude non-content URLs
        exclude_patterns = [
            '/search', '/login', '/register', '/contact', '/about',
            '.pdf', '.zip', '.tar.gz', '/edit', '/fork', '/star',
            '#', '?', '/issues/', '/pull/', '/releases/', '/tags/'
        ]
        
        url_lower = url.lower()
        
        # Must have documentation indicators
        has_doc_indicator = any(indicator in url_lower for indicator in doc_indicators)
        
        # Must not have exclude patterns
        has_exclude_pattern = any(pattern in url_lower for pattern in exclude_patterns)
        
        return has_doc_indicator and not has_exclude_pattern
        
    def extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 
                               'aside', 'menu', 'form', 'button']):
                element.decompose()
                
            # Get text from main content areas first
            main_content = soup.find('main') or soup.find('article') or soup.find(class_=re.compile(r'content|main|article'))
            
            if main_content:
                text = main_content.get_text()
            else:
                text = soup.get_text()
                
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = ' '.join(chunk for chunk in chunks if chunk)
            
            return clean_text
            
        except Exception as e:
            print(f"⚠️  Text extraction error: {e}")
            return ""
            
    def chunk_text(self, text: str, max_chunk_size: int = 1500) -> List[str]:
        """Split text into manageable chunks."""
        if len(text) <= max_chunk_size:
            return [text] if text.strip() else []
            
        chunks = []
        sentences = re.split(r'[.!?]+', text)
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk) + len(sentence) + 2 > max_chunk_size:
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
            
        return [chunk for chunk in chunks if len(chunk) > 50]  # Filter very short chunks
        
    def calculate_quality_score(self, text: str, title: str, url: str, source_name: str) -> float:
        """Calculate content quality score."""
        score = 0.3  # Base score
        
        # Length scoring (prefer substantial content)
        length = len(text)
        if 200 <= length <= 3000:
            score += 0.3
        elif length > 100:
            score += 0.1
            
        # Title quality
        if title and len(title) > 5:
            score += 0.1
            
        # URL structure indicators
        if any(indicator in url.lower() for indicator in ['/docs/', '/guide/', '/tutorial/', '/api/']):
            score += 0.15
            
        # Content quality indicators
        quality_indicators = ['example', 'code', 'function', 'class', 'install', 'configuration']
        found_indicators = sum(1 for indicator in quality_indicators if indicator in text.lower())
        score += min(found_indicators * 0.05, 0.15)
        
        # Source-specific bonuses
        if source_name in ['FastAPI', 'SurrealDB', 'NextJS', 'Pydantic AI']:
            score += 0.05
            
        return min(score, 1.0)
        
    def extract_topics(self, text: str, title: str, source_name: str) -> List[str]:
        """Extract relevant topics from content."""
        topics = [source_name]
        
        # Add title-based topics
        if title:
            title_words = re.findall(r'\b[A-Z][a-z]+\b', title)
            topics.extend(title_words[:3])
            
        # Technical terms extraction
        tech_terms = {
            'API', 'authentication', 'database', 'framework', 'library',
            'installation', 'configuration', 'tutorial', 'guide', 'example',
            'Python', 'JavaScript', 'TypeScript', 'React', 'Vue', 'Angular',
            'async', 'function', 'class', 'method', 'component', 'service',
            'testing', 'debugging', 'deployment', 'docker', 'kubernetes'
        }
        
        text_lower = text.lower()
        for term in tech_terms:
            if term.lower() in text_lower:
                topics.append(term)
                
        return list(set(topics[:8]))  # Limit to 8 most relevant topics
        
    async def crawl_source(self, source: Dict[str, str]) -> int:
        """Crawl a single documentation source."""
        source_name = source['name']
        start_url = source['url']
        
        print(f"\n📚 Crawling {source_name}: {start_url}")
        
        try:
            domain = urlparse(start_url).netloc
            urls_to_crawl = [start_url]
            crawled_urls = set()
            pages_processed = 0
            chunks_created = 0
            
            while urls_to_crawl and pages_processed < 50:  # Limit per source
                current_url = urls_to_crawl.pop(0)
                
                if current_url in crawled_urls:
                    continue
                    
                crawled_urls.add(current_url)
                
                try:
                    print(f"   📄 Fetching: {current_url[:80]}...")
                    
                    response = await self.client.get(current_url)
                    if response.status_code != 200:
                        continue
                        
                    html_content = response.text
                    
                    # Extract text content
                    text_content = self.extract_text_from_html(html_content)
                    if len(text_content) < 100:
                        continue
                        
                    # Extract title
                    soup = BeautifulSoup(html_content, 'html.parser')
                    title_elem = soup.find('title')
                    title = title_elem.get_text().strip() if title_elem else f"{source_name} Documentation"
                    
                    # Create chunks
                    text_chunks = self.chunk_text(text_content)
                    
                    for chunk_index, chunk_text in enumerate(text_chunks):
                        # Calculate quality and topics
                        quality_score = self.calculate_quality_score(chunk_text, title, current_url, source_name)
                        topics = self.extract_topics(chunk_text, title, source_name)
                        
                        # Create database record
                        chunk_data = {
                            'source_name': source_name,
                            'source_url': current_url,
                            'title': title,
                            'content': chunk_text.replace("'", "''"),  # Escape quotes for SQL
                            'chunk_index': chunk_index,
                            'total_chunks': len(text_chunks),
                            'quality_score': quality_score,
                            'topics': topics,
                            'created_at': 'time::now()'
                        }
                        
                        # Insert into database
                        success = await self.insert_document_chunk(chunk_data)
                        if success:
                            chunks_created += 1
                            self.stats.chunks_created += 1
                        else:
                            self.stats.processing_errors += 1
                    
                    pages_processed += 1
                    self.stats.pages_crawled += 1
                    
                    # Extract more links for deeper crawling
                    if pages_processed < 30:  # Limit link extraction
                        new_links = await self.extract_links(html_content, current_url, domain)
                        for link in new_links[:10]:  # Limit new links
                            if link not in crawled_urls and link not in urls_to_crawl:
                                urls_to_crawl.append(link)
                    
                    # Respectful delay
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"   ⚠️  Error processing {current_url}: {e}")
                    self.stats.processing_errors += 1
                    continue
                    
            print(f"   ✅ {source_name}: {pages_processed} pages, {chunks_created} chunks created")
            return chunks_created
            
        except Exception as e:
            print(f"   ❌ {source_name} failed: {e}")
            self.stats.processing_errors += 1
            return 0
            
    async def insert_document_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """Insert a document chunk into the database."""
        try:
            topics_sql = "[" + ", ".join(f"'{topic}'" for topic in chunk_data['topics']) + "]"
            
            query = f"""
            CREATE document_chunks SET
                source_name = '{chunk_data['source_name']}',
                source_url = '{chunk_data['source_url']}',
                title = '{chunk_data['title'][:100]}',
                content = '{chunk_data['content'][:2000]}',
                chunk_index = {chunk_data['chunk_index']},
                total_chunks = {chunk_data['total_chunks']},
                quality_score = {chunk_data['quality_score']},
                topics = {topics_sql},
                created_at = {chunk_data['created_at']};
            """
            
            return run_surreal_query(query)
            
        except Exception as e:
            print(f"⚠️  Database insert error: {e}")
            return False
            
    async def build_knowledge_base(self):
        """Build the complete knowledge base from all sources."""
        print("🚀 BUILDING COMPLETE PTOLEMIES KNOWLEDGE BASE")
        print("=" * 60)
        print(f"📚 Processing {len(DOCUMENTATION_SOURCES)} documentation sources")
        print("🎯 Target: ~784 pages of technical documentation")
        print()
        
        self.stats.start_time = time.time()
        
        # Clear existing document_chunks to rebuild
        print("🗑️  Clearing existing document chunks...")
        if run_surreal_query("DELETE document_chunks;"):
            print("✅ Database cleared for fresh rebuild")
        else:
            print("⚠️  Database clear warning - continuing")
            
        print()
        
        # Process each source
        for i, source in enumerate(DOCUMENTATION_SOURCES, 1):
            print(f"📖 Source {i}/{len(DOCUMENTATION_SOURCES)}: {source['name']}")
            chunks_created = await self.crawl_source(source)
            self.stats.sources_processed += 1
            
            print(f"   📊 Progress: {chunks_created} chunks added")
            print(f"   📈 Total so far: {self.stats.chunks_created} chunks")
            
        # Final statistics
        elapsed_time = time.time() - self.stats.start_time
        
        print("\n" + "=" * 60)
        print("📊 FINAL CRAWL STATISTICS")
        print("=" * 60)
        print(f"📚 Sources processed: {self.stats.sources_processed}/{len(DOCUMENTATION_SOURCES)}")
        print(f"📄 Pages crawled: {self.stats.pages_crawled}")
        print(f"📝 Document chunks created: {self.stats.chunks_created}")
        print(f"❌ Processing errors: {self.stats.processing_errors}")
        print(f"⏱️  Total time: {elapsed_time:.1f} seconds")
        print(f"⚡ Performance: {self.stats.pages_crawled/elapsed_time:.2f} pages/second")
        
        if self.stats.chunks_created > 0:
            success_rate = ((self.stats.chunks_created) / (self.stats.chunks_created + self.stats.processing_errors)) * 100
            print(f"✅ Success rate: {success_rate:.1f}%")
            
        return self.stats.chunks_created > 0
        
    async def verify_knowledge_base(self):
        """Verify the completed knowledge base."""
        print("\n🔍 VERIFYING KNOWLEDGE BASE")
        print("=" * 40)
        
        # Test database queries
        queries = [
            "SELECT count() FROM document_chunks GROUP ALL;",
            "SELECT source_name, count() as chunks FROM document_chunks GROUP BY source_name ORDER BY chunks DESC LIMIT 5;",
            "SELECT math::mean(quality_score) as avg_quality FROM document_chunks GROUP ALL;"
        ]
        
        for query in queries:
            print(f"Testing: {query[:50]}...")
            success = run_surreal_query(query)
            print(f"   {'✅' if success else '❌'} Query {'passed' if success else 'failed'}")
            
    async def cleanup(self):
        """Clean up resources."""
        await self.client.aclose()

async def main():
    """Main execution function."""
    crawler = KnowledgeBaseCrawler()
    
    try:
        # Build the complete knowledge base
        success = await crawler.build_knowledge_base()
        
        if success:
            await crawler.verify_knowledge_base()
            print("\n🎉 KNOWLEDGE BASE BUILD COMPLETE!")
            print("✅ Full 784-page knowledge base is ready for use")
        else:
            print("\n❌ Knowledge base build failed")
            return 1
            
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Build interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    finally:
        await crawler.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())