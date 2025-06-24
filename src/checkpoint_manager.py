#!/usr/bin/env python3
"""
Checkpoint Manager for Long-Running Operations
Saves progress periodically to enable recovery from interruptions
"""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
from pathlib import Path
import logfire

logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

class CheckpointManager:
    """Manages checkpoints during long crawling operations."""
    
    def __init__(self, checkpoint_dir: str = "checkpoints", save_interval: int = 30):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.save_interval = save_interval  # seconds
        self.last_save = 0
        self.operation_id = None
        self.checkpoint_data = {}
        
    @logfire.instrument("start_operation")
    def start_operation(self, operation_name: str, sources: List[str]) -> str:
        """Start a new checkpointed operation."""
        self.operation_id = f"{operation_name}_{int(time.time())}"
        
        self.checkpoint_data = {
            "operation_id": self.operation_id,
            "operation_name": operation_name,
            "start_time": datetime.now(UTC).isoformat(),
            "status": "in_progress",
            "total_sources": len(sources),
            "completed_sources": [],
            "failed_sources": [],
            "current_source": None,
            "source_progress": {},
            "overall_stats": {
                "total_pages": 0,
                "total_chunks": 0,
                "total_errors": 0
            },
            "last_checkpoint": datetime.now(UTC).isoformat()
        }
        
        self._save_checkpoint()
        
        logfire.info("Operation started with checkpointing",
                   operation_id=self.operation_id,
                   total_sources=len(sources))
        
        return self.operation_id
    
    @logfire.instrument("update_source_start")
    def update_source_start(self, source_name: str, source_info: Dict[str, Any]):
        """Update checkpoint when starting a new source."""
        self.checkpoint_data["current_source"] = source_name
        self.checkpoint_data["source_progress"][source_name] = {
            "status": "in_progress",
            "start_time": datetime.now(UTC).isoformat(),
            "pages_crawled": 0,
            "chunks_created": 0,
            "errors": 0,
            "source_info": source_info
        }
        
        self._conditional_save()
        
        logfire.info("Source started", source=source_name, operation_id=self.operation_id)
    
    @logfire.instrument("update_source_progress")
    def update_source_progress(self, source_name: str, pages: int = 0, 
                             chunks: int = 0, errors: int = 0):
        """Update progress for current source."""
        if source_name in self.checkpoint_data["source_progress"]:
            progress = self.checkpoint_data["source_progress"][source_name]
            progress["pages_crawled"] += pages
            progress["chunks_created"] += chunks
            progress["errors"] += errors
            progress["last_update"] = datetime.now(UTC).isoformat()
            
            # Update overall stats
            self.checkpoint_data["overall_stats"]["total_pages"] += pages
            self.checkpoint_data["overall_stats"]["total_chunks"] += chunks
            self.checkpoint_data["overall_stats"]["total_errors"] += errors
            
            self._conditional_save()
    
    @logfire.instrument("complete_source")
    def complete_source(self, source_name: str, success: bool = True):
        """Mark source as completed."""
        if source_name in self.checkpoint_data["source_progress"]:
            progress = self.checkpoint_data["source_progress"][source_name]
            progress["status"] = "completed" if success else "failed"
            progress["end_time"] = datetime.now(UTC).isoformat()
            
            if success:
                self.checkpoint_data["completed_sources"].append(source_name)
            else:
                self.checkpoint_data["failed_sources"].append(source_name)
            
            self.checkpoint_data["current_source"] = None
            
            self._save_checkpoint()
            
            logfire.info("Source completed",
                       source=source_name,
                       success=success,
                       chunks=progress["chunks_created"])
    
    @logfire.instrument("complete_operation")
    def complete_operation(self, success: bool = True):
        """Mark entire operation as completed."""
        self.checkpoint_data["status"] = "completed" if success else "failed"
        self.checkpoint_data["end_time"] = datetime.now(UTC).isoformat()
        
        # Calculate final statistics
        total_chunks = sum(
            self.checkpoint_data["source_progress"][source]["chunks_created"]
            for source in self.checkpoint_data["completed_sources"]
        )
        
        self.checkpoint_data["final_stats"] = {
            "total_sources_completed": len(self.checkpoint_data["completed_sources"]),
            "total_sources_failed": len(self.checkpoint_data["failed_sources"]),
            "total_chunks_created": total_chunks,
            "duration_seconds": self._calculate_duration()
        }
        
        self._save_checkpoint()
        
        logfire.info("Operation completed",
                   operation_id=self.operation_id,
                   success=success,
                   total_chunks=total_chunks)
    
    @logfire.instrument("get_checkpoint_data")
    def get_checkpoint_data(self) -> Dict[str, Any]:
        """Get current checkpoint data."""
        return self.checkpoint_data.copy()
    
    @logfire.instrument("get_progress_summary")
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of current progress."""
        completed = len(self.checkpoint_data["completed_sources"])
        failed = len(self.checkpoint_data["failed_sources"])
        total = self.checkpoint_data["total_sources"]
        
        return {
            "operation_id": self.operation_id,
            "progress_percentage": ((completed + failed) / total * 100) if total > 0 else 0,
            "sources_completed": completed,
            "sources_failed": failed,
            "sources_remaining": total - completed - failed,
            "current_source": self.checkpoint_data["current_source"],
            "total_chunks": self.checkpoint_data["overall_stats"]["total_chunks"],
            "total_errors": self.checkpoint_data["overall_stats"]["total_errors"],
            "duration_seconds": self._calculate_duration()
        }
    
    def _conditional_save(self):
        """Save checkpoint if enough time has passed."""
        current_time = time.time()
        if current_time - self.last_save >= self.save_interval:
            self._save_checkpoint()
    
    def _save_checkpoint(self):
        """Save checkpoint to disk."""
        if not self.operation_id:
            return
        
        try:
            self.checkpoint_data["last_checkpoint"] = datetime.now(UTC).isoformat()
            
            checkpoint_file = self.checkpoint_dir / f"operation_{self.operation_id}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(self.checkpoint_data, f, indent=2)
            
            self.last_save = time.time()
            
            logfire.debug("Checkpoint saved", 
                        operation_id=self.operation_id,
                        file=str(checkpoint_file))
            
        except Exception as e:
            logfire.error("Failed to save checkpoint", 
                        operation_id=self.operation_id,
                        error=str(e))
    
    def _calculate_duration(self) -> float:
        """Calculate operation duration in seconds."""
        if "start_time" not in self.checkpoint_data:
            return 0
        
        start = datetime.fromisoformat(self.checkpoint_data["start_time"].replace('Z', '+00:00'))
        
        if "end_time" in self.checkpoint_data:
            end = datetime.fromisoformat(self.checkpoint_data["end_time"].replace('Z', '+00:00'))
        else:
            end = datetime.now(UTC)
        
        return (end - start).total_seconds()


class OperationRecovery:
    """Handles recovery of interrupted operations."""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
    
    @logfire.instrument("find_interrupted_operations")
    def find_interrupted_operations(self) -> List[Dict[str, Any]]:
        """Find operations that were interrupted."""
        interrupted = []
        
        for checkpoint_file in self.checkpoint_dir.glob("operation_*.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                
                if data.get("status") == "in_progress":
                    # Check if it's actually interrupted (older than 1 hour)
                    last_checkpoint = data.get("last_checkpoint")
                    if last_checkpoint:
                        last_time = datetime.fromisoformat(last_checkpoint.replace('Z', '+00:00'))
                        if (datetime.now(UTC) - last_time).total_seconds() > 3600:  # 1 hour
                            interrupted.append(data)
                            
            except Exception as e:
                logfire.error("Failed to read operation checkpoint",
                            file=str(checkpoint_file),
                            error=str(e))
        
        return interrupted
    
    @logfire.instrument("get_recovery_plan")
    def get_recovery_plan(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a recovery plan for an interrupted operation."""
        completed_sources = set(operation_data.get("completed_sources", []))
        failed_sources = set(operation_data.get("failed_sources", []))
        current_source = operation_data.get("current_source")
        
        # Determine sources that need to be processed
        all_sources = operation_data.get("source_list", [])
        if not all_sources:
            # Try to reconstruct from progress data
            all_sources = list(operation_data.get("source_progress", {}).keys())
        
        remaining_sources = []
        for source in all_sources:
            if source not in completed_sources and source not in failed_sources:
                remaining_sources.append(source)
        
        # Add current source if it was interrupted
        if current_source and current_source not in completed_sources:
            if current_source not in remaining_sources:
                remaining_sources.insert(0, current_source)
        
        return {
            "operation_id": operation_data["operation_id"],
            "operation_name": operation_data["operation_name"],
            "total_sources": operation_data["total_sources"],
            "completed_count": len(completed_sources),
            "failed_count": len(failed_sources),
            "remaining_sources": remaining_sources,
            "progress_so_far": operation_data.get("overall_stats", {}),
            "interrupted_at": operation_data.get("last_checkpoint"),
            "recovery_recommended": len(remaining_sources) > 0
        }
    
    @logfire.instrument("resume_operation")
    async def resume_operation(self, operation_data: Dict[str, Any], 
                             crawler_instance) -> bool:
        """Resume an interrupted operation."""
        recovery_plan = self.get_recovery_plan(operation_data)
        
        if not recovery_plan["recovery_recommended"]:
            logfire.info("No recovery needed", operation_id=operation_data["operation_id"])
            return True
        
        logfire.info("Resuming interrupted operation",
                   operation_id=operation_data["operation_id"],
                   remaining_sources=len(recovery_plan["remaining_sources"]))
        
        # Continue with remaining sources
        # This would integrate with the main crawler logic
        # For now, just log the plan
        
        return True


