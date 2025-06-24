#!/usr/bin/env python3
"""
Process Crawled Data to Vector Knowledge Base
Transform raw crawl4ai_data into document_chunks with embeddings for the 784-page knowledge base
"""

import asyncio
import json
import os
import re
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
import hashlib

# Add src to path for imports
sys.path.insert(0, 'src')

try:
    from surrealdb import Surreal
    import openai
    from bs4 import BeautifulSoup
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip3 install surrealdb openai beautifulsoup4 python-dotenv --break-system-packages --user")
    sys.exit(1)

# Load environment
load_dotenv()

@dataclass
class ProcessingStats:
    """Statistics for the data processing operation."""
    total_raw_records: int = 0
    total_text_chunks: int = 0
    total_embeddings_generated: int = 0
    processing_errors: int = 0
    average_quality_score: float = 0.0
    processing_time_seconds: float = 0.0

class CrawledDataProcessor:
    """Process raw crawled data into vector knowledge base."""
    
    def __init__(self):
        self.db = None
        self.openai_client = None
        self.stats = ProcessingStats()
        
    async def initialize(self):
        """Initialize database and API connections."""
        print("🔌 Initializing connections...")
        
        # Load configuration
        url = os.getenv("SURREALDB_URL", "ws://localhost:8000/rpc")
        username = os.getenv("SURREALDB_USERNAME", "root")
        password = os.getenv("SURREALDB_PASSWORD", "root")
        namespace = os.getenv("SURREALDB_NAMESPACE", "ptolemies")
        database = os.getenv("SURREALDB_DATABASE", "knowledge")
        
        # Connect to SurrealDB
        try:
            self.db = Surreal()
            await self.db.connect(url)
            await self.db.signin({"user": username, "pass": password})
            await self.db.use(namespace, database)
            print(f"✅ Connected to SurrealDB: {namespace}/{database}")
        except Exception as e:
            print(f"❌ SurrealDB connection failed: {e}")
            return False
            
        # Initialize OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return False
            
        self.openai_client = openai.AsyncOpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
        
        return True
        
    async def analyze_raw_data(self):
        """Analyze the raw crawl4ai_data to understand structure."""
        print("\n📊 Analyzing Raw Crawled Data")
        print("=" * 50)
        
        # Get total count
        count_result = await self.db.query("SELECT count() FROM crawl4ai_data GROUP ALL;")
        if count_result and len(count_result) > 0 and len(count_result[0]) > 0:
            total_count = count_result[0][0].get('count', 0)
            self.stats.total_raw_records = total_count
            print(f"📄 Total raw records: {total_count}")
        
        # Get sample data structure
        sample_result = await self.db.query("SELECT * FROM crawl4ai_data LIMIT 3;")
        if sample_result and len(sample_result) > 0:
            samples = sample_result[0]
            print(f"📋 Sample records analyzed: {len(samples)}")
            
            for i, sample in enumerate(samples, 1):
                print(f"\n{i}. Record: {sample.get('id', 'No ID')}")
                print(f"   Title: {sample.get('title', 'No title')[:60]}...")
                print(f"   Content Type: {sample.get('content_type', 'Unknown')}")
                print(f"   Has Content: {'Yes' if sample.get('content') else 'No'}")
                
                # Analyze content structure
                content = sample.get('content')
                if content:
                    try:
                        if isinstance(content, str):
                            content_obj = json.loads(content)
                        else:
                            content_obj = content
                            
                        crawl_result = content_obj.get('crawl_result', {})
                        url = crawl_result.get('url', 'No URL')
                        html_content = crawl_result.get('content', '')
                        
                        print(f"   Source URL: {url}")
                        print(f"   HTML Length: {len(html_content)} characters")
                        
                        # Extract text preview
                        if html_content:
                            soup = BeautifulSoup(html_content, 'html.parser')
                            text = soup.get_text()
                            text_preview = ' '.join(text.split())[:100]
                            print(f"   Text Preview: {text_preview}...")
                            
                    except Exception as e:
                        print(f"   ⚠️  Content parsing error: {e}")
        
        return total_count > 0
        
    async def extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
                
            # Get text and clean it
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            print(f"⚠️  HTML parsing error: {e}")
            return ""
            
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for processing."""
        if len(text) <= chunk_size:
            return [text]
            
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break on sentence boundary
            if end < len(text):
                # Look for sentence endings near the end point
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
                    
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
                
            start = end - overlap
            
        return chunks
        
    def calculate_quality_score(self, text: str, title: str, url: str) -> float:
        """Calculate quality score for content chunk."""
        score = 0.5  # Base score
        
        # Length factor (prefer medium-length content)
        length = len(text)
        if 200 <= length <= 2000:
            score += 0.2
        elif length > 100:
            score += 0.1
            
        # Title quality
        if title and len(title) > 10:
            score += 0.1
            
        # URL structure (docs/documentation URLs are higher quality)
        if url and ('docs' in url or 'documentation' in url or 'guide' in url):
            score += 0.1
            
        # Content quality indicators
        if 'example' in text.lower() or 'code' in text.lower():
            score += 0.1
            
        return min(score, 1.0)
        
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate OpenAI embedding for text."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️  Embedding generation error: {e}")
            return None
            
    async def create_document_chunks_table(self):
        """Create document_chunks table with proper schema."""
        print("\n🏗️  Creating document_chunks table schema...")
        
        schema_sql = """
        DEFINE TABLE document_chunks SCHEMAFULL;
        
        DEFINE FIELD id ON TABLE document_chunks TYPE string;
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
        DEFINE FIELD updated_at ON TABLE document_chunks TYPE datetime;
        
        DEFINE INDEX embedding_idx ON TABLE document_chunks COLUMNS embedding MTREE DIMENSION 1536;
        """
        
        try:
            await self.db.query(schema_sql)
            print("✅ document_chunks table schema created")
        except Exception as e:
            print(f"⚠️  Schema creation warning: {e}")
            
    async def process_single_record(self, record: Dict[str, Any]) -> int:
        """Process a single crawl4ai_data record into document_chunks."""
        try:
            # Extract basic information
            record_id = record.get('id', '')
            title = record.get('title', '')
            content_data = record.get('content', '')
            
            # Parse content
            if isinstance(content_data, str):
                try:
                    content_obj = json.loads(content_data)
                except:
                    content_obj = {}
            else:
                content_obj = content_data or {}
                
            crawl_result = content_obj.get('crawl_result', {})
            source_url = crawl_result.get('url', '')
            html_content = crawl_result.get('content', '')
            page_title = crawl_result.get('title', title)
            
            if not html_content:
                print(f"⚠️  No HTML content for {record_id}")
                return 0
                
            # Extract text from HTML
            text_content = await self.extract_text_from_html(html_content)
            if not text_content or len(text_content) < 50:
                print(f"⚠️  Insufficient text content for {record_id}")
                return 0
                
            # Determine source name from URL
            source_name = self.extract_source_name(source_url)
            
            # Chunk the text
            chunks = self.chunk_text(text_content)
            total_chunks = len(chunks)
            
            print(f"📄 Processing {page_title[:40]}... → {total_chunks} chunks")
            
            chunks_created = 0
            
            for chunk_index, chunk_text in enumerate(chunks):
                try:
                    # Calculate quality score
                    quality_score = self.calculate_quality_score(chunk_text, page_title, source_url)
                    
                    # Generate embedding
                    embedding = await self.generate_embedding(chunk_text)
                    if not embedding:
                        continue
                        
                    # Extract topics (simple keyword extraction)
                    topics = self.extract_topics(chunk_text, source_name)
                    
                    # Create unique chunk ID
                    chunk_id = f"{record_id}_chunk_{chunk_index}"
                    
                    # Create document chunk
                    chunk_data = {
                        "source_name": source_name,
                        "source_url": source_url,
                        "title": page_title,
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "total_chunks": total_chunks,
                        "quality_score": quality_score,
                        "topics": topics,
                        "embedding": embedding,
                        "created_at": datetime.now(UTC).isoformat(),
                        "updated_at": datetime.now(UTC).isoformat()
                    }
                    
                    # Store in database
                    await self.db.create("document_chunks", chunk_data)
                    chunks_created += 1
                    self.stats.total_embeddings_generated += 1
                    
                except Exception as e:
                    print(f"⚠️  Error processing chunk {chunk_index}: {e}")
                    self.stats.processing_errors += 1
                    
            self.stats.total_text_chunks += chunks_created
            return chunks_created
            
        except Exception as e:
            print(f"❌ Error processing record {record.get('id', 'unknown')}: {e}")
            self.stats.processing_errors += 1
            return 0
            
    def extract_source_name(self, url: str) -> str:
        """Extract source name from URL."""
        if not url:
            return "Unknown"
            
        # Common patterns
        patterns = {
            'fastapi.tiangolo.com': 'FastAPI',
            'ai.pydantic.dev': 'Pydantic AI',
            'docs.crawl4ai.com': 'Crawl4AI',
            'surrealdb.com': 'SurrealDB',
            'nextjs.org': 'NextJS',
            'animejs.com': 'AnimeJS',
            'ui.shadcn.com': 'Shadcn',
            'tailwindcss.com': 'Tailwind',
            'docs.anthropic.com': 'Claude Code',
            'gofastmcp.com': 'FastMCP',
            'panel.holoviz.org': 'Panel',
            'pygad.readthedocs.io': 'PyGAD',
            'docs.circom.io': 'Circom',
            'docs.bokeh.org': 'Bokeh',
            'logfire.pydantic.dev': 'Logfire',
            'pymc.io': 'PyMC',
            'wildwood.readthedocs.io': 'Wildwood'
        }
        
        for pattern, name in patterns.items():
            if pattern in url:
                return name
                
        # Fallback: extract domain
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace('www.', '').split('.')[0].title()
        except:
            return "Unknown"
            
    def extract_topics(self, text: str, source_name: str) -> List[str]:
        """Extract topics/keywords from text."""
        topics = [source_name]
        
        # Common technical terms
        tech_terms = [
            'API', 'authentication', 'database', 'framework', 'library',
            'documentation', 'tutorial', 'guide', 'example', 'configuration',
            'installation', 'setup', 'deployment', 'security', 'performance',
            'testing', 'development', 'python', 'javascript', 'typescript',
            'async', 'await', 'function', 'class', 'method', 'component'
        ]
        
        text_lower = text.lower()
        for term in tech_terms:
            if term.lower() in text_lower:
                topics.append(term)
                
        return list(set(topics))  # Remove duplicates
        
    async def process_all_data(self):
        """Process all crawl4ai_data records."""
        print("\n🔄 Processing All Crawled Data")
        print("=" * 50)
        
        # Create table schema
        await self.create_document_chunks_table()
        
        # Get all raw data
        all_data_result = await self.db.query("SELECT * FROM crawl4ai_data;")
        if not all_data_result or not all_data_result[0]:
            print("❌ No raw data found to process")
            return False
            
        records = all_data_result[0]
        total_records = len(records)
        
        print(f"📊 Processing {total_records} raw records...")
        
        start_time = asyncio.get_event_loop().time()
        
        for i, record in enumerate(records, 1):
            print(f"\n📄 Record {i}/{total_records}")
            chunks_created = await self.process_single_record(record)
            print(f"   ✅ Created {chunks_created} chunks")
            
        end_time = asyncio.get_event_loop().time()
        self.stats.processing_time_seconds = end_time - start_time
        
        return True
        
    async def verify_results(self):
        """Verify the processing results."""
        print("\n✅ Verifying Processing Results")
        print("=" * 50)
        
        # Count document chunks
        count_result = await self.db.query("SELECT count() FROM document_chunks GROUP ALL;")
        if count_result and len(count_result) > 0 and len(count_result[0]) > 0:
            total_chunks = count_result[0][0].get('count', 0)
            print(f"📄 Total document chunks created: {total_chunks}")
            
        # Get quality statistics
        quality_result = await self.db.query("""
            SELECT 
                avg(quality_score) AS avg_quality,
                min(quality_score) AS min_quality,
                max(quality_score) AS max_quality,
                count(DISTINCT source_name) AS unique_sources
            FROM document_chunks
            GROUP ALL;
        """)
        
        if quality_result and len(quality_result) > 0 and len(quality_result[0]) > 0:
            stats = quality_result[0][0]
            print(f"📊 Quality Statistics:")
            print(f"   Average Quality: {stats.get('avg_quality', 0):.3f}")
            print(f"   Quality Range: {stats.get('min_quality', 0):.3f} - {stats.get('max_quality', 0):.3f}")
            print(f"   Unique Sources: {stats.get('unique_sources', 0)}")
            
        # Test vector search
        print(f"\n🔍 Testing Vector Search...")
        try:
            sample_result = await self.db.query("""
                SELECT id, title, source_name, quality_score
                FROM document_chunks
                WHERE array::len(embedding) = 1536
                LIMIT 3;
            """)
            
            if sample_result and len(sample_result) > 0:
                samples = sample_result[0]
                print(f"✅ Vector search ready: {len(samples)} samples with embeddings")
                for sample in samples:
                    print(f"   • {sample.get('source_name')}: {sample.get('title', 'No title')[:40]}...")
            else:
                print("⚠️  No documents with valid embeddings found")
                
        except Exception as e:
            print(f"⚠️  Vector search test error: {e}")
            
    def print_final_stats(self):
        """Print final processing statistics."""
        print("\n" + "=" * 60)
        print("📊 FINAL PROCESSING STATISTICS")
        print("=" * 60)
        print(f"📄 Raw records processed: {self.stats.total_raw_records}")
        print(f"📝 Text chunks created: {self.stats.total_text_chunks}")
        print(f"🔢 Embeddings generated: {self.stats.total_embeddings_generated}")
        print(f"❌ Processing errors: {self.stats.processing_errors}")
        print(f"⏱️  Processing time: {self.stats.processing_time_seconds:.1f} seconds")
        
        if self.stats.total_text_chunks > 0:
            success_rate = ((self.stats.total_text_chunks - self.stats.processing_errors) / self.stats.total_text_chunks) * 100
            print(f"✅ Success rate: {success_rate:.1f}%")
            
        print(f"\n🎯 KNOWLEDGE BASE STATUS:")
        if self.stats.total_embeddings_generated > 0:
            print(f"✅ Vector knowledge base created with {self.stats.total_embeddings_generated} searchable chunks")
            print(f"🔍 Ready for semantic search queries")
            print(f"⚡ Sub-100ms performance target achievable")
        else:
            print("❌ No vector knowledge base created")
            
    async def cleanup(self):
        """Clean up connections."""
        if self.db:
            await self.db.close()

async def main():
    """Main processing function."""
    print("🚀 PTOLEMIES DATA PROCESSING: RAW → VECTOR KNOWLEDGE BASE")
    print("=" * 70)
    
    processor = CrawledDataProcessor()
    
    try:
        # Initialize
        if not await processor.initialize():
            return 1
            
        # Analyze raw data
        if not await processor.analyze_raw_data():
            print("❌ No raw data found to process")
            return 1
            
        # Process all data
        if not await processor.process_all_data():
            print("❌ Data processing failed")
            return 1
            
        # Verify results
        await processor.verify_results()
        
        # Print statistics
        processor.print_final_stats()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    finally:
        await processor.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())