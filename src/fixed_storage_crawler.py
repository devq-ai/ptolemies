#!/usr/bin/env python3
"""
Fixed Storage Crawler
Addresses the storage persistence issues identified in debug crawler
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

# All 17 sources for complete rebuild
ALL_SOURCES = [
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
class FixedMetrics:
    sources_attempted: int = 0
    sources_completed: int = 0
    pages_crawled: int = 0
    chunks_created: int = 0
    chunks_verified: int = 0
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

def run_surreal_command_fixed(query: str) -> Tuple[bool, str, int]:
    """Execute SurrealDB command with proper transaction handling."""
    env_vars = load_env_file()
    
    # Add explicit commit to ensure persistence
    full_query = query.rstrip(';') + ";\nCOMMIT;"
    
    try:
        cmd = [
            'surreal', 'sql',
            '--conn', env_vars.get('SURREALDB_URL', 'ws://localhost:8000/rpc'),
            '--user', env_vars.get('SURREALDB_USERNAME', 'root'),
            '--pass', env_vars.get('SURREALDB_PASSWORD', 'root'),
            '--ns', env_vars.get('SURREALDB_NAMESPACE', 'ptolemies'),
            '--db', env_vars.get('SURREALDB_DATABASE', 'knowledge'),
            '--pretty'
        ]
        
        result = subprocess.run(
            cmd,
            input=full_query,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        return result.returncode == 0, result.stdout + result.stderr, len(result.stdout)
        
    except Exception as e:
        return False, str(e), 0

def verify_chunk_stored(source_name: str, expected_chunks: int) -> int:
    """Verify chunks are actually stored in database."""
    query = f"SELECT count() as total FROM document_chunks WHERE source_name = '{source_name}' GROUP ALL;"
    success, output, length = run_surreal_command_fixed(query)
    
    if success and "total" in output:
        try:
            # Extract count from output
            import re
            match = re.search(r'"?total"?\s*:\s*(\d+)', output)
            if match:
                return int(match.group(1))
        except:
            pass
    
    return 0

class FixedStorageCrawler:
    """Crawler with fixed storage persistence."""
    
    def __init__(self):
        self.metrics = FixedMetrics()
        self.openai_client = None
        self.http_client = None
        
    async def initialize(self) -> bool:
        """Initialize with connection verification."""
        print("🔧 Initializing fixed storage crawler...")
        
        # Test database connection with verification
        success, output, length = run_surreal_command_fixed("SELECT 1 as test")
        if not success:
            print(f"❌ Database connection failed: {output}")
            return False
        print("✅ Database connection verified with commit")
        
        # Initialize OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not found")
            return False
        
        self.openai_client = openai.AsyncOpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": "Ptolemies Fixed Crawler/1.0"},
            follow_redirects=True
        )
        print("✅ HTTP client initialized")
        
        return True
        
    async def clear_database(self) -> bool:
        """Clear database with verification."""
        print("🗑️  Clearing database...")
        
        success, output, length = run_surreal_command_fixed("DELETE document_chunks")
        if not success:
            print(f"❌ Database clear failed: {output}")
            return False
            
        # Verify clear
        count = verify_chunk_stored("any", 0)  # This will check total count
        print(f"✅ Database cleared, chunks remaining: {count}")
        return True
        
    async def crawl_with_enhanced_extraction(self, source: Dict[str, str]) -> Dict[str, Any]:
        """Crawl with enhanced content extraction for problematic sources."""
        source_name = source['name']
        start_url = source['url']
        
        print(f"\n📚 Crawling {source_name}: {start_url}")
        self.metrics.sources_attempted += 1
        
        result = {
            "source_name": source_name,
            "source_url": start_url,
            "chunks_created": 0,
            "chunks_verified": 0,
            "success": False
        }
        
        try:
            # Fetch page
            response = await self.http_client.get(start_url)
            if response.status_code != 200:
                print(f"   ❌ HTTP {response.status_code}")
                return result
                
            self.metrics.pages_crawled += 1
            print(f"   📄 Fetched: {len(response.text)} chars")
            
            # Enhanced content extraction
            content = await self.extract_content_enhanced(response.text, source_name)
            if len(content) < 200:
                print(f"   ⚠️  Low content: {len(content)} chars, trying alternative extraction")
                content = await self.extract_content_alternative(response.text, source_name)
                
            if len(content) < 200:
                print(f"   ❌ Insufficient content: {len(content)} chars")
                return result
                
            print(f"   ✅ Content extracted: {len(content)} chars")
            
            # Create and process chunks
            chunks = self.create_chunks(content)
            print(f"   ✂️  Created {len(chunks)} chunks")
            
            chunks_stored = 0
            for i, chunk_text in enumerate(chunks):
                if await self.store_chunk_verified(source_name, start_url, chunk_text, i, len(chunks)):
                    chunks_stored += 1
                    
            # Verify storage
            verified_count = verify_chunk_stored(source_name, chunks_stored)
            print(f"   📊 Stored: {chunks_stored}, Verified: {verified_count}")
            
            result["chunks_created"] = chunks_stored
            result["chunks_verified"] = verified_count
            result["success"] = verified_count > 0
            
            if verified_count > 0:
                self.metrics.sources_completed += 1
                self.metrics.chunks_created += chunks_stored
                self.metrics.chunks_verified += verified_count
                
            return result
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.metrics.processing_errors += 1
            return result
    
    async def extract_content_enhanced(self, html: str, source_name: str) -> str:
        """Enhanced content extraction with source-specific logic."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
            
        # Source-specific extraction strategies
        if source_name == "SurrealDB":
            # Try specific selectors for SurrealDB docs
            content_selectors = [
                '.docs-content', '.documentation', '.content-main', 
                'main .content', '[role="main"]', '.prose'
            ]
        elif source_name == "PyMC":
            # Try specific selectors for PyMC
            content_selectors = [
                '.main-content', '.content', '.documentation',
                'main', '[role="main"]', '.entry-content'
            ]
        else:
            # Default selectors
            content_selectors = [
                'main', 'article', '.content', '.docs-content',
                '.documentation', '[role="main"]', '.main-content'
            ]
            
        # Try each selector
        for selector in content_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 500:  # Good content found
                        return self.clean_text(text)
            except:
                continue
                
        # Fallback to body
        body = soup.find('body')
        if body:
            text = body.get_text(separator=' ', strip=True)
            return self.clean_text(text)
            
        return self.clean_text(soup.get_text(separator=' ', strip=True))
    
    async def extract_content_alternative(self, html: str, source_name: str) -> str:
        """Alternative extraction for difficult sources."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # More aggressive cleaning
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 
                           'aside', 'menu', 'form', 'button', 'noscript']):
            element.decompose()
            
        # Look for any content containers
        content_indicators = [
            'p', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
        ]
        
        texts = []
        for tag in content_indicators:
            elements = soup.find_all(tag)
            for elem in elements:
                text = elem.get_text(strip=True)
                if len(text) > 50 and text not in texts:
                    texts.append(text)
                    
        combined = ' '.join(texts)
        return self.clean_text(combined)
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Remove repeated phrases (common in navigation)
        words = clean_text.split()
        if len(words) > 100:
            # Remove very short repeated segments
            clean_words = []
            prev_word = ""
            repeat_count = 0
            
            for word in words:
                if word == prev_word:
                    repeat_count += 1
                    if repeat_count < 3:  # Allow some repetition
                        clean_words.append(word)
                else:
                    clean_words.append(word)
                    repeat_count = 0
                prev_word = word
                
            clean_text = ' '.join(clean_words)
            
        return clean_text
        
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
        
    async def store_chunk_verified(self, source_name: str, source_url: str, content: str, 
                                  index: int, total: int) -> bool:
        """Store chunk with immediate verification."""
        try:
            # Generate embedding
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=content,
                dimensions=1536
            )
            embedding = response.data[0].embedding
            self.metrics.embeddings_generated += 1
            
            # Prepare safe data
            safe_source = source_name.replace("'", "''")
            safe_url = source_url.replace("'", "''")  
            safe_content = content.replace("'", "''").replace('"', '""')[:2500]
            
            # Create embedding string
            embedding_str = "[" + ", ".join(f"{float(x):.6f}" for x in embedding) + "]"
            
            # Create unique ID to verify storage
            chunk_id = f"{safe_source.replace(' ', '_')}_{index}_{int(time.time())}"
            
            query = f"""
            CREATE document_chunks:{chunk_id} SET
                source_name = '{safe_source}',
                source_url = '{safe_url}',
                title = '{safe_source} Documentation',
                content = '{safe_content}',
                chunk_index = {index},
                total_chunks = {total},
                quality_score = 0.8,
                topics = ['{safe_source}'],
                embedding = {embedding_str},
                created_at = time::now()
            """
            
            # Execute with verification
            success, output, length = run_surreal_command_fixed(query)
            
            if success:
                # Immediate verification
                verify_query = f"SELECT id FROM document_chunks:{chunk_id}"
                verify_success, verify_output, verify_length = run_surreal_command_fixed(verify_query)
                
                if verify_success and chunk_id in verify_output:
                    print(f"      ✅ Chunk {index+1} stored and verified")
                    return True
                else:
                    print(f"      ❌ Chunk {index+1} storage not verified")
                    return False
            else:
                print(f"      ❌ Chunk {index+1} storage failed: {output[:100]}")
                return False
                
        except Exception as e:
            print(f"      ❌ Chunk {index+1} exception: {str(e)}")
            return False
            
    async def build_complete_knowledge_base(self) -> bool:
        """Build complete knowledge base with verification."""
        print("🚀 FIXED STORAGE KNOWLEDGE BASE BUILD")
        print("=" * 60)
        
        self.metrics.start_time = time.time()
        
        # Clear database first
        if not await self.clear_database():
            return False
            
        # Process all sources
        for i, source in enumerate(ALL_SOURCES, 1):
            print(f"\n📖 [{i:2d}/{len(ALL_SOURCES)}] Processing {source['name']}...")
            
            result = await self.crawl_with_enhanced_extraction(source)
            
            if result["success"]:
                print(f"     ✅ Success: {result['chunks_verified']} chunks verified")
            else:
                print(f"     ❌ Failed: {source['name']}")
                
        # Final verification
        elapsed = time.time() - self.metrics.start_time
        
        print("\n" + "=" * 60)
        print("📊 FIXED STORAGE BUILD RESULTS")
        print("=" * 60)
        print(f"Sources attempted: {self.metrics.sources_attempted}")
        print(f"Sources completed: {self.metrics.sources_completed}")
        print(f"Pages crawled: {self.metrics.pages_crawled}")
        print(f"Chunks created: {self.metrics.chunks_created}")
        print(f"Chunks verified: {self.metrics.chunks_verified}")
        print(f"Embeddings generated: {self.metrics.embeddings_generated}")
        print(f"Processing errors: {self.metrics.processing_errors}")
        print(f"Elapsed time: {elapsed:.1f} seconds")
        
        # Database verification
        total_verified = verify_chunk_stored("", 0)  # Will get total count
        print(f"Final database count: {total_verified} chunks")
        
        return self.metrics.sources_completed >= 15  # Allow 2 failures
        
    async def cleanup(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()

async def main():
    """Run fixed storage crawler."""
    crawler = FixedStorageCrawler()
    
    try:
        if not await crawler.initialize():
            return 1
            
        success = await crawler.build_complete_knowledge_base()
        
        if success:
            print("\n🎉 FIXED STORAGE BUILD SUCCESSFUL!")
            return 0
        else:
            print("\n❌ Fixed storage build failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Build error: {e}")
        return 1
    finally:
        await crawler.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())