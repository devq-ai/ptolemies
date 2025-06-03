#!/usr/bin/env python3
"""
MCP Adapter for Crawl4AI Integration

Provides a MCP-compatible interface for the Crawl4AI integration.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple

from .crawler import CrawlManager, CrawlScheduler

class Crawl4AIMCPAdapter:
    """MCP Adapter for Crawl4AI functionality."""
    
    def __init__(self):
        """Initialize the MCP adapter."""
        self.logger = logging.getLogger("ptolemies.integrations.crawl4ai.mcp")
        self.crawl_manager = CrawlManager()
        self.scheduler = CrawlScheduler()
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request.
        
        Args:
            request: The MCP request
            
        Returns:
            Response dictionary
        """
        operation = request.get("operation")
        parameters = request.get("parameters", {})
        
        try:
            if operation == "crawl":
                return await self._handle_crawl(parameters)
            elif operation == "schedule":
                return await self._handle_schedule(parameters)
            elif operation == "list_schedules":
                return await self._handle_list_schedules(parameters)
            elif operation == "delete_schedule":
                return await self._handle_delete_schedule(parameters)
            else:
                return self._error_response(f"Unknown operation: {operation}")
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            return self._error_response(str(e))
    
    async def _handle_crawl(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a crawl operation.
        
        Args:
            parameters: The parameters for the crawl
            
        Returns:
            Response with crawl results
        """
        url = parameters.get("url")
        
        if not url:
            return self._error_response("URL is required")
        
        try:
            depth = int(parameters.get("depth", 2))
            max_pages = int(parameters.get("max_pages", 100))
            delay_ms = int(parameters.get("delay_ms", 1000))
        except ValueError:
            return self._error_response("Invalid numeric parameter")
        
        extract_code = parameters.get("extract_code", True)
        extract_tables = parameters.get("extract_tables", True)
        respect_robots_txt = parameters.get("respect_robots_txt", True)
        user_agent = parameters.get("user_agent", "Ptolemies Knowledge Crawler/1.0")
        
        # Execute the crawl
        try:
            result = await self.crawl_manager.crawl_url(
                url=url,
                depth=depth,
                max_pages=max_pages,
                extract_code=extract_code,
                extract_tables=extract_tables,
                respect_robots_txt=respect_robots_txt,
                delay_ms=delay_ms,
                user_agent=user_agent
            )
            
            # Process the results if requested
            process_results = parameters.get("process_results", True)
            if process_results:
                item_ids = await self.crawl_manager.process_results(result)
                result["knowledge_items"] = item_ids
            
            return {
                "result": result,
                "metadata": {
                    "url": url,
                    "depth": depth,
                    "timestamp": datetime.now().isoformat(),
                    "pages_crawled": len(result.get("pages", [])),
                }
            }
        except Exception as e:
            self.logger.error(f"Error during crawl operation: {e}")
            return self._error_response(f"Crawl failed: {str(e)}")
    
    async def _handle_schedule(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a schedule operation.
        
        Args:
            parameters: The parameters for scheduling
            
        Returns:
            Response with schedule information
        """
        name = parameters.get("name")
        urls = parameters.get("urls")
        schedule = parameters.get("schedule")
        
        if not name:
            return self._error_response("Schedule name is required")
        if not urls:
            return self._error_response("URLs are required")
        if not schedule:
            return self._error_response("Schedule is required")
        
        if isinstance(urls, str):
            urls = [urls]
        
        # Add the schedule
        try:
            self.scheduler.add_scheduled_crawl(
                name=name,
                urls=urls,
                schedule=schedule,
                depth=parameters.get("depth", 2),
                max_pages=parameters.get("max_pages", 100),
                extract_code=parameters.get("extract_code", True),
                extract_tables=parameters.get("extract_tables", True),
                respect_robots_txt=parameters.get("respect_robots_txt", True),
                delay_ms=parameters.get("delay_ms", 1000),
                user_agent=parameters.get("user_agent", "Ptolemies Knowledge Crawler/1.0"),
                tags=parameters.get("tags", []),
                category=parameters.get("category", "")
            )
            
            # Start the scheduler if it's not already running
            if not self.scheduler.running:
                self.scheduler.start()
            
            return {
                "result": {
                    "status": "scheduled",
                    "name": name,
                    "urls": urls,
                    "schedule": schedule
                }
            }
        except Exception as e:
            self.logger.error(f"Error scheduling crawl: {e}")
            return self._error_response(f"Scheduling failed: {str(e)}")
    
    async def _handle_list_schedules(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a list_schedules operation.
        
        Args:
            parameters: The parameters (unused)
            
        Returns:
            Response with list of schedules
        """
        try:
            return {
                "result": {
                    "schedules": [
                        {
                            "name": schedule["name"],
                            "urls": schedule["urls"],
                            "schedule": schedule["schedule"]
                        }
                        for schedule in self.scheduler.schedules
                    ],
                    "count": len(self.scheduler.schedules),
                    "running": self.scheduler.running
                }
            }
        except Exception as e:
            self.logger.error(f"Error listing schedules: {e}")
            return self._error_response(f"Listing failed: {str(e)}")
    
    async def _handle_delete_schedule(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a delete_schedule operation.
        
        Args:
            parameters: The parameters with name of schedule to delete
            
        Returns:
            Response with deletion status
        """
        name = parameters.get("name")
        
        if not name:
            return self._error_response("Schedule name is required")
        
        try:
            # Find and remove the schedule
            for i, schedule in enumerate(self.scheduler.schedules):
                if schedule["name"] == name:
                    del self.scheduler.schedules[i]
                    self.logger.info(f"Deleted schedule '{name}'")
                    return {
                        "result": {
                            "status": "deleted",
                            "name": name
                        }
                    }
            
            return self._error_response(f"Schedule '{name}' not found")
        except Exception as e:
            self.logger.error(f"Error deleting schedule: {e}")
            return self._error_response(f"Deletion failed: {str(e)}")
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Create an error response.
        
        Args:
            message: Error message
            
        Returns:
            Formatted error response
        """
        return {
            "error": {
                "message": message,
                "code": "crawl4ai_error"
            }
        }