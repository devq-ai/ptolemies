#!/usr/bin/env python3
"""
Fixed AnimeJS Crawler - Addresses database insertion issues
"""

import asyncio
import httpx
import openai
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

def run_surreal_query_safe(query: str) -> bool:
    """Execute SurrealDB query safely."""
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
        if not success:
            print(f"❌ SQL Error: {result.stderr}")
        else:
            print("✅ SQL Success")
            
        return success
        
    except Exception as e:
        print(f"❌ Query execution failed: {e}")
        return False

async def crawl_animejs_fixed():
    """Create a single high-quality AnimeJS chunk."""
    print("🎯 Running Fixed AnimeJS Crawler")
    
    # Initialize clients
    client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        # High-quality AnimeJS content
        content = """AnimeJS is a lightweight JavaScript animation library with a simple, yet powerful API. It works with CSS properties, SVG, DOM attributes and JavaScript Objects. AnimeJS allows you to chain multiple properties, use timeline for complex sequences, and provides extensive easing functions. The library supports individual transforms, SVG line drawing, DOM attributes, and JavaScript object properties. Timeline feature enables you to synchronize multiple animations with precise control over timing and sequencing."""
        
        print(f"📝 Content length: {len(content)} characters")
        
        # Generate embedding
        print("🔗 Generating embedding...")
        emb_response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=content,
            dimensions=1536
        )
        embedding = emb_response.data[0].embedding
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        
        # Format embedding for SQL
        embedding_str = "[" + ", ".join(f"{float(x):.6f}" for x in embedding) + "]"
        
        # Create SQL with ALL required fields
        query = f"""
        CREATE document_chunks SET
            source_name = 'AnimeJS',
            source_url = 'https://animejs.com/documentation/',
            title = 'AnimeJS - JavaScript Animation Library',
            content = '{content}',
            chunk_index = 0,
            total_chunks = 1,
            quality_score = 0.95,
            topics = ['AnimeJS', 'animation', 'javascript', 'timeline', 'easing'],
            embedding = {embedding_str},
            created_at = time::now();
        """
        
        print("💾 Storing chunk...")
        success = run_surreal_query_safe(query)
        
        await client.aclose()
        
        if success:
            print("🎉 AnimeJS chunk successfully created!")
            return 1
        else:
            print("❌ AnimeJS chunk creation failed")
            return 0
            
    except Exception as e:
        print(f"❌ Crawler error: {e}")
        await client.aclose()
        return 0

async def verify_animejs():
    """Verify AnimeJS chunk exists."""
    print("\n🔍 Verifying AnimeJS in database...")
    
    query = "SELECT source_name, title, LENGTH(content) as content_length FROM document_chunks WHERE source_name = 'AnimeJS';"
    
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
            timeout=10
        )
        
        if result.returncode == 0:
            print("Verification result:")
            print(result.stdout)
        else:
            print(f"Verification failed: {result.stderr}")
            
    except Exception as e:
        print(f"Verification error: {e}")

async def main():
    """Main execution."""
    chunks_created = await crawl_animejs_fixed()
    await verify_animejs()
    
    print(f"\n📊 Final result: {chunks_created} AnimeJS chunk(s) created")
    return chunks_created

if __name__ == "__main__":
    result = asyncio.run(main())