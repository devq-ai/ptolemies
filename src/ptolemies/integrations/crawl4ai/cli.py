#!/usr/bin/env python3
"""
CLI for Ptolemies Crawl4AI integration

Command-line interface for managing crawls and schedules.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import List, Optional, Dict, Any
from datetime import datetime

from .crawler import CrawlManager, CrawlScheduler


def setup_logging(verbose: bool = False):
    """Set up logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


async def crawl_url(args):
    """Handle the crawl-url command."""
    manager = CrawlManager()
    
    # Convert comma-separated tags to list
    tags = args.tags.split(",") if args.tags else []
    
    try:
        result = await manager.crawl_url(
            url=args.url,
            depth=args.depth,
            max_pages=args.max_pages,
            extract_code=args.extract_code,
            extract_tables=args.extract_tables,
            respect_robots_txt=args.respect_robots,
            delay_ms=args.delay,
            user_agent=args.user_agent,
            tags=tags,
            category=args.category
        )
        
        print(f"Crawl completed: {len(result.get('pages', []))} pages crawled")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to {args.output}")
        
        if not args.skip_processing:
            item_ids = await manager.process_results(result)
            print(f"Created {len(item_ids)} knowledge items")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


async def list_targets(args):
    """Handle the list-targets command."""
    import yaml
    from pathlib import Path
    
    try:
        targets_file = Path(__file__).parent.parent.parent / "crawl_targets.md"
        if not targets_file.exists():
            print("Error: crawl_targets.md file not found")
            return 1
        
        with open(targets_file, "r") as f:
            content = f.read()
        
        # Extract YAML blocks
        yaml_blocks = []
        in_yaml = False
        current_block = []
        
        for line in content.split("\n"):
            if line.strip() == "```yaml":
                in_yaml = True
                current_block = []
            elif line.strip() == "```" and in_yaml:
                in_yaml = False
                if current_block:
                    yaml_blocks.append("\n".join(current_block))
            elif in_yaml:
                current_block.append(line)
        
        # Parse YAML blocks
        targets = []
        for block in yaml_blocks:
            try:
                data = yaml.safe_load(block)
                if isinstance(data, dict) and "url" in data:
                    targets.append(data)
            except yaml.YAMLError:
                pass
        
        # Print targets
        print(f"Found {len(targets)} crawl targets:")
        for i, target in enumerate(targets, 1):
            url = target.get("url", "Unknown")
            depth = target.get("depth", "?")
            tags = ", ".join(target.get("tags", []))
            category = target.get("category", "Uncategorized")
            
            print(f"{i}. {url}")
            print(f"   Depth: {depth}")
            print(f"   Category: {category}")
            if tags:
                print(f"   Tags: {tags}")
            print()
        
        if args.export:
            with open(args.export, "w") as f:
                json.dump(targets, f, indent=2)
            print(f"Exported targets to {args.export}")
            
    except Exception as e:
        print(f"Error listing targets: {e}")
        return 1
    
    return 0


async def crawl_targets(args):
    """Handle the crawl-targets command."""
    import yaml
    from pathlib import Path
    
    try:
        targets_file = Path(__file__).parent.parent.parent / "crawl_targets.md"
        if not targets_file.exists():
            print("Error: crawl_targets.md file not found")
            return 1
        
        with open(targets_file, "r") as f:
            content = f.read()
        
        # Extract YAML blocks
        yaml_blocks = []
        in_yaml = False
        current_block = []
        
        for line in content.split("\n"):
            if line.strip() == "```yaml":
                in_yaml = True
                current_block = []
            elif line.strip() == "```" and in_yaml:
                in_yaml = False
                if current_block:
                    yaml_blocks.append("\n".join(current_block))
            elif in_yaml:
                current_block.append(line)
        
        # Parse YAML blocks
        targets = []
        for block in yaml_blocks:
            try:
                data = yaml.safe_load(block)
                if isinstance(data, dict) and "url" in data:
                    targets.append(data)
            except yaml.YAMLError:
                pass
        
        # Filter targets
        if args.target:
            targets = [t for t in targets if t.get("url") == args.target]
        elif args.category:
            targets = [t for t in targets if t.get("category") == args.category]
        
        if not targets:
            print("No matching targets found")
            return 1
        
        print(f"Crawling {len(targets)} targets:")
        
        manager = CrawlManager()
        for i, target in enumerate(targets, 1):
            url = target.get("url")
            depth = target.get("depth", 2)
            
            print(f"[{i}/{len(targets)}] Crawling {url} (depth {depth})")
            
            try:
                result = await manager.crawl_url(
                    url=url,
                    depth=depth,
                    max_pages=target.get("max_pages", 100),
                    extract_code=target.get("extract_code", True),
                    extract_tables=target.get("extract_tables", True),
                    respect_robots_txt=target.get("respect_robots_txt", True),
                    delay_ms=target.get("delay_ms", 1000),
                    user_agent=target.get("user_agent", "Ptolemies Knowledge Crawler/1.0"),
                    tags=target.get("tags", []),
                    category=target.get("category", "")
                )
                
                print(f"  Crawled {len(result.get('pages', []))} pages")
                
                if not args.skip_processing:
                    item_ids = await manager.process_results(result)
                    print(f"  Created {len(item_ids)} knowledge items")
                
                if args.output:
                    output_file = f"{args.output}/crawl_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                    os.makedirs(args.output, exist_ok=True)
                    with open(output_file, 'w') as f:
                        json.dump(result, f, indent=2)
                    print(f"  Results saved to {output_file}")
                
            except Exception as e:
                print(f"  Error crawling {url}: {e}")
                if not args.continue_on_error:
                    return 1
        
        print("Crawl completed successfully")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Ptolemies Crawl4AI Integration CLI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # crawl-url command
    crawl_parser = subparsers.add_parser("crawl-url", help="Crawl a specific URL")
    crawl_parser.add_argument("url", help="URL to crawl")
    crawl_parser.add_argument("--depth", type=int, default=2, help="Crawl depth")
    crawl_parser.add_argument("--max-pages", type=int, default=100, help="Maximum pages to crawl")
    crawl_parser.add_argument("--extract-code", action="store_true", help="Extract code blocks")
    crawl_parser.add_argument("--extract-tables", action="store_true", help="Extract tables")
    crawl_parser.add_argument("--respect-robots", action="store_true", help="Respect robots.txt")
    crawl_parser.add_argument("--delay", type=int, default=1000, help="Delay between requests (ms)")
    crawl_parser.add_argument("--user-agent", default="Ptolemies Knowledge Crawler/1.0", help="User agent")
    crawl_parser.add_argument("--tags", help="Comma-separated list of tags")
    crawl_parser.add_argument("--category", help="Category for the content")
    crawl_parser.add_argument("--output", help="Output file for crawl results")
    crawl_parser.add_argument("--skip-processing", action="store_true", help="Skip processing results")
    
    # list-targets command
    list_targets_parser = subparsers.add_parser("list-targets", help="List crawl targets from crawl_targets.md")
    list_targets_parser.add_argument("--export", help="Export targets to JSON file")
    
    # crawl-targets command
    crawl_targets_parser = subparsers.add_parser("crawl-targets", help="Crawl targets from crawl_targets.md")
    crawl_targets_parser.add_argument("--target", help="Specific target URL to crawl")
    crawl_targets_parser.add_argument("--category", help="Category of targets to crawl")
    crawl_targets_parser.add_argument("--output", help="Output directory for crawl results")
    crawl_targets_parser.add_argument("--skip-processing", action="store_true", help="Skip processing results")
    crawl_targets_parser.add_argument("--continue-on-error", action="store_true", help="Continue on error")
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    if args.command == "crawl-url":
        return asyncio.run(crawl_url(args))
    elif args.command == "list-targets":
        return asyncio.run(list_targets(args))
    elif args.command == "crawl-targets":
        return asyncio.run(crawl_targets(args))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())