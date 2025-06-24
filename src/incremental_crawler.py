#!/usr/bin/env python3
"""
Incremental Crawler for Large Documentation Sources
Optimized for Claude Code and other high-volume documentation
"""

import asyncio
import json
import os
import hashlib
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Set, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
import logfire
from pathlib import Path

logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

class IncrementalCrawler:
    """Handles incremental updates for large documentation sources."""
    
    def __init__(self, cache_dir: str = "crawl_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.url_cache_file = self.cache_dir / "url_checksums.json"
        self.metadata_file = self.cache_dir / "crawl_metadata.json"
        self.url_checksums = self._load_url_cache()
        self.metadata = self._load_metadata()
        
    def _load_url_cache(self) -> Dict[str, Dict[str, str]]:
        """Load URL checksums from cache."""
        if self.url_cache_file.exists():
            with open(self.url_cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_url_cache(self):
        """Save URL checksums to cache."""
        with open(self.url_cache_file, 'w') as f:
            json.dump(self.url_checksums, f, indent=2)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load crawl metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """Save crawl metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    @logfire.instrument("calculate_content_hash")
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @logfire.instrument("check_url_changed")
    async def check_url_changed(self, url: str, content: str) -> Tuple[bool, Optional[str]]:
        """Check if URL content has changed since last crawl."""
        content_hash = self.calculate_content_hash(content)
        
        if url in self.url_checksums:
            old_hash = self.url_checksums[url].get('hash')
            if old_hash == content_hash:
                return False, old_hash
        
        return True, content_hash
    
    @logfire.instrument("get_changed_urls")
    async def get_changed_urls(self, source_name: str, urls: List[str], 
                             http_client: httpx.AsyncClient) -> List[Dict[str, str]]:
        """Get list of URLs that have changed since last crawl."""
        changed_urls = []
        
        with logfire.span("Checking URLs for changes", source=source_name, url_count=len(urls)):
            for url in urls:
                try:
                    response = await http_client.get(url)
                    if response.status_code == 200:
                        changed, content_hash = await self.check_url_changed(url, response.text)
                        
                        if changed:
                            changed_urls.append({
                                'url': url,
                                'content': response.text,
                                'hash': content_hash
                            })
                            logfire.info("URL changed", url=url)
                        else:
                            logfire.debug("URL unchanged", url=url)
                    
                    await asyncio.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    logfire.error("Failed to check URL", url=url, error=str(e))
        
        return changed_urls
    
    @logfire.instrument("update_cache")
    def update_cache(self, url: str, content_hash: str, chunks_created: int):
        """Update cache with crawl results."""
        self.url_checksums[url] = {
            'hash': content_hash,
            'last_crawled': datetime.now(UTC).isoformat(),
            'chunks': chunks_created
        }
    
    @logfire.instrument("should_full_recrawl")
    def should_full_recrawl(self, source_name: str, days: int = 7) -> bool:
        """Check if source needs full recrawl based on age."""
        if source_name not in self.metadata:
            return True
        
        last_full_crawl = self.metadata[source_name].get('last_full_crawl')
        if not last_full_crawl:
            return True
        
        last_crawl_date = datetime.fromisoformat(last_full_crawl.replace('Z', '+00:00'))
        age = datetime.now(UTC) - last_crawl_date
        
        return age.days >= days
    
    @logfire.instrument("get_crawl_statistics")
    def get_crawl_statistics(self, source_name: str) -> Dict[str, Any]:
        """Get statistics for a source."""
        stats = {
            'total_urls': 0,
            'last_crawled_urls': 0,
            'total_chunks': 0,
            'last_full_crawl': None,
            'last_incremental': None
        }
        
        # Count URLs for this source
        source_urls = [url for url in self.url_checksums if source_name.lower() in url.lower()]
        stats['total_urls'] = len(source_urls)
        
        # Get metadata
        if source_name in self.metadata:
            meta = self.metadata[source_name]
            stats['last_full_crawl'] = meta.get('last_full_crawl')
            stats['last_incremental'] = meta.get('last_incremental')
            stats['total_chunks'] = meta.get('total_chunks', 0)
        
        return stats
    
    @logfire.instrument("mark_crawl_complete")
    def mark_crawl_complete(self, source_name: str, crawl_type: str, 
                          urls_crawled: int, chunks_created: int):
        """Mark crawl as complete and update metadata."""
        if source_name not in self.metadata:
            self.metadata[source_name] = {}
        
        timestamp = datetime.now(UTC).isoformat()
        
        if crawl_type == 'full':
            self.metadata[source_name]['last_full_crawl'] = timestamp
            self.metadata[source_name]['total_chunks'] = chunks_created
        else:
            self.metadata[source_name]['last_incremental'] = timestamp
            self.metadata[source_name]['last_incremental_chunks'] = chunks_created
        
        self.metadata[source_name]['last_urls_crawled'] = urls_crawled
        
        self._save_metadata()
        self._save_url_cache()
        
        logfire.info("Crawl marked complete",
                    source=source_name,
                    type=crawl_type,
                    urls=urls_crawled,
                    chunks=chunks_created)


class ClaudeCodeOptimizedCrawler:
    """Optimized crawler specifically for Claude Code documentation."""
    
    def __init__(self, incremental_crawler: IncrementalCrawler):
        self.incremental = incremental_crawler
        self.base_url = "https://docs.anthropic.com"
        self.priority_paths = [
            "/en/docs/claude-code/overview",
            "/en/docs/claude-code/quickstart",
            "/en/docs/claude-code/memory",
            "/en/docs/claude-code/common-workflows",
            "/en/docs/claude-code/mcp",
            "/en/docs/claude-code/cli-reference",
            "/en/docs/claude-code/settings"
        ]
        
    @logfire.instrument("get_claude_code_urls")
    async def get_all_urls(self, http_client: httpx.AsyncClient) -> List[str]:
        """Get all Claude Code documentation URLs."""
        urls = set()
        
        # Start with priority paths
        for path in self.priority_paths:
            urls.add(f"{self.base_url}{path}")
        
        # Crawl main page for additional links
        try:
            response = await http_client.get(f"{self.base_url}/en/docs/claude-code/overview")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all documentation links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/docs/claude-code/' in href:
                        if href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            continue
                        
                        if 'claude-code' in full_url:
                            urls.add(full_url.split('#')[0])  # Remove anchors
        
        except Exception as e:
            logfire.error("Failed to get Claude Code URLs", error=str(e))
        
        return sorted(list(urls))
    
    @logfire.instrument("optimize_claude_code_crawl")
    async def crawl_optimized(self, production_crawler) -> int:
        """Perform optimized crawl of Claude Code documentation."""
        stats = self.incremental.get_crawl_statistics("Claude Code")
        
        # Decide crawl type
        if self.incremental.should_full_recrawl("Claude Code", days=7):
            return await self._full_crawl(production_crawler)
        else:
            return await self._incremental_crawl(production_crawler)
    
    async def _full_crawl(self, production_crawler) -> int:
        """Perform full crawl of Claude Code."""
        logfire.info("Starting full Claude Code crawl")
        
        # Get all URLs
        urls = await self.get_all_urls(production_crawler.http_client)
        
        chunks_created = 0
        urls_processed = 0
        
        for url in urls:
            try:
                response = await production_crawler.http_client.get(url)
                if response.status_code == 200:
                    content, title = production_crawler.extract_text_from_html(response.text)
                    
                    if len(content) > 200:
                        # Create chunks
                        text_chunks = production_crawler.create_chunks(content)
                        
                        for chunk_index, chunk_text in enumerate(text_chunks):
                            # Calculate quality
                            quality_score = production_crawler.calculate_quality(
                                chunk_text, title, url, "Claude Code"
                            )
                            
                            # Extract topics
                            topics = production_crawler.extract_topics(
                                chunk_text, title, "Claude Code"
                            )
                            
                            # Generate embedding
                            embedding = await production_crawler.generate_embedding(chunk_text)
                            if not embedding:
                                continue
                            
                            # Store chunk
                            chunk_data = {
                                'source_name': 'Claude Code',
                                'source_url': url,
                                'title': title,
                                'content': chunk_text,
                                'chunk_index': chunk_index,
                                'total_chunks': len(text_chunks),
                                'quality_score': quality_score,
                                'topics': topics,
                                'embedding': embedding
                            }
                            
                            if production_crawler.store_chunk(chunk_data):
                                chunks_created += 1
                        
                        # Update cache
                        content_hash = self.incremental.calculate_content_hash(response.text)
                        self.incremental.update_cache(url, content_hash, len(text_chunks))
                        
                        urls_processed += 1
                    
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logfire.error("Failed to crawl Claude Code URL", url=url, error=str(e))
        
        # Mark crawl complete
        self.incremental.mark_crawl_complete("Claude Code", "full", urls_processed, chunks_created)
        
        return chunks_created
    
    async def _incremental_crawl(self, production_crawler) -> int:
        """Perform incremental crawl of Claude Code."""
        logfire.info("Starting incremental Claude Code crawl")
        
        # Get all URLs
        all_urls = await self.get_all_urls(production_crawler.http_client)
        
        # Check which URLs have changed
        changed_urls = await self.incremental.get_changed_urls(
            "Claude Code", all_urls, production_crawler.http_client
        )
        
        if not changed_urls:
            logfire.info("No changes detected in Claude Code documentation")
            return 0
        
        logfire.info(f"Found {len(changed_urls)} changed URLs in Claude Code")
        
        # Process only changed URLs
        chunks_created = 0
        
        for url_data in changed_urls:
            url = url_data['url']
            content = url_data['content']
            
            try:
                # Extract and process content
                text_content, title = production_crawler.extract_text_from_html(content)
                
                if len(text_content) > 200:
                    # Delete old chunks for this URL
                    delete_query = f"""
                    DELETE document_chunks WHERE source_url = '{url}';
                    """
                    from production_crawler_hybrid import run_surreal_query
                    run_surreal_query(delete_query)
                    
                    # Create new chunks
                    text_chunks = production_crawler.create_chunks(text_content)
                    
                    for chunk_index, chunk_text in enumerate(text_chunks):
                        # Process as before
                        quality_score = production_crawler.calculate_quality(
                            chunk_text, title, url, "Claude Code"
                        )
                        topics = production_crawler.extract_topics(
                            chunk_text, title, "Claude Code"
                        )
                        embedding = await production_crawler.generate_embedding(chunk_text)
                        
                        if embedding:
                            chunk_data = {
                                'source_name': 'Claude Code',
                                'source_url': url,
                                'title': title,
                                'content': chunk_text,
                                'chunk_index': chunk_index,
                                'total_chunks': len(text_chunks),
                                'quality_score': quality_score,
                                'topics': topics,
                                'embedding': embedding
                            }
                            
                            if production_crawler.store_chunk(chunk_data):
                                chunks_created += 1
                    
                    # Update cache
                    self.incremental.update_cache(url, url_data['hash'], len(text_chunks))
                
            except Exception as e:
                logfire.error("Failed to process changed URL", url=url, error=str(e))
        
        # Mark incremental crawl complete
        self.incremental.mark_crawl_complete(
            "Claude Code", "incremental", len(changed_urls), chunks_created
        )
        
        return chunks_created


# Test the incremental crawler
if __name__ == "__main__":
    incremental = IncrementalCrawler()
    
    # Show statistics
    stats = incremental.get_crawl_statistics("Claude Code")
    print("\n📊 Claude Code Crawl Statistics:")
    print(f"   Total URLs tracked: {stats['total_urls']}")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Last full crawl: {stats['last_full_crawl']}")
    print(f"   Last incremental: {stats['last_incremental']}")
    
    # Check if full recrawl needed
    needs_full = incremental.should_full_recrawl("Claude Code")
    print(f"\n   Needs full recrawl: {needs_full}")