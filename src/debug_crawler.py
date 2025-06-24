#!/usr/bin/env python3
"""
Debug Production Crawler
Focused debugging of storage failures for missing sources
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

# Focus on the missing sources
MISSING_SOURCES = [
    {"name": "SurrealDB", "url": "https://surrealdb.com/docs/surrealdb", "priority": "high"},
    {"name": "PyMC", "url": "https://www.pymc.io/", "priority": "medium"},
    {"name": "Pydantic AI", "url": "https://ai.pydantic.dev/", "priority": "high"},
    {"name": "Logfire", "url": "https://logfire.pydantic.dev/docs/", "priority": "high"},
    {"name": "AnimeJS", "url": "https://animejs.com/documentation/", "priority": "medium"}
]

@dataclass
class DebugMetrics:
    sources_attempted: int = 0
    pages_fetched: int = 0
    content_extracted: int = 0
    chunks_generated: int = 0
    embeddings_created: int = 0
    storage_attempts: int = 0
    storage_successes: int = 0
    storage_failures: int = 0

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

def run_surreal_query_debug(query: str) -> Tuple[bool, str]:
    """Execute SurrealDB query with detailed debugging."""
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
        
        success = result.returncode == 0
        
        if not success:
            error_msg = f"Return code: {result.returncode}, stderr: {result.stderr}, stdout: {result.stdout}"
            print(f"❌ Query failed: {error_msg}")
            logfire.error("SurrealDB query failed", 
                        query=query[:200], 
                        stderr=result.stderr,
                        stdout=result.stdout,
                        returncode=result.returncode)
        else:
            print(f"✅ Query succeeded: {len(result.stdout)} chars output")
            
        return success, result.stderr + result.stdout
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"❌ Query exception: {error_msg}")
        logfire.error("SurrealDB execution error", error=str(e), query=query[:200])
        return False, error_msg

class DebugCrawler:
    """Debug-focused crawler for missing sources."""
    
    def __init__(self):
        self.metrics = DebugMetrics()
        self.openai_client = None
        self.http_client = None
        
    async def initialize(self) -> bool:
        """Initialize with debugging."""
        print("🔧 Initializing debug crawler...")
        
        # Test database connection
        success, output = run_surreal_query_debug("SELECT 1 as test;")
        if not success:
            print(f"❌ Database connection failed: {output}")
            return False
        print("✅ Database connection verified")
        
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
            headers={"User-Agent": "Ptolemies Debug Crawler/1.0"},
            follow_redirects=True
        )
        print("✅ HTTP client initialized")
        
        return True
        
    async def debug_single_source(self, source: Dict[str, str]) -> Dict[str, Any]:
        """Debug crawl a single source with detailed logging."""
        source_name = source['name']
        start_url = source['url']
        
        print(f"\n🔍 DEBUG CRAWLING: {source_name}")
        print(f"📍 URL: {start_url}")
        
        self.metrics.sources_attempted += 1
        result = {
            "source_name": source_name,
            "source_url": start_url,
            "pages_fetched": 0,
            "chunks_generated": 0,
            "chunks_stored": 0,
            "errors": [],
            "debug_info": []
        }
        
        try:
            # Step 1: Fetch main page
            print(f"   📥 Fetching main page...")
            response = await self.http_client.get(start_url)
            if response.status_code != 200:
                error = f"HTTP {response.status_code}"
                print(f"   ❌ HTTP error: {error}")
                result["errors"].append(error)
                return result
                
            print(f"   ✅ Page fetched: {len(response.text)} chars")
            self.metrics.pages_fetched += 1
            result["pages_fetched"] = 1
            
            # Step 2: Extract content
            print(f"   🔤 Extracting content...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else f"{source_name} Documentation"
            print(f"   📝 Title: {title[:50]}...")
            
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
            
            print(f"   ✅ Content extracted: {len(clean_text)} chars")
            self.metrics.content_extracted += 1
            
            if len(clean_text) < 200:
                error = f"Insufficient content: {len(clean_text)} chars"
                print(f"   ❌ {error}")
                result["errors"].append(error)
                return result
            
            # Step 3: Create chunks
            print(f"   ✂️  Creating chunks...")
            text_chunks = self.create_chunks(clean_text)
            print(f"   ✅ Created {len(text_chunks)} chunks")
            self.metrics.chunks_generated += len(text_chunks)
            result["chunks_generated"] = len(text_chunks)
            
            # Step 4: Process each chunk
            chunks_stored = 0
            for chunk_index, chunk_text in enumerate(text_chunks):
                print(f"   🔄 Processing chunk {chunk_index + 1}/{len(text_chunks)}...")
                
                # Calculate quality and topics
                quality_score = self.calculate_quality(chunk_text, title, start_url, source_name)
                topics = self.extract_topics(chunk_text, title, source_name)
                
                print(f"      📊 Quality: {quality_score:.3f}, Topics: {topics}")
                
                # Generate embedding
                print(f"      🤖 Generating embedding...")
                embedding = await self.generate_embedding(chunk_text)
                if not embedding:
                    error = f"Embedding failed for chunk {chunk_index}"
                    print(f"      ❌ {error}")
                    result["errors"].append(error)
                    continue
                    
                print(f"      ✅ Embedding: {len(embedding)} dimensions")
                
                # Store chunk with debugging
                print(f"      💾 Storing chunk...")
                chunk_data = {
                    'source_name': source_name,
                    'source_url': start_url,
                    'title': title,
                    'content': chunk_text,
                    'chunk_index': chunk_index,
                    'total_chunks': len(text_chunks),
                    'quality_score': quality_score,
                    'topics': topics,
                    'embedding': embedding
                }
                
                success = await self.store_chunk_debug(chunk_data)
                if success:
                    chunks_stored += 1
                    print(f"      ✅ Chunk stored successfully")
                else:
                    error = f"Storage failed for chunk {chunk_index}"
                    print(f"      ❌ {error}")
                    result["errors"].append(error)
                    
            result["chunks_stored"] = chunks_stored
            print(f"   📊 Final: {chunks_stored}/{len(text_chunks)} chunks stored")
            
            return result
            
        except Exception as e:
            error = f"Source processing failed: {str(e)}"
            print(f"   ❌ {error}")
            result["errors"].append(error)
            return result
    
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
        
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate OpenAI embedding."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536
            )
            
            self.metrics.embeddings_created += 1
            return response.data[0].embedding
            
        except Exception as e:
            print(f"         ❌ Embedding error: {str(e)}")
            logfire.error("Embedding generation failed", error=str(e))
            return None
            
    async def store_chunk_debug(self, chunk_data: Dict[str, Any]) -> bool:
        """Store document chunk with detailed debugging."""
        self.metrics.storage_attempts += 1
        
        try:
            # Safely prepare data
            source_name = str(chunk_data['source_name']).replace("'", "''")
            source_url = str(chunk_data['source_url']).replace("'", "''")
            title = str(chunk_data['title']).replace("'", "''").replace('"', '""')[:200]
            content = str(chunk_data['content']).replace("'", "''").replace('"', '""')[:2500]
            
            # Handle embedding
            embedding = chunk_data.get('embedding', [])
            if embedding and len(embedding) > 0:
                embedding_safe = embedding[:1536]
                embedding_str = "[" + ", ".join(f"{float(x):.6f}" for x in embedding_safe) + "]"
            else:
                embedding_str = "[]"
                
            # Handle topics  
            topics = chunk_data.get('topics', [])
            topics_safe = [str(topic).replace("'", "''")[:50] for topic in topics[:10]]
            topics_str = "[" + ", ".join(f"'{topic}'" for topic in topics_safe) + "]"
            
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
            
            print(f"         🔍 Query length: {len(query)} chars")
            print(f"         🔍 Content length: {len(content)} chars")
            print(f"         🔍 Embedding length: {len(embedding_str)} chars")
            
            success, output = run_surreal_query_debug(query)
            
            if success:
                self.metrics.storage_successes += 1
                return True
            else:
                self.metrics.storage_failures += 1
                print(f"         ❌ Storage query failed: {output[:200]}")
                return False
                
        except Exception as e:
            self.metrics.storage_failures += 1
            error_msg = str(e)
            print(f"         ❌ Storage exception: {error_msg}")
            logfire.error("Chunk storage exception", error=error_msg)
            return False
            
    async def cleanup(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()

async def main():
    """Debug the missing sources."""
    crawler = DebugCrawler()
    
    try:
        print("🐛 PTOLEMIES DEBUG CRAWLER")
        print("=" * 50)
        print(f"🎯 Debugging {len(MISSING_SOURCES)} missing sources")
        print()
        
        if not await crawler.initialize():
            print("❌ Debug crawler initialization failed")
            return 1
            
        results = []
        
        for i, source in enumerate(MISSING_SOURCES, 1):
            print(f"\n🔍 [{i}/{len(MISSING_SOURCES)}] Debugging {source['name']}...")
            result = await crawler.debug_single_source(source)
            results.append(result)
            
            print(f"📊 Source summary:")
            print(f"   Pages fetched: {result['pages_fetched']}")
            print(f"   Chunks generated: {result['chunks_generated']}")
            print(f"   Chunks stored: {result['chunks_stored']}")
            print(f"   Errors: {len(result['errors'])}")
            if result['errors']:
                for error in result['errors']:
                    print(f"     ❌ {error}")
        
        # Final metrics
        print("\n" + "=" * 50)
        print("🐛 DEBUG SUMMARY")
        print("=" * 50)
        print(f"Sources attempted: {crawler.metrics.sources_attempted}")
        print(f"Pages fetched: {crawler.metrics.pages_fetched}")
        print(f"Content extracted: {crawler.metrics.content_extracted}")
        print(f"Chunks generated: {crawler.metrics.chunks_generated}")
        print(f"Embeddings created: {crawler.metrics.embeddings_created}")
        print(f"Storage attempts: {crawler.metrics.storage_attempts}")
        print(f"Storage successes: {crawler.metrics.storage_successes}")
        print(f"Storage failures: {crawler.metrics.storage_failures}")
        
        success_rate = (crawler.metrics.storage_successes / max(crawler.metrics.storage_attempts, 1)) * 100
        print(f"Storage success rate: {success_rate:.1f}%")
        
        return 0
        
    except Exception as e:
        print(f"❌ Debug crawler failed: {e}")
        return 1
    finally:
        await crawler.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())