class ProgressReporter:
    """Reports progress during long operations."""
    
    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self.report_interval = 60  # seconds
        self.last_report = 0
    
    @logfire.instrument("maybe_report_progress")
    def maybe_report_progress(self, force: bool = False):
        """Report progress if enough time has passed."""
        current_time = time.time()
        
        if force or (current_time - self.last_report >= self.report_interval):
            self._generate_progress_report()
            self.last_report = current_time
    
    def _generate_progress_report(self):
        """Generate and log progress report."""
        summary = self.checkpoint_manager.get_progress_summary()
        
        print(f"\n📊 CRAWL PROGRESS REPORT")
        print(f"🕐 Duration: {summary['duration_seconds']:.1f}s")
        print(f"📈 Progress: {summary['progress_percentage']:.1f}%")
        print(f"✅ Completed: {summary['sources_completed']}")
        print(f"❌ Failed: {summary['sources_failed']}")
        print(f"⏳ Remaining: {summary['sources_remaining']}")
        print(f"📄 Total Chunks: {summary['total_chunks']}")
        
        if summary['current_source']:
            print(f"🔄 Current: {summary['current_source']}")
        
        logfire.info("Progress report generated", **summary)


# CLI tool for checkpoint management
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            recovery = OperationRecovery()
            interrupted = recovery.find_interrupted_operations()
            
            if interrupted:
                print(f"\n🔄 Found {len(interrupted)} interrupted operations:")
                for op in interrupted:
                    print(f"   - {op['operation_id']} ({op['operation_name']})")
                    plan = recovery.get_recovery_plan(op)
                    print(f"     Remaining sources: {len(plan['remaining_sources'])}")
            else:
                print("✅ No interrupted operations found")
        
        elif command == "clean":
            # Clean up old checkpoints
            checkpoint_dir = Path("checkpoints")
            cleaned = 0
            
            for file in checkpoint_dir.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    
                    if data.get("status") in ["completed", "failed"]:
                        file.unlink()
                        cleaned += 1
                        
                except Exception:
                    pass
            
            print(f"🧹 Cleaned up {cleaned} old checkpoint files")
    
    else:
        print("Usage: python checkpoint_manager.py [list|clean]")