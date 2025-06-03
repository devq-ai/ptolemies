#!/usr/bin/env python3
"""
Display crawl targets for Ptolemies Knowledge Base

This script reads and displays the crawl targets configured for the system.
"""

import json
import os
import sys
from pathlib import Path

def main():
    """Main entry point."""
    # Find the crawl targets JSON file
    root_dir = Path(__file__).parent
    json_path = os.path.join(root_dir, "data", "crawl_targets.json")
    
    if not os.path.exists(json_path):
        print(f"Error: Crawl targets JSON file not found: {json_path}")
        return 1
    
    # Load the targets
    with open(json_path, "r") as f:
        data = json.load(f)
    
    targets = data.get("targets", [])
    schedules = data.get("schedules", [])
    
    # Display targets
    print("===== Ptolemies Knowledge Base Crawl Targets =====")
    print(f"Found {len(targets)} targets:")
    print()
    
    for i, target in enumerate(targets, 1):
        name = target.get("name", "Unnamed Target")
        url = target.get("url", "No URL")
        depth = target.get("depth", "?")
        category = target.get("category", "Uncategorized")
        priority = target.get("priority", "medium")
        tags = ", ".join(target.get("tags", []))
        
        print(f"{i}. {name}")
        print(f"   URL: {url}")
        print(f"   Depth: {depth}")
        print(f"   Category: {category}")
        print(f"   Priority: {priority}")
        if tags:
            print(f"   Tags: {tags}")
        print()
    
    # Display schedules
    print("===== Crawl Schedules =====")
    print(f"Found {len(schedules)} schedules:")
    print()
    
    for i, schedule in enumerate(schedules, 1):
        name = schedule.get("name", "Unnamed Schedule")
        schedule_pattern = schedule.get("schedule", "?")
        urls = schedule.get("urls", [])
        depth = schedule.get("depth", "?")
        category = schedule.get("category", "Uncategorized")
        tags = ", ".join(schedule.get("tags", []))
        
        print(f"{i}. {name}")
        print(f"   Schedule: {schedule_pattern}")
        print(f"   URLs: {len(urls)}")
        for url in urls:
            print(f"     - {url}")
        print(f"   Depth: {depth}")
        print(f"   Category: {category}")
        if tags:
            print(f"   Tags: {tags}")
        print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())