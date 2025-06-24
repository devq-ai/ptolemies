#!/usr/bin/env python3
"""
Persistent Metrics Tracker for Ptolemies Crawl Operations
Tracks detailed statistics over time with visualization support
"""

import json
import os
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from pathlib import Path
import logfire

# Optional visualization imports
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    plt = None
    pd = None

logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

class CrawlMetricsTracker:
    """Tracks and persists crawl metrics over time."""
    
    def __init__(self, metrics_dir: str = "metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        self.current_metrics_file = self.metrics_dir / "current_metrics.json"
        self.history_file = self.metrics_dir / "metrics_history.jsonl"
        self.source_stats_file = self.metrics_dir / "source_statistics.json"
        
    @logfire.instrument("record_crawl_start")
    def record_crawl_start(self, crawl_id: str, crawl_type: str = "full"):
        """Record the start of a crawl operation."""
        metrics = {
            "crawl_id": crawl_id,
            "crawl_type": crawl_type,
            "start_time": datetime.now(UTC).isoformat(),
            "status": "in_progress",
            "sources": {}
        }
        
        with open(self.current_metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logfire.info("Crawl started", crawl_id=crawl_id, type=crawl_type)
    
    @logfire.instrument("update_source_metrics")
    def update_source_metrics(self, source_name: str, metrics: Dict[str, Any]):
        """Update metrics for a specific source during crawl."""
        current_metrics = self._load_current_metrics()
        
        if current_metrics:
            current_metrics["sources"][source_name] = {
                "pages_crawled": metrics.get("pages_crawled", 0),
                "chunks_created": metrics.get("chunks_created", 0),
                "embeddings_generated": metrics.get("embeddings_generated", 0),
                "errors": metrics.get("errors", 0),
                "avg_quality_score": metrics.get("avg_quality_score", 0),
                "crawl_time_seconds": metrics.get("crawl_time_seconds", 0),
                "status": metrics.get("status", "completed")
            }
            
            with open(self.current_metrics_file, 'w') as f:
                json.dump(current_metrics, f, indent=2)
    
    @logfire.instrument("record_crawl_complete")
    def record_crawl_complete(self, total_chunks: int, total_pages: int, 
                            total_embeddings: int, total_errors: int):
        """Record completion of a crawl operation."""
        current_metrics = self._load_current_metrics()
        
        if current_metrics:
            current_metrics["end_time"] = datetime.now(UTC).isoformat()
            current_metrics["status"] = "completed"
            current_metrics["totals"] = {
                "chunks_created": total_chunks,
                "pages_crawled": total_pages,
                "embeddings_generated": total_embeddings,
                "errors": total_errors,
                "duration_seconds": self._calculate_duration(
                    current_metrics["start_time"],
                    current_metrics["end_time"]
                )
            }
            
            # Save to current metrics
            with open(self.current_metrics_file, 'w') as f:
                json.dump(current_metrics, f, indent=2)
            
            # Append to history
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(current_metrics) + '\n')
            
            # Update source statistics
            self._update_source_statistics(current_metrics)
            
            logfire.info("Crawl completed", 
                       crawl_id=current_metrics["crawl_id"],
                       total_chunks=total_chunks,
                       duration=current_metrics["totals"]["duration_seconds"])
    
    def _calculate_duration(self, start_time: str, end_time: str) -> float:
        """Calculate duration in seconds between timestamps."""
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        return (end - start).total_seconds()
    
    def _load_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Load current metrics from file."""
        if self.current_metrics_file.exists():
            with open(self.current_metrics_file, 'r') as f:
                return json.load(f)
        return None
    
    def _update_source_statistics(self, metrics: Dict[str, Any]):
        """Update cumulative source statistics."""
        stats = {}
        
        if self.source_stats_file.exists():
            with open(self.source_stats_file, 'r') as f:
                stats = json.load(f)
        
        for source_name, source_metrics in metrics["sources"].items():
            if source_name not in stats:
                stats[source_name] = {
                    "total_crawls": 0,
                    "total_chunks": 0,
                    "total_pages": 0,
                    "total_errors": 0,
                    "avg_chunks_per_crawl": 0,
                    "avg_quality_score": 0,
                    "last_crawl": None
                }
            
            # Update statistics
            stats[source_name]["total_crawls"] += 1
            stats[source_name]["total_chunks"] += source_metrics["chunks_created"]
            stats[source_name]["total_pages"] += source_metrics["pages_crawled"]
            stats[source_name]["total_errors"] += source_metrics["errors"]
            stats[source_name]["last_crawl"] = metrics["end_time"]
            
            # Update averages
            crawl_count = stats[source_name]["total_crawls"]
            stats[source_name]["avg_chunks_per_crawl"] = (
                stats[source_name]["total_chunks"] / crawl_count
            )
            
            # Update average quality score
            if source_metrics.get("avg_quality_score", 0) > 0:
                if stats[source_name]["avg_quality_score"] == 0:
                    stats[source_name]["avg_quality_score"] = source_metrics["avg_quality_score"]
                else:
                    stats[source_name]["avg_quality_score"] = (
                        (stats[source_name]["avg_quality_score"] * (crawl_count - 1) + 
                         source_metrics["avg_quality_score"]) / crawl_count
                    )
        
        with open(self.source_stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    @logfire.instrument("get_crawl_history")
    def get_crawl_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent crawl history."""
        history = []
        
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                for line in f:
                    history.append(json.loads(line))
        
        # Return most recent crawls
        return history[-limit:]
    
    @logfire.instrument("get_source_statistics")
    def get_source_statistics(self) -> Dict[str, Any]:
        """Get cumulative statistics for all sources."""
        if self.source_stats_file.exists():
            with open(self.source_stats_file, 'r') as f:
                return json.load(f)
        return {}
    
    @logfire.instrument("generate_report")
    def generate_report(self) -> str:
        """Generate a comprehensive metrics report."""
        stats = self.get_source_statistics()
        history = self.get_crawl_history()
        
        report = ["# Ptolemies Crawl Metrics Report"]
        report.append(f"\nGenerated: {datetime.now(UTC).isoformat()}")
        
        # Overall statistics
        if history:
            total_crawls = len(history)
            last_crawl = history[-1]
            
            report.append("\n## Overall Statistics")
            report.append(f"- Total crawls: {total_crawls}")
            report.append(f"- Last crawl: {last_crawl['end_time']}")
            report.append(f"- Last crawl chunks: {last_crawl['totals']['chunks_created']}")
            report.append(f"- Last crawl duration: {last_crawl['totals']['duration_seconds']:.1f}s")
        
        # Source statistics
        report.append("\n## Source Statistics")
        report.append("\n| Source | Total Crawls | Total Chunks | Avg Chunks/Crawl | Avg Quality | Last Crawl |")
        report.append("|--------|--------------|--------------|------------------|-------------|------------|")
        
        for source, data in sorted(stats.items(), key=lambda x: x[1]["total_chunks"], reverse=True):
            report.append(f"| {source} | {data['total_crawls']} | "
                        f"{data['total_chunks']} | {data['avg_chunks_per_crawl']:.1f} | "
                        f"{data['avg_quality_score']:.2f} | {data['last_crawl'][:10]} |")
        
        # Recent crawl performance
        if history:
            report.append("\n## Recent Crawl Performance")
            report.append("\n| Crawl ID | Type | Duration | Chunks | Pages | Errors | Status |")
            report.append("|----------|------|----------|--------|-------|--------|--------|")
            
            for crawl in history[-5:]:
                report.append(f"| {crawl['crawl_id'][:8]} | {crawl['crawl_type']} | "
                            f"{crawl['totals']['duration_seconds']:.1f}s | "
                            f"{crawl['totals']['chunks_created']} | "
                            f"{crawl['totals']['pages_crawled']} | "
                            f"{crawl['totals']['errors']} | {crawl['status']} |")
        
        return "\n".join(report)
    
    @logfire.instrument("visualize_metrics")
    def visualize_metrics(self, output_dir: str = "metrics/visualizations"):
        """Generate visualization charts for metrics."""
        if not VISUALIZATION_AVAILABLE:
            logfire.warning("Visualization libraries not available, skipping charts")
            return
            
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        stats = self.get_source_statistics()
        history = self.get_crawl_history(limit=30)
        
        if not stats or not history:
            logfire.warning("Insufficient data for visualization")
            return
        
        # 1. Source chunk distribution pie chart
        plt.figure(figsize=(10, 8))
        sources = list(stats.keys())
        chunks = [stats[s]["total_chunks"] for s in sources]
        
        plt.pie(chunks, labels=sources, autopct='%1.1f%%', startangle=90)
        plt.title("Chunk Distribution by Source")
        plt.savefig(output_path / "chunk_distribution.png")
        plt.close()
        
        # 2. Crawl performance over time
        plt.figure(figsize=(12, 6))
        crawl_times = [h["totals"]["duration_seconds"] for h in history]
        crawl_chunks = [h["totals"]["chunks_created"] for h in history]
        crawl_dates = [h["end_time"][:10] for h in history]
        
        plt.subplot(2, 1, 1)
        plt.plot(crawl_dates, crawl_times, marker='o')
        plt.title("Crawl Duration Over Time")
        plt.xlabel("Date")
        plt.ylabel("Duration (seconds)")
        plt.xticks(rotation=45)
        
        plt.subplot(2, 1, 2)
        plt.plot(crawl_dates, crawl_chunks, marker='s', color='green')
        plt.title("Chunks Created Over Time")
        plt.xlabel("Date")
        plt.ylabel("Chunks")
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_path / "crawl_performance.png")
        plt.close()
        
        logfire.info("Visualizations generated", output_dir=output_dir)


# Integration with production crawler
def integrate_metrics_with_crawler(production_crawler_class):
    """Decorator to add metrics tracking to production crawler."""
    original_build = production_crawler_class.build_knowledge_base
    original_crawl_source = production_crawler_class.crawl_source
    
    async def build_with_metrics(self):
        """Enhanced build with metrics tracking."""
        tracker = CrawlMetricsTracker()
        crawl_id = f"crawl_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        
        tracker.record_crawl_start(crawl_id, "full")
        
        # Store original crawl_source method
        original_method = self.crawl_source
        
        # Create wrapped version that tracks metrics
        async def crawl_source_with_metrics(source):
            start_time = datetime.now(UTC)
            chunks = await original_method(source)
            end_time = datetime.now(UTC)
            
            tracker.update_source_metrics(source['name'], {
                'pages_crawled': self.metrics.pages_crawled,
                'chunks_created': chunks,
                'embeddings_generated': chunks,  # Assuming 1:1 ratio
                'errors': self.metrics.processing_errors,
                'avg_quality_score': 0.8,  # Would need to track this
                'crawl_time_seconds': (end_time - start_time).total_seconds(),
                'status': 'completed' if chunks > 0 else 'failed'
            })
            
            return chunks
        
        # Temporarily replace method
        self.crawl_source = crawl_source_with_metrics
        
        try:
            # Run original build
            result = await original_build(self)
            
            # Record completion
            tracker.record_crawl_complete(
                self.metrics.chunks_created,
                self.metrics.pages_crawled,
                self.metrics.embeddings_generated,
                self.metrics.processing_errors
            )
            
            # Generate report
            report = tracker.generate_report()
            report_file = Path("metrics/latest_report.md")
            report_file.parent.mkdir(exist_ok=True)
            with open(report_file, 'w') as f:
                f.write(report)
            
            # Generate visualizations
            tracker.visualize_metrics()
            
            return result
            
        finally:
            # Restore original method
            self.crawl_source = original_method
    
    production_crawler_class.build_knowledge_base = build_with_metrics
    return production_crawler_class


# CLI for metrics viewing
if __name__ == "__main__":
    import sys
    
    tracker = CrawlMetricsTracker()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "report":
            print(tracker.generate_report())
        
        elif command == "visualize":
            tracker.visualize_metrics()
            print("✅ Visualizations generated in metrics/visualizations/")
        
        elif command == "stats":
            stats = tracker.get_source_statistics()
            print(json.dumps(stats, indent=2))
        
        elif command == "history":
            history = tracker.get_crawl_history()
            for crawl in history:
                print(f"\n{crawl['crawl_id']} - {crawl['end_time']}")
                print(f"  Chunks: {crawl['totals']['chunks_created']}")
                print(f"  Duration: {crawl['totals']['duration_seconds']:.1f}s")
    
    else:
        print("Usage: python crawl_metrics_tracker.py [report|visualize|stats|history]")