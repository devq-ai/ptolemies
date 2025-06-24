#!/usr/bin/env python3
"""
Focused AnimeJS Crawler with Enhanced Debugging
Specifically targets AnimeJS documentation with robust error handling
"""

import asyncio
import httpx
import re
import subprocess
import os
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
import openai
import logfire
from dotenv import load_dotenv

load_dotenv()
logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

def run_surreal_query_with_debug(query: str) -> Tuple[bool, str]:
    """Execute SurrealDB query with detailed debugging."""
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
        
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        
        print(f"Query: {query[:100]}...")
        print(f"Success: {success}")
        if not success:
            print(f"Error: {output}")
            
        return success, output
        
    except Exception as e:
        print(f"Query execution failed: {e}")
        return False, str(e)

class AnimeJSFocusedCrawler:
    """Focused crawler specifically for AnimeJS with enhanced debugging."""
    
    def __init__(self):
        self.http_client = None
        self.openai_client = None
        self.chunks_attempted = 0
        self.chunks_stored = 0
        
    async def initialize(self):
        """Initialize HTTP and OpenAI clients."""
        print("🚀 Initializing AnimeJS Focused Crawler...")
        
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": "Ptolemies AnimeJS Crawler/1.0"},
            follow_redirects=True
        )
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=api_key)
            print("✅ OpenAI client initialized")
        else:
            print("❌ No OpenAI API key found")
            
        print("✅ HTTP client initialized")
            
    async def cleanup(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()
            
    def extract_animejs_content(self, html: str) -> Tuple[str, str]:
        """Extract content specifically from AnimeJS documentation."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # AnimeJS uses specific structure
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else "AnimeJS Documentation"
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', '.nav', '.navigation']):
                element.decompose()
                
            # AnimeJS documentation is often in specific containers
            content_selectors = [
                '.documentation',
                '.content',
                '.docs',
                'main',
                'article',
                '.container',
                'body'
            ]
            
            text_content = ""
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    text_content = content.get_text()
                    break
                    
            if not text_content:
                text_content = soup.get_text()
            
            # Clean the text
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Remove common navigation text
            clean_text = re.sub(r'(Home|Documentation|Examples|GitHub|npm)', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            print(f"Extracted {len(clean_text)} characters from {title}")
            
            return clean_text, title
            
        except Exception as e:
            print(f"Content extraction failed: {e}")
            return "", ""
            
    def create_chunks_debug(self, text: str, max_size: int = 1200) -> List[str]:
        """Create text chunks with debugging."""
        print(f"Creating chunks from {len(text)} characters...")
        
        if len(text) <= max_size:
            result = [text] if text.strip() else []
            print(f"Single chunk created: {len(result)} chunks")
            return result
            
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
            
        # Filter out very short chunks
        valid_chunks = [chunk for chunk in chunks if len(chunk) > 100]
        print(f"Created {len(valid_chunks)} valid chunks (filtered from {len(chunks)})")
        
        return valid_chunks
        
    def calculate_quality_debug(self, text: str, title: str, url: str) -> float:
        """Calculate content quality with debugging."""
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
        if any(indicator in url.lower() for indicator in ['/documentation', '/docs', '/guide']):
            score += 0.15
            
        # AnimeJS specific terms
        animejs_terms = ['anime', 'animation', 'javascript', 'timeline', 'easing', 'transform']
        found = sum(1 for term in animejs_terms if term in text.lower())
        score += min(found * 0.05, 0.25)
        
        final_score = min(score, 1.0)
        print(f"Quality score: {final_score:.2f} (length: {length}, title: {bool(title)}, terms: {found})")
        
        return final_score
        
    def extract_topics_debug(self, text: str, title: str) -> List[str]:
        """Extract topics with debugging."""
        topics = ["AnimeJS"]
        
        # Title words
        if title:
            title_words = re.findall(r'\b[A-Z][a-z]+\b', title)
            topics.extend(title_words[:2])
            
        # AnimeJS specific terms
        animejs_terms = [
            'animation', 'timeline', 'easing', 'transform', 'rotate', 'scale',
            'translate', 'opacity', 'duration', 'delay', 'javascript', 'css'
        ]
        
        text_lower = text.lower()
        for term in animejs_terms:
            if term in text_lower:
                topics.append(term)
                
        # Remove duplicates and limit
        unique_topics = list(dict.fromkeys(topics))[:8]
        print(f"Extracted topics: {unique_topics}")
        
        return unique_topics
        
    async def generate_embedding_debug(self, text: str) -> List[float]:
        """Generate embedding with debugging."""
        try:
            print(f"Generating embedding for {len(text)} characters...")
            
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],  # Limit input size
                dimensions=1536
            )
            
            embedding = response.data[0].embedding
            print(f"✅ Embedding generated: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            return []
            
    def store_chunk_debug(self, chunk_data: Dict[str, Any]) -> bool:
        """Store chunk with enhanced debugging."""
        try:
            print(f"\n--- Storing Chunk {self.chunks_attempted + 1} ---")
            self.chunks_attempted += 1
            
            # Safely escape content
            content = chunk_data['content'].replace("'", "''")[:2500]
            title = chunk_data['title'].replace("'", "''")[:200]
            source_url = chunk_data['source_url'].replace("'", "''")
            
            print(f"Content length: {len(content)}")
            print(f"Title: {title}")
            print(f"URL: {source_url}")
            
            # Format embedding
            embedding = chunk_data.get('embedding', [])
            if embedding and len(embedding) > 0:
                embedding_str = "[" + ", ".join(f"{float(x):.6f}" for x in embedding[:1536]) + "]"
                print(f"Embedding: {len(embedding)} dimensions")
            else:
                embedding_str = "[]"
                print("No embedding available")
            
            # Format topics
            topics = chunk_data.get('topics', ['AnimeJS'])
            topics_safe = [str(topic).replace("'", "''")[:50] for topic in topics[:10]]
            topics_str = "[" + ", ".join(f"'{topic}'" for topic in topics_safe) + "]"
            print(f"Topics: {topics_safe}")
            
            query = f"""
            CREATE document_chunks SET
                source_name = 'AnimeJS',
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
            
            success, output = run_surreal_query_with_debug(query)
            
            if success:
                self.chunks_stored += 1
                print(f"✅ Chunk stored successfully ({self.chunks_stored}/{self.chunks_attempted})")
                return True
            else:
                print(f"❌ Chunk storage failed: {output}")
                return False
                
        except Exception as e:
            print(f"❌ Exception during chunk storage: {e}")
            return False
    
    @logfire.instrument("animejs_focused_crawl")
    async def crawl_animejs_focused(self) -> int:
        """Focused crawl of AnimeJS with comprehensive debugging."""
        print("\n🎯 Starting Focused AnimeJS Crawl")
        print("=" * 50)
        
        # AnimeJS specific URLs with sections
        target_urls = [
            "https://animejs.com/documentation/",
            "https://animejs.com/documentation/#installation",
            "https://animejs.com/documentation/#basicExample", 
            "https://animejs.com/documentation/#targets",
            "https://animejs.com/documentation/#animationParameters",
            "https://animejs.com/documentation/#propertyParameters",
            "https://animejs.com/documentation/#animationKeyframes",
            "https://animejs.com/documentation/#timelineBasic",
            "https://animejs.com/documentation/#timelineParameters",
            "https://animejs.com/documentation/#controls",
            "https://animejs.com/documentation/#values",
            "https://animejs.com/documentation/#helpers",
        ]
        
        print(f"📋 Target URLs: {len(target_urls)}")
        
        for i, url in enumerate(target_urls, 1):
            try:
                print(f"\n🔄 [{i}/{len(target_urls)}] Crawling: {url}")
                
                response = await self.http_client.get(url)
                print(f"HTTP Status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ Skipping due to status code: {response.status_code}")
                    continue
                    
                # Extract content
                text_content, title = self.extract_animejs_content(response.text)
                
                if len(text_content) < 200:
                    print(f"❌ Content too short: {len(text_content)} characters")
                    continue
                    
                print(f"✅ Content extracted: {len(text_content)} characters")
                
                # Create chunks
                text_chunks = self.create_chunks_debug(text_content)
                
                if not text_chunks:
                    print("❌ No valid chunks created")
                    continue
                
                print(f"📄 Processing {len(text_chunks)} chunks...")
                
                for chunk_index, chunk_text in enumerate(text_chunks):
                    print(f"\n  📝 Chunk {chunk_index + 1}/{len(text_chunks)}")
                    
                    # Calculate quality
                    quality_score = self.calculate_quality_debug(chunk_text, title, url)
                    
                    # Extract topics
                    topics = self.extract_topics_debug(chunk_text, title)
                    
                    # Generate embedding
                    embedding = await self.generate_embedding_debug(chunk_text)
                    if not embedding:
                        print("❌ Skipping chunk due to embedding failure")
                        continue
                        
                    # Store chunk
                    chunk_data = {
                        'source_name': 'AnimeJS',
                        'source_url': url,
                        'title': title,
                        'content': chunk_text,
                        'chunk_index': chunk_index,
                        'total_chunks': len(text_chunks),
                        'quality_score': quality_score,
                        'topics': topics,
                        'embedding': embedding
                    }
                    
                    self.store_chunk_debug(chunk_data)
                    
                    # Small delay between chunks
                    await asyncio.sleep(0.5)
                
                # Delay between URLs
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Failed to process {url}: {e}")
                logfire.error("AnimeJS URL failed", url=url, error=str(e))
                continue
                
        print(f"\n🎉 AnimeJS Focused Crawl Complete!")
        print(f"📊 Results: {self.chunks_stored}/{self.chunks_attempted} chunks stored")
        
        return self.chunks_stored

async def main():
    """Main execution function."""
    crawler = AnimeJSFocusedCrawler()
    
    try:
        await crawler.initialize()
        chunks_created = await crawler.crawl_animejs_focused()
        
        print(f"\n✅ AnimeJS crawl completed: {chunks_created} chunks created")
        
        # Verify in database
        print("\n🔍 Verifying in database...")
        success, output = run_surreal_query_with_debug(
            "SELECT source_name, count() FROM document_chunks WHERE source_name = 'AnimeJS';"
        )
        
        if success:
            print("Database verification:")
            print(output)
        
        return chunks_created
        
    except Exception as e:
        print(f"❌ Crawler failed: {e}")
        return 0
    finally:
        await crawler.cleanup()

if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nFinal result: {result} chunks")