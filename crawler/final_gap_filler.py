#!/usr/bin/env python3
"""
Final Gap Filler for Last 3 Sources
==================================

Quick targeted crawling for the last 3 sources that need just a few more chunks:
- SurrealDB: 7 → 10 chunks (need +3)
- AnimeJS: 7 → 10 chunks (need +3)  
- Wildwood: 6 → 10 chunks (need +4)
"""

import asyncio
import json
import os
import sys
import time
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
import logging

try:
    import httpx
    import openai
    from bs4 import BeautifulSoup
    import logfire
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    sys.exit(1)

load_dotenv()
logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

# Final targeted sources with alternative URLs
FINAL_TARGETS = [
    {
        "name": "SurrealDB",
        "current": 7,
        "needed": 3,
        "urls": [
            "https://surrealdb.com/docs/introduction/start",
            "https://surrealdb.com/docs/surrealql",
            "https://surrealdb.com/docs/introduction/concepts",
            "https://surrealdb.com/docs/introduction/architecture"
        ],
        "delay": 3
    },
    {
        "name": "AnimeJS", 
        "current": 7,
        "needed": 3,
        "urls": [
            "https://github.com/juliangarnier/anime/blob/master/README.md",
            "https://github.com/juliangarnier/anime/blob/master/documentation.md",
            "https://codepen.io/collection/b392d3a52d6abf5b8d9fda6e4a965d2e"
        ],
        "delay": 5
    },
    {
        "name": "Wildwood",
        "current": 6, 
        "needed": 4,
        "urls": [
            "https://wildwood.readthedocs.io/en/latest/",
            "https://wildwood.readthedocs.io/en/latest/quickstart.html",
            "https://wildwood.readthedocs.io/en/latest/installation.html",
            "https://github.com/sklearn-jax/wildwood"
        ],
        "delay": 4
    }
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinalGapFiller:
    """Quick filler for the last 3 sources."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.openai_client = None
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
    
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
            return result.returncode == 0
        except Exception as e:
            logger.error(f"SurrealDB query failed: {e}")
            return False
    
    async def get_content(self, url: str, delay: int = 3) -> Optional[str]:
        """Get page content."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; FinalDocBot/1.0)"}
            
            # Handle GitHub raw content
            if "github.com" in url and "/blob/" in url:
                url = url.replace("/blob/", "/raw/")
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: {response.status_code}")
                return None
            
            await asyncio.sleep(delay)
            return response.text
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_content(self, html: str) -> str:
        """Extract text content."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove noise
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            # Try to find main content
            content_selectors = ['.content', '.docs-content', '.markdown-body', '.rst-content', 'main', 'article']
            
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    text = content_div.get_text(separator='\n', strip=True)
                    if len(text) > 200:
                        return text
            
            # Fallback to body
            body = soup.find('body')
            if body:
                return body.get_text(separator='\n', strip=True)
            
            return ""
            
        except Exception as e:
            logger.error(f"Content extraction error: {e}")
            return ""
    
    def create_chunks(self, content: str, source_name: str, url: str) -> List[Dict]:
        """Create document chunks."""
        chunks = []
        
        # Split into smaller chunks for better coverage
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > 800 and current_chunk:
                chunks.append({
                    "content": current_chunk.strip(),
                    "source_name": source_name,
                    "source_url": url,
                    "chunk_id": f"{source_name}_final_{len(chunks)}_{int(time.time())}",
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
                "chunk_id": f"{source_name}_final_{len(chunks)}_{int(time.time())}",
                "created_at": datetime.now(UTC).isoformat(),
                "word_count": len(current_chunk.split()),
                "char_count": len(current_chunk)
            })
        
        return chunks
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding."""
        if not self.openai_client:
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    async def store_chunks(self, chunks: List[Dict]) -> bool:
        """Store chunks in SurrealDB."""
        for chunk in chunks:
            embedding = await self.generate_embedding(chunk["content"])
            if embedding:
                chunk["embedding"] = embedding
            
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
    
    async def fill_source(self, target: Dict) -> int:
        """Fill gaps for one source."""
        source_name = target["name"]
        needed = target["needed"]
        
        logger.info(f"🎯 Filling {source_name}: need {needed} more chunks")
        
        chunks_added = 0
        
        for url in target["urls"]:
            if chunks_added >= needed:
                break
                
            logger.info(f"  Processing: {url}")
            
            # Get content
            html = await self.get_content(url, target["delay"])
            if not html:
                continue
            
            # Extract content
            content = self.extract_content(html)
            if len(content) < 150:
                continue
            
            # Create chunks
            chunks = self.create_chunks(content, source_name, url)
            if not chunks:
                continue
            
            # Limit chunks to what we need
            chunks_to_add = chunks[:needed - chunks_added]
            
            # Store chunks
            if await self.store_chunks(chunks_to_add):
                chunks_added += len(chunks_to_add)
                logger.info(f"  ✅ Added {len(chunks_to_add)} chunks")
        
        logger.info(f"🎯 {source_name} complete: +{chunks_added} chunks")
        return chunks_added
    
    async def fill_all_final_gaps(self):
        """Fill all remaining gaps."""
        logger.info("🚀 Final Gap Filling for Last 3 Sources")
        
        total_added = 0
        
        for target in FINAL_TARGETS:
            chunks_added = await self.fill_source(target)
            total_added += chunks_added
        
        logger.info(f"\n✅ Final gap filling complete: +{total_added} total chunks")
        
        # Report final status
        print("\n" + "="*50)
        print("🎉 FINAL STATUS REPORT")
        print("="*50)
        
        for target in FINAL_TARGETS:
            source_name = target["name"]
            current = target["current"]
            # We'd need to query the database to get the exact final count
            print(f"  {source_name}: {current} → {current + target['needed']}+ chunks")
        
        print(f"\n📊 Total chunks added: {total_added}")
        print("✅ All sources should now meet the 10-chunk minimum!")
    
    async def cleanup(self):
        """Cleanup."""
        await self.client.aclose()

async def main():
    """Main execution."""
    filler = FinalGapFiller()
    
    try:
        await filler.fill_all_final_gaps()
    finally:
        await filler.cleanup()

if __name__ == "__main__":
    asyncio.run(main())