#!/usr/bin/env python3
"""
Crawl4AI Integration for Ptolemies Knowledge Base

This module provides integration with the Crawl4AI MCP server
for intelligent web crawling and content ingestion.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

class CrawlManager:
    """Manager for crawl operations via Crawl4AI MCP."""
    
    def __init__(self, mcp_endpoint: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize the crawl manager.
        
        Args:
            mcp_endpoint: The endpoint for the Crawl4AI MCP server
            api_key: API key for authentication
        """
        # Use environment variables if not provided
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        self.mcp_endpoint = mcp_endpoint or os.getenv("MCP_CRAWL4AI_ENDPOINT")
        self.api_key = api_key or os.getenv("MCP_CRAWL4AI_API_KEY")
        
        if not self.mcp_endpoint:
            raise ValueError("Crawl4AI MCP endpoint not configured")
        
        self.logger = logging.getLogger("ptolemies.integrations.crawl4ai")
    
    async def crawl_url(self, url: str, depth: int = 2, **kwargs) -> Dict[str, Any]:
        """Crawl a URL and its linked pages.
        
        Args:
            url: The URL to crawl
            depth: How deep to follow links (default: 2)
            **kwargs: Additional crawl parameters
                - extract_code: Whether to extract code blocks
                - extract_tables: Whether to extract tables
                - max_pages: Maximum pages to crawl
                - respect_robots_txt: Whether to respect robots.txt
                - delay_ms: Delay between requests
                - user_agent: User agent to use
                - tags: Tags to apply to knowledge items
                - category: Category for knowledge items
                
        Returns:
            Dictionary with crawl results
        """
        self.logger.info(f"Crawling URL: {url} with depth {depth}")
        
        # Prepare MCP request
        request = {
            "tool": "crawl4ai",
            "operation": "crawl",
            "parameters": {
                "url": url,
                "depth": depth,
                "max_pages": kwargs.get("max_pages", 100),
                "extract_code": kwargs.get("extract_code", True),
                "extract_tables": kwargs.get("extract_tables", True),
                "respect_robots_txt": kwargs.get("respect_robots_txt", True),
                "delay_ms": kwargs.get("delay_ms", 1000),
                "user_agent": kwargs.get("user_agent", "Ptolemies Knowledge Crawler/1.0")
            },
            "metadata": {
                "request_id": f"ptolemies-crawl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Make request to MCP server
        try:
            # In a real implementation, this would use httpx or similar
            # to make the actual request to the MCP server
            self.logger.debug(f"Sending request to Crawl4AI MCP: {json.dumps(request)}")
            
            # This is a placeholder for the actual HTTP request
            # result = await self._make_mcp_request(request)
            
            # Simulate response for demonstration purposes
            result = {
                "pages": [
                    {"url": url, "title": "Example Page", "content": "Example content..."},
                    {"url": f"{url}/page1", "title": "Page 1", "content": "More content..."},
                ],
                "stats": {
                    "pages_crawled": 2,
                    "total_content_bytes": 5000,
                    "time_ms": 1500
                }
            }
            
            self.logger.info(f"Crawl completed: {result['stats']['pages_crawled']} pages crawled")
            return result
            
        except Exception as e:
            self.logger.error(f"Error during crawl: {e}")
            raise
    
    async def process_results(self, results: Dict[str, Any]) -> List[str]:
        """Process crawl results and store in the knowledge base.
        
        Args:
            results: Crawl results from crawl_url()
            
        Returns:
            List of created knowledge item IDs
        """
        from ptolemies.client import PtolemiesClient
        
        client = PtolemiesClient()
        item_ids = []
        
        self.logger.info(f"Processing {len(results.get('pages', []))} crawled pages")
        
        for page in results.get("pages", []):
            # Create knowledge item from page
            try:
                item_id = client.add_item(
                    title=page.get("title", "Untitled"),
                    content=page.get("content", ""),
                    source=page.get("url", ""),
                    content_type="text/html",
                    metadata={
                        "crawl_timestamp": datetime.now().isoformat(),
                        "page_metadata": page.get("metadata", {})
                    }
                )
                item_ids.append(item_id)
                self.logger.debug(f"Created knowledge item: {item_id}")
            except Exception as e:
                self.logger.error(f"Error storing knowledge item: {e}")
        
        self.logger.info(f"Processed {len(item_ids)} knowledge items")
        return item_ids
    
    async def _make_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to MCP server.
        
        This is a private method that would handle the actual HTTP request
        to the MCP server in a real implementation.
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await client.post(
                self.mcp_endpoint, 
                json=request,
                headers=headers
            )
            response.raise_for_status()
            return response.json()


class CrawlScheduler:
    """Scheduler for regular crawl operations."""
    
    def __init__(self):
        """Initialize the crawl scheduler."""
        self.schedules = []
        self.logger = logging.getLogger("ptolemies.integrations.crawl4ai.scheduler")
        self.running = False
    
    def add_scheduled_crawl(self, name: str, urls: List[str], schedule: str, **kwargs):
        """Add a scheduled crawl.
        
        Args:
            name: Name of the schedule
            urls: List of URLs to crawl
            schedule: Cron-style schedule (e.g., "0 0 * * *" for daily at midnight)
            **kwargs: Additional parameters for crawl_url()
        """
        self.schedules.append({
            "name": name,
            "urls": urls,
            "schedule": schedule,
            "parameters": kwargs
        })
        self.logger.info(f"Added scheduled crawl '{name}' with {len(urls)} URLs on schedule {schedule}")
    
    def start(self):
        """Start the scheduler."""
        import asyncio
        import aiocron
        
        self.running = True
        self.logger.info(f"Starting crawl scheduler with {len(self.schedules)} schedules")
        
        loop = asyncio.get_event_loop()
        
        for schedule in self.schedules:
            # Create cron job for each schedule
            aiocron.crontab(
                schedule["schedule"],
                func=self._run_scheduled_crawl,
                args=(schedule,),
                loop=loop
            )
        
        self.logger.info("Crawl scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self.logger.info("Crawl scheduler stopped")
    
    async def _run_scheduled_crawl(self, schedule: Dict[str, Any]):
        """Run a scheduled crawl.
        
        This is called by the scheduler when a schedule is triggered.
        """
        if not self.running:
            return
        
        crawl_manager = CrawlManager()
        self.logger.info(f"Running scheduled crawl '{schedule['name']}'")
        
        for url in schedule["urls"]:
            try:
                result = await crawl_manager.crawl_url(url, **schedule["parameters"])
                await crawl_manager.process_results(result)
                self.logger.info(f"Completed scheduled crawl for {url}")
            except Exception as e:
                self.logger.error(f"Error in scheduled crawl for {url}: {e}")