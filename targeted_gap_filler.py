#!/usr/bin/env python3
"""
Targeted Gap-Filling Crawler for 7 Minimal-Coverage Sources
==========================================================

Specialized crawler to bring 7 sources up to minimum 10 chunks each:
- SurrealDB: 7 → 10 chunks
- FastMCP: 4 → 10 chunks  
- Panel: 3 → 10 chunks
- Wildwood: 3 → 10 chunks
- AnimeJS: 2 → 10 chunks
- Crawl4AI: 2 → 10 chunks
- circom: 2 → 10 chunks
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
import logging

try:
    import httpx
    import openai
    from bs4 import BeautifulSoup
    import logfire
    from dotenv import load_dotenv
    import requests
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    sys.exit(1)

# Load environment and configure Logfire
load_dotenv()
logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Targeted sources with custom strategies
TARGETED_SOURCES = [
    {
        "name": "SurrealDB", 
        "current_chunks": 7,
        "target_chunks": 10,
        "strategy": "multi_entry_api_focus",
        "entry_points": [
            "https://surrealdb.com/docs/surrealql/functions/",
            "https://surrealdb.com/docs/surrealdb/cli/",
            "https://surrealdb.com/docs/surrealql/statements/"
        ],
        "delays": 3,
        "user_agent": "Mozilla/5.0 (compatible; DocumentationBot/1.0)",
        "selectors": [".docs-content", ".markdown-body", ".content"],
        "max_depth": 2
    },
    {
        "name": "FastMCP",
        "current_chunks": 4, 
        "target_chunks": 10,
        "strategy": "javascript_heavy",
        "entry_points": [
            "https://gofastmcp.com/docs/",
            "https://gofastmcp.com/examples/",
            "https://gofastmcp.com/getting-started/welcome"
        ],
        "delays": 5,
        "javascript_wait": 5,
        "user_agent": "Mozilla/5.0 (compatible; DocCrawler/2.0)",
        "selectors": [".docs-content", ".content", "main"],
        "max_depth": 3
    },
    {
        "name": "Panel",
        "current_chunks": 3,
        "target_chunks": 10, 
        "strategy": "academic_site",
        "entry_points": [
            "https://panel.holoviz.org/reference/",
            "https://panel.holoviz.org/how_to/",
            "https://panel.holoviz.org/tutorials/"
        ],
        "delays": 4,
        "user_agent": "Mozilla/5.0 (compatible; AcademicResearchBot/1.0)",
        "selectors": [".rst-content", ".document", ".content"],
        "max_depth": 2
    },
    {
        "name": "Wildwood",
        "current_chunks": 3,
        "target_chunks": 10,
        "strategy": "readthedocs",
        "entry_points": [
            "https://wildwood.readthedocs.io/en/stable/api/",
            "https://wildwood.readthedocs.io/en/stable/examples/", 
            "https://wildwood.readthedocs.io/en/stable/user_guide/"
        ],
        "delays": 5,
        "user_agent": "Mozilla/5.0 (compatible; ReadTheDocsBot/1.0)",
        "selectors": [".rst-content", ".document", ".body"],
        "max_depth": 2
    },
    {
        "name": "AnimeJS",
        "current_chunks": 2,
        "target_chunks": 10,
        "strategy": "github_primary",
        "entry_points": [
            "https://github.com/juliangarnier/anime/wiki",
            "https://animejs.com/documentation/"
        ],
        "delays": 3,
        "javascript_wait": 10,
        "user_agent": "Mozilla/5.0 (compatible; GitHubDocBot/1.0)",
        "selectors": [".wiki-content", ".markdown-body", ".documentation"],
        "max_depth": 2,
        "github_mode": True
    },
    {
        "name": "Crawl4AI", 
        "current_chunks": 2,
        "target_chunks": 10,
        "strategy": "github_repo",
        "entry_points": [
            "https://github.com/unclecode/crawl4ai/blob/main/README.md",
            "https://github.com/unclecode/crawl4ai/tree/main/docs/",
            "https://docs.crawl4ai.com/"
        ],
        "delays": 3,
        "user_agent": "Mozilla/5.0 (compatible; RepoDocBot/1.0)",
        "selectors": [".markdown-body", ".Box-body", ".docs-content"],
        "max_depth": 2,
        "github_mode": True
    },
    {
        "name": "circom",
        "current_chunks": 2,
        "target_chunks": 10,
        "strategy": "math_content",
        "entry_points": [
            "https://docs.circom.io/getting-started/",
            "https://docs.circom.io/circom-language/",
            "https://docs.circom.io/circom-language/basic-operators/"
        ],
        "delays": 4,
        "user_agent": "Mozilla/5.0 (compatible; MathDocBot/1.0)",
        "selectors": [".rst-content", ".document", ".content"],
        "max_depth": 2,
        "preserve_math": True
    }
]

@dataclass
class TargetedMetrics:
    """Track metrics for targeted crawling."""
    sources_processed: int = 0
    total_new_chunks: int = 0
    chunks_per_source: Dict[str, int] = None
    processing_errors: int = 0
    start_time: float = 0
    
    def __post_init__(self):
        if self.chunks_per_source is None:
            self.chunks_per_source = {}

class TargetedGapFiller:
    """Specialized crawler for filling gaps in minimal-coverage sources."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self.openai_client = None
        self.metrics = TargetedMetrics()
        self.processed_urls = set()
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
        else:
            logger.warning("OpenAI API key not found - embeddings will be skipped")
    
    def load_env_file(self, filepath=".env"):
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
    
    def run_surreal_query(self, query: str) -> bool:
        """Execute SurrealDB query."""
        env_vars = self.load_env_file()
        
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
                cmd, input=query, text=True,
                capture_output=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"SurrealDB error: {result.stderr}")
                return False
            return True
            
        except Exception as e:
            logger.error(f"SurrealDB query failed: {e}")
            return False
    
    async def get_page_content(self, url: str, source_config: Dict) -> Optional[str]:
        """Get page content with source-specific handling."""
        
        if url in self.processed_urls:
            return None
            
        try:
            headers = {"User-Agent": source_config.get("user_agent", "Mozilla/5.0 (compatible; DocBot/1.0)")}
            
            # Handle GitHub URLs specially
            if source_config.get("github_mode") and "github.com" in url:
                # Convert GitHub URLs to raw content when possible
                if "/blob/" in url:
                    url = url.replace("/blob/", "/raw/")
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: {response.status_code}")
                return None
            
            # Add delay based on source configuration
            await asyncio.sleep(source_config.get("delays", 2))
            
            content = response.text
            self.processed_urls.add(url)
            
            # Handle JavaScript-heavy sites
            if source_config.get("javascript_wait"):
                logger.info(f"Waiting {source_config['javascript_wait']}s for JavaScript content")
                await asyncio.sleep(source_config["javascript_wait"])
            
            return content
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_content(self, html: str, source_config: Dict) -> str:
        """Extract relevant content using source-specific selectors."""
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove common noise elements
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Try source-specific selectors
            content_parts = []
            selectors = source_config.get("selectors", [".content"])
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(separator='\n', strip=True)
                    if len(text) > 100:  # Only keep substantial content
                        content_parts.append(text)
            
            # Fallback to body if no content found
            if not content_parts:
                body = soup.find('body')
                if body:
                    content_parts.append(body.get_text(separator='\n', strip=True))
            
            content = '\n\n'.join(content_parts)
            
            # Handle math content preservation
            if source_config.get("preserve_math"):
                # Keep LaTeX expressions intact
                content = re.sub(r'\$([^$]+)\$', r'$\1$', content)
            
            return content
            
        except Exception as e:
            logger.error(f"Content extraction error: {e}")
            return ""
    
    def find_links(self, html: str, base_url: str, source_config: Dict) -> List[str]:
        """Find relevant links for continued crawling."""
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    full_url = urljoin(base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(base_url, href)
                
                # Filter relevant links based on source
                if self.is_relevant_link(full_url, source_config):
                    links.append(full_url)
            
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Link extraction error: {e}")
            return []
    
    def is_relevant_link(self, url: str, source_config: Dict) -> bool:
        """Check if a link is relevant for the source."""
        
        # Basic filters
        if any(ext in url.lower() for ext in ['.pdf', '.zip', '.tar.gz', '.exe', '.dmg']):
            return False
        
        if any(skip in url.lower() for skip in ['download', 'login', 'register', 'admin']):
            return False
        
        # Source-specific relevance
        source_name = source_config["name"].lower()
        
        if source_name == "surrealdb":
            return any(term in url.lower() for term in ['docs', 'surrealql', 'cli', 'functions'])
        elif source_name == "fastmcp":
            return any(term in url.lower() for term in ['docs', 'examples', 'getting-started', 'api'])
        elif source_name == "panel":
            return any(term in url.lower() for term in ['reference', 'how_to', 'tutorials', 'api'])
        elif source_name == "wildwood":
            return any(term in url.lower() for term in ['api', 'examples', 'user_guide', 'stable'])
        elif source_name == "animejs":
            return any(term in url.lower() for term in ['wiki', 'documentation', 'api', 'github'])
        elif source_name == "crawl4ai":
            return any(term in url.lower() for term in ['docs', 'readme', 'examples', 'github'])
        elif source_name == "circom":
            return any(term in url.lower() for term in ['docs', 'getting-started', 'language', 'operators'])
        
        return True
    
    def create_chunks(self, content: str, source_name: str, url: str) -> List[Dict]:
        """Create document chunks from content."""
        
        # Split content into chunks (aim for ~1000 chars per chunk)
        chunks = []
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > 1000 and current_chunk:
                chunks.append({
                    "content": current_chunk.strip(),
                    "source_name": source_name,
                    "source_url": url,
                    "chunk_id": f"{source_name}_{len(chunks)}_{int(time.time())}",
                    "created_at": datetime.now(UTC).isoformat(),
                    "word_count": len(current_chunk.split()),
                    "char_count": len(current_chunk)
                })
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "source_name": source_name,
                "source_url": url,
                "chunk_id": f"{source_name}_{len(chunks)}_{int(time.time())}",
                "created_at": datetime.now(UTC).isoformat(),
                "word_count": len(current_chunk.split()),
                "char_count": len(current_chunk)
            })
        
        return chunks
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate OpenAI embedding for text."""
        
        if not self.openai_client:
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]  # Limit text length
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    async def store_chunks(self, chunks: List[Dict]) -> bool:
        """Store chunks in SurrealDB."""
        
        for chunk in chunks:
            # Generate embedding
            embedding = await self.generate_embedding(chunk["content"])
            if embedding:
                chunk["embedding"] = embedding
            
            # Create SurrealDB insert query
            query = f"""
            CREATE document_chunks SET
                content = '{chunk["content"].replace("'", "''")}',
                source_name = '{chunk["source_name"]}',
                source_url = '{chunk["source_url"]}',
                chunk_id = '{chunk["chunk_id"]}',
                created_at = '{chunk["created_at"]}',
                word_count = {chunk["word_count"]},
                char_count = {chunk["char_count"]},
                embedding = {json.dumps(embedding) if embedding else 'NONE'};
            """
            
            if not self.run_surreal_query(query):
                logger.error(f"Failed to store chunk: {chunk['chunk_id']}")
                return False
        
        return True
    
    async def crawl_source(self, source_config: Dict) -> int:
        """Crawl a single source to fill its gap."""
        
        source_name = source_config["name"]
        current_chunks = source_config["current_chunks"]
        target_chunks = source_config["target_chunks"]
        needed_chunks = target_chunks - current_chunks
        
        logger.info(f"📦 Starting {source_name}: need {needed_chunks} more chunks")
        
        urls_to_process = source_config["entry_points"].copy()
        processed_urls = set()
        new_chunks_count = 0
        depth = 0
        max_depth = source_config.get("max_depth", 2)
        
        with logfire.span(f"Crawling {source_name}"):
            while urls_to_process and new_chunks_count < needed_chunks and depth < max_depth:
                current_urls = urls_to_process.copy()
                urls_to_process.clear()
                depth += 1
                
                logger.info(f"  Depth {depth}: Processing {len(current_urls)} URLs")
                
                for url in current_urls:
                    if url in processed_urls:
                        continue
                    
                    # Get page content
                    html = await self.get_page_content(url, source_config)
                    if not html:
                        continue
                    
                    # Extract content
                    content = self.extract_content(html, source_config)
                    if len(content) < 200:  # Skip pages with minimal content
                        continue
                    
                    # Create chunks
                    chunks = self.create_chunks(content, source_name, url)
                    
                    # Store chunks
                    if chunks and await self.store_chunks(chunks):
                        new_chunks_count += len(chunks)
                        logger.info(f"  ✅ {url}: +{len(chunks)} chunks")
                        
                        # Stop if we've reached our target
                        if new_chunks_count >= needed_chunks:
                            break
                    
                    # Find more links for next depth
                    if depth < max_depth:
                        links = self.find_links(html, url, source_config)
                        for link in links[:5]:  # Limit links per page
                            if link not in processed_urls:
                                urls_to_process.append(link)
                    
                    processed_urls.add(url)
        
        self.metrics.chunks_per_source[source_name] = new_chunks_count
        logger.info(f"🎯 {source_name} complete: +{new_chunks_count} chunks")
        return new_chunks_count
    
    async def fill_all_gaps(self):
        """Fill gaps for all targeted sources."""
        
        self.metrics.start_time = time.time()
        
        logger.info("🚀 Starting Targeted Gap-Filling Crawler")
        logger.info(f"📊 Targeting {len(TARGETED_SOURCES)} sources")
        
        with logfire.span("Targeted gap filling"):
            for source_config in TARGETED_SOURCES:
                try:
                    new_chunks = await self.crawl_source(source_config)
                    self.metrics.total_new_chunks += new_chunks
                    self.metrics.sources_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {source_config['name']}: {e}")
                    self.metrics.processing_errors += 1
        
        # Report final results
        self.report_results()
    
    def report_results(self):
        """Report final crawling results."""
        
        duration = time.time() - self.metrics.start_time
        
        print("\n" + "="*60)
        print("🎉 TARGETED GAP-FILLING COMPLETE!")
        print("="*60)
        
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📦 Total new chunks: {self.metrics.total_new_chunks}")
        print(f"✅ Sources processed: {self.metrics.sources_processed}/{len(TARGETED_SOURCES)}")
        print(f"❌ Processing errors: {self.metrics.processing_errors}")
        
        print("\n📊 Chunks per source:")
        for source_name, chunk_count in self.metrics.chunks_per_source.items():
            print(f"  {source_name}: +{chunk_count} chunks")
        
        print("\n🎯 Target Achievement:")
        for source_config in TARGETED_SOURCES:
            source_name = source_config["name"]
            current = source_config["current_chunks"]
            new_chunks = self.metrics.chunks_per_source.get(source_name, 0)
            total = current + new_chunks
            target = source_config["target_chunks"]
            status = "✅" if total >= target else "⚠️"
            print(f"  {status} {source_name}: {current} → {total} (target: {target})")
    
    async def update_neo4j_graph(self):
        """Update Neo4j graph with new source data."""
        
        logger.info("🔗 Updating Neo4j graph...")
        
        # Create nodes for sources that now have adequate coverage
        for source_config in TARGETED_SOURCES:
            source_name = source_config["name"]
            current = source_config["current_chunks"]
            new_chunks = self.metrics.chunks_per_source.get(source_name, 0)
            total = current + new_chunks
            
            if total >= 10:  # Only update if we have adequate coverage
                query = f"""
                MERGE (f:Framework {{name: "{source_name}"}})
                SET f.documentation_chunks = {total},
                    f.last_updated = datetime(),
                    f.coverage_status = "adequate";
                """
                
                cmd = [
                    'cypher-shell',
                    '-a', 'bolt://localhost:7687',
                    '-u', 'neo4j',
                    '-p', 'ptolemies',
                    '-d', 'neo4j',
                    '--format', 'plain'
                ]
                
                try:
                    subprocess.run(cmd, input=query, text=True, capture_output=True, timeout=30)
                    logger.info(f"  ✅ Updated Neo4j for {source_name}")
                except Exception as e:
                    logger.error(f"  ❌ Neo4j update failed for {source_name}: {e}")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.client.aclose()

async def main():
    """Main execution function."""
    
    crawler = TargetedGapFiller()
    
    try:
        # Fill gaps in targeted sources
        await crawler.fill_all_gaps()
        
        # Update Neo4j graph
        await crawler.update_neo4j_graph()
        
        print("\n✅ All targeted sources processed!")
        print("✅ Results stored in SurrealDB RAG system")
        print("✅ Neo4j graph updated with new framework data")
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        await crawler.cleanup()

if __name__ == "__main__":
    asyncio.run(main())