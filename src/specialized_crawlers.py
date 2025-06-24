#!/usr/bin/env python3
"""
Specialized Crawlers for Missing Sources
Targets Pydantic AI, Logfire, AnimeJS, and PyMC with optimized strategies
"""

import asyncio
import httpx
import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import openai
import os
import subprocess
import logfire
from dotenv import load_dotenv

load_dotenv()
logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

def run_surreal_query(query: str) -> bool:
    """Execute SurrealDB query using CLI."""
    cmd = [
        'surreal', 'sql',
        '--conn', 'ws://localhost:8000/rpc',
        '--user', 'root',
        '--pass', 'root',
        '--ns', 'ptolemies',
        '--db', 'knowledge',
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
        return result.returncode == 0
    except Exception:
        return False

class SpecializedCrawler:
    """Base class for specialized crawlers."""
    
    def __init__(self):
        self.http_client = None
        self.openai_client = None
        
    async def initialize(self):
        """Initialize HTTP and OpenAI clients."""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": "Ptolemies Specialized Crawler/1.0"},
            follow_redirects=True
        )
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=api_key)
            
    async def cleanup(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()
            
    def extract_text_from_html(self, html: str) -> tuple[str, str]:
        """Extract content and title from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
                
            # Get main content
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find(class_=re.compile(r'content|main|docs|documentation'))
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
        """Create text chunks with sentence boundaries."""
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
        if any(indicator in url.lower() for indicator in ['/docs/', '/guide/', '/api/', '/documentation/']):
            score += 0.15
            
        # Content quality
        quality_terms = ['example', 'code', 'function', 'api', 'install', 'tutorial', 'guide']
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
        
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536
            )
            return response.data[0].embedding
        except Exception as e:
            logfire.error("Embedding generation failed", error=str(e))
            return []
            
    def store_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """Store document chunk in SurrealDB."""
        try:
            # Safely escape content for SQL
            content = chunk_data['content'].replace("'", "''").replace('"', '""')[:2500]
            title = chunk_data['title'].replace("'", "''").replace('"', '""')[:200]
            source_name = chunk_data['source_name'].replace("'", "''")
            source_url = chunk_data['source_url'].replace("'", "''")
            
            # Format embedding array
            embedding = chunk_data.get('embedding', [])
            if embedding and len(embedding) > 0:
                embedding_str = "[" + ", ".join(f"{float(x):.6f}" for x in embedding[:1536]) + "]"
            else:
                embedding_str = "[]"
            
            # Format topics array
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
            
            return run_surreal_query(query)
            
        except Exception as e:
            logfire.error("Chunk storage failed", error=str(e))
            return False

class PydanticAICrawler(SpecializedCrawler):
    """Specialized crawler for Pydantic AI documentation."""
    
    @logfire.instrument("pydantic_ai_crawl")
    async def crawl_pydantic_ai(self) -> int:
        """Crawl Pydantic AI documentation with focused strategy."""
        source_name = "Pydantic AI"
        base_url = "https://ai.pydantic.dev"
        
        # Pydantic AI specific URLs
        target_urls = [
            "https://ai.pydantic.dev/",
            "https://ai.pydantic.dev/install/",
            "https://ai.pydantic.dev/agents/",
            "https://ai.pydantic.dev/api/agent/",
            "https://ai.pydantic.dev/models/",
            "https://ai.pydantic.dev/tools/",
            "https://ai.pydantic.dev/results/",
            "https://ai.pydantic.dev/dependencies/",
            "https://ai.pydantic.dev/streaming/",
            "https://ai.pydantic.dev/examples/",
            "https://ai.pydantic.dev/testing/",
            "https://ai.pydantic.dev/api/",
        ]
        
        chunks_created = 0
        
        for url in target_urls:
            try:
                logfire.info("Crawling Pydantic AI page", url=url)
                response = await self.http_client.get(url)
                
                if response.status_code != 200:
                    continue
                    
                text_content, title = self.extract_text_from_html(response.text)
                
                if len(text_content) < 200:
                    continue
                    
                # Create chunks
                text_chunks = self.create_chunks(text_content)
                
                for chunk_index, chunk_text in enumerate(text_chunks):
                    quality_score = self.calculate_quality(chunk_text, title, url, source_name)
                    topics = self.extract_topics(chunk_text, title, source_name)
                    
                    # Generate embedding
                    embedding = await self.generate_embedding(chunk_text)
                    if not embedding:
                        continue
                        
                    # Store chunk
                    chunk_data = {
                        'source_name': source_name,
                        'source_url': url,
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
                        
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logfire.error("Pydantic AI page failed", url=url, error=str(e))
                continue
                
        logfire.info("Pydantic AI crawl completed", chunks_created=chunks_created)
        return chunks_created

class LogfireCrawler(SpecializedCrawler):
    """Specialized crawler for Logfire documentation."""
    
    @logfire.instrument("logfire_crawl")
    async def crawl_logfire(self) -> int:
        """Crawl Logfire documentation with focused strategy."""
        source_name = "Logfire"
        base_url = "https://logfire.pydantic.dev"
        
        # Logfire specific URLs
        target_urls = [
            "https://logfire.pydantic.dev/docs/",
            "https://logfire.pydantic.dev/docs/getting-started/",
            "https://logfire.pydantic.dev/docs/getting-started/installation/",
            "https://logfire.pydantic.dev/docs/guides/",
            "https://logfire.pydantic.dev/docs/guides/first-steps/",
            "https://logfire.pydantic.dev/docs/guides/web-ui/",
            "https://logfire.pydantic.dev/docs/integrations/",
            "https://logfire.pydantic.dev/docs/integrations/fastapi/",
            "https://logfire.pydantic.dev/docs/integrations/pydantic/",
            "https://logfire.pydantic.dev/docs/api/",
            "https://logfire.pydantic.dev/docs/reference/",
        ]
        
        chunks_created = 0
        
        for url in target_urls:
            try:
                logfire.info("Crawling Logfire page", url=url)
                response = await self.http_client.get(url)
                
                if response.status_code != 200:
                    continue
                    
                text_content, title = self.extract_text_from_html(response.text)
                
                if len(text_content) < 200:
                    continue
                    
                # Create chunks
                text_chunks = self.create_chunks(text_content)
                
                for chunk_index, chunk_text in enumerate(text_chunks):
                    quality_score = self.calculate_quality(chunk_text, title, url, source_name)
                    topics = self.extract_topics(chunk_text, title, source_name)
                    
                    # Generate embedding
                    embedding = await self.generate_embedding(chunk_text)
                    if not embedding:
                        continue
                        
                    # Store chunk
                    chunk_data = {
                        'source_name': source_name,
                        'source_url': url,
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
                        
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logfire.error("Logfire page failed", url=url, error=str(e))
                continue
                
        logfire.info("Logfire crawl completed", chunks_created=chunks_created)
        return chunks_created

class AnimeJSCrawler(SpecializedCrawler):
    """Specialized crawler for AnimeJS documentation."""
    
    @logfire.instrument("animejs_crawl")
    async def crawl_animejs(self) -> int:
        """Crawl AnimeJS documentation with focused strategy."""
        source_name = "AnimeJS"
        base_url = "https://animejs.com"
        
        # AnimeJS specific URLs
        target_urls = [
            "https://animejs.com/documentation/",
            "https://animejs.com/documentation/#installation",
            "https://animejs.com/documentation/#basicExample",
            "https://animejs.com/documentation/#targets",
            "https://animejs.com/documentation/#animationParameters",
            "https://animejs.com/documentation/#propertyParameters",
            "https://animejs.com/documentation/#animationKeyframes",
            "https://animejs.com/documentation/#timelineBasic",
            "https://animejs.com/documentation/#controls",
            "https://animejs.com/documentation/#values",
            "https://animejs.com/documentation/#helpers",
        ]
        
        chunks_created = 0
        
        for url in target_urls:
            try:
                logfire.info("Crawling AnimeJS page", url=url)
                response = await self.http_client.get(url)
                
                if response.status_code != 200:
                    continue
                    
                text_content, title = self.extract_text_from_html(response.text)
                
                if len(text_content) < 200:
                    continue
                    
                # Create chunks
                text_chunks = self.create_chunks(text_content)
                
                for chunk_index, chunk_text in enumerate(text_chunks):
                    quality_score = self.calculate_quality(chunk_text, title, url, source_name)
                    topics = self.extract_topics(chunk_text, title, source_name)
                    
                    # Generate embedding
                    embedding = await self.generate_embedding(chunk_text)
                    if not embedding:
                        continue
                        
                    # Store chunk
                    chunk_data = {
                        'source_name': source_name,
                        'source_url': url,
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
                        
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logfire.error("AnimeJS page failed", url=url, error=str(e))
                continue
                
        logfire.info("AnimeJS crawl completed", chunks_created=chunks_created)
        return chunks_created

class PyMCCrawler(SpecializedCrawler):
    """Specialized crawler for PyMC documentation."""
    
    @logfire.instrument("pymc_crawl")
    async def crawl_pymc(self) -> int:
        """Crawl PyMC documentation with focused strategy."""
        source_name = "PyMC"
        base_url = "https://www.pymc.io"
        
        # PyMC specific URLs  
        target_urls = [
            "https://www.pymc.io/",
            "https://docs.pymc.io/en/stable/",
            "https://docs.pymc.io/en/stable/learn.html",
            "https://docs.pymc.io/en/stable/api.html",
            "https://docs.pymc.io/en/stable/contributing/index.html",
            "https://docs.pymc.io/en/stable/learn/core_notebooks/getting_started.html",
            "https://docs.pymc.io/en/stable/learn/core_notebooks/GLM_linear.html",
            "https://docs.pymc.io/en/stable/learn/core_notebooks/sampling_multiple_chains.html",
        ]
        
        chunks_created = 0
        
        for url in target_urls:
            try:
                logfire.info("Crawling PyMC page", url=url)
                response = await self.http_client.get(url)
                
                if response.status_code != 200:
                    continue
                    
                text_content, title = self.extract_text_from_html(response.text)
                
                if len(text_content) < 200:
                    continue
                    
                # Create chunks
                text_chunks = self.create_chunks(text_content)
                
                for chunk_index, chunk_text in enumerate(text_chunks):
                    quality_score = self.calculate_quality(chunk_text, title, url, source_name)
                    topics = self.extract_topics(chunk_text, title, source_name)
                    
                    # Generate embedding
                    embedding = await self.generate_embedding(chunk_text)
                    if not embedding:
                        continue
                        
                    # Store chunk
                    chunk_data = {
                        'source_name': source_name,
                        'source_url': url,
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
                        
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logfire.error("PyMC page failed", url=url, error=str(e))
                continue
                
        logfire.info("PyMC crawl completed", chunks_created=chunks_created)
        return chunks_created

async def run_specialized_crawlers():
    """Run all specialized crawlers for missing sources."""
    
    print("🚀 Starting Specialized Crawlers for Missing Sources")
    print("=" * 60)
    
    # Initialize crawlers
    pydantic_crawler = PydanticAICrawler()
    logfire_crawler = LogfireCrawler()
    animejs_crawler = AnimeJSCrawler()
    pymc_crawler = PyMCCrawler()
    
    crawlers = [
        (pydantic_crawler, "Pydantic AI"),
        (logfire_crawler, "Logfire"),
        (animejs_crawler, "AnimeJS"),
        (pymc_crawler, "PyMC")
    ]
    
    total_chunks = 0
    
    for crawler, name in crawlers:
        try:
            print(f"\n🔄 Crawling {name}...")
            await crawler.initialize()
            
            if name == "Pydantic AI":
                chunks = await crawler.crawl_pydantic_ai()
            elif name == "Logfire":
                chunks = await crawler.crawl_logfire()
            elif name == "AnimeJS":
                chunks = await crawler.crawl_animejs()
            elif name == "PyMC":
                chunks = await crawler.crawl_pymc()
            else:
                chunks = 0
                
            total_chunks += chunks
            print(f"✅ {name}: {chunks} chunks created")
            
            await crawler.cleanup()
            
        except Exception as e:
            print(f"❌ {name}: Failed - {str(e)}")
            logfire.error(f"{name} crawler failed", error=str(e))
            
    print(f"\n🎉 Specialized crawlers completed!")
    print(f"📊 Total new chunks: {total_chunks}")
    
    return total_chunks

if __name__ == "__main__":
    import re
    asyncio.run(run_specialized_crawlers())