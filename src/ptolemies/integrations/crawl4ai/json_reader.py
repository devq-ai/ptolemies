#!/usr/bin/env python3
"""
JSON-based crawl target reader for Ptolemies

This module provides a way to read crawl targets from a JSON file
rather than parsing the Markdown file, which simplifies implementation.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

class CrawlTargetReader:
    """Reader for crawl targets from JSON file."""
    
    def __init__(self, json_path: Optional[str] = None):
        """Initialize the reader.
        
        Args:
            json_path: Path to the JSON file (optional)
        """
        if json_path is None:
            # Default to data/crawl_targets.json in the project root
            root_dir = Path(__file__).parent.parent.parent
            json_path = os.path.join(root_dir, "data", "crawl_targets.json")
        
        self.json_path = json_path
        self._data = None
    
    def load(self) -> Dict[str, Any]:
        """Load the targets from the JSON file.
        
        Returns:
            Dictionary with targets and schedules
        """
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"Crawl targets JSON file not found: {self.json_path}")
        
        with open(self.json_path, "r") as f:
            self._data = json.load(f)
        
        return self._data
    
    def get_targets(self) -> List[Dict[str, Any]]:
        """Get all targets.
        
        Returns:
            List of target dictionaries
        """
        if self._data is None:
            self.load()
        
        return self._data.get("targets", [])
    
    def get_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules.
        
        Returns:
            List of schedule dictionaries
        """
        if self._data is None:
            self.load()
        
        return self._data.get("schedules", [])
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration.
        
        Returns:
            Dictionary with default configuration
        """
        if self._data is None:
            self.load()
        
        return self._data.get("default_config", {})
    
    def get_targets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get targets by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of matching targets
        """
        if self._data is None:
            self.load()
        
        return [t for t in self.get_targets() if t.get("category") == category]
    
    def get_targets_by_priority(self, priority: str) -> List[Dict[str, Any]]:
        """Get targets by priority.
        
        Args:
            priority: Priority to filter by
            
        Returns:
            List of matching targets
        """
        if self._data is None:
            self.load()
        
        return [t for t in self.get_targets() if t.get("priority") == priority]
    
    def get_target_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a target by name.
        
        Args:
            name: Target name
            
        Returns:
            Target dictionary or None if not found
        """
        if self._data is None:
            self.load()
        
        for target in self.get_targets():
            if target.get("name") == name:
                return target
        
        return None
    
    def get_schedule_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a schedule by name.
        
        Args:
            name: Schedule name
            
        Returns:
            Schedule dictionary or None if not found
        """
        if self._data is None:
            self.load()
        
        for schedule in self.get_schedules():
            if schedule.get("name") == name:
                return schedule
        
        return None
    
    def get_all_urls(self) -> List[str]:
        """Get all URLs from all targets.
        
        Returns:
            List of all URLs
        """
        if self._data is None:
            self.load()
        
        return [t.get("url") for t in self.get_targets() if "url" in t]