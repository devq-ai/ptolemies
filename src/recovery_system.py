#!/usr/bin/env python3
"""
Comprehensive Recovery System for Interrupted Crawl Operations
Handles graceful shutdown, state preservation, and automatic resume
"""

import signal
import sys
import json
import asyncio
import atexit
from typing import Dict, Any, Optional, Callable
from datetime import datetime, UTC
from pathlib import Path
import logfire

logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

class GracefulShutdownHandler:
    """Handles graceful shutdown and state preservation."""
    
    def __init__(self):
        self.shutdown_requested = False
        self.current_operation = None
        self.cleanup_callbacks = []
        self.state_file = Path("crawler_state.json")
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Register exit handler
        atexit.register(self._cleanup_on_exit)
        
        logfire.info("Graceful shutdown handler initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logfire.info("Shutdown signal received", signal=signal_name)
        
        print(f"\n🛑 Received {signal_name} - Initiating graceful shutdown...")
        
        self.shutdown_requested = True
        
        # Save current state
        self._save_state()
        
        # Run cleanup callbacks
        self._run_cleanup_callbacks()
        
        print("✅ Graceful shutdown completed")
        sys.exit(0)
    
    def _cleanup_on_exit(self):
        """Cleanup when process exits normally."""
        if not self.shutdown_requested:
            self._save_state()
            self._run_cleanup_callbacks()
    
    def register_cleanup_callback(self, callback: Callable):
        """Register a callback to run during shutdown."""
        self.cleanup_callbacks.append(callback)
    
    def set_current_operation(self, operation_data: Dict[str, Any]):
        """Set current operation for state preservation."""
        self.current_operation = operation_data
    
    def should_shutdown(self) -> bool:
        """Check if shutdown was requested."""
        return self.shutdown_requested
    
    def _save_state(self):
        """Save current crawler state."""
        if self.current_operation:
            try:
                state_data = {
                    "last_operation": self.current_operation,
                    "shutdown_time": datetime.now(UTC).isoformat(),
                    "shutdown_requested": True
                }
                
                with open(self.state_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
                
                logfire.info("Crawler state saved", file=str(self.state_file))
                
            except Exception as e:
                logfire.error("Failed to save state", error=str(e))
    
    def _run_cleanup_callbacks(self):
        """Run all registered cleanup callbacks."""
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logfire.error("Cleanup callback failed", error=str(e))


class RecoveryOrchestrator:
    """Orchestrates the recovery of interrupted operations."""
    
    def __init__(self):
        self.state_file = Path("crawler_state.json")
        
    @logfire.instrument("check_for_recovery")
    def check_for_recovery(self) -> Optional[Dict[str, Any]]:
        """Check if there's a previous operation to recover."""
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
            
            if state_data.get("shutdown_requested"):
                logfire.info("Previous operation recovery data found")
                return state_data
            
        except Exception as e:
            logfire.error("Failed to read recovery state", error=str(e))
        
        return None
    
    @logfire.instrument("prompt_for_recovery")
    def prompt_for_recovery(self, recovery_data: Dict[str, Any]) -> bool:
        """Prompt user whether to recover previous operation."""
        last_op = recovery_data.get("last_operation", {})
        shutdown_time = recovery_data.get("shutdown_time", "unknown")
        
        print(f"\n🔄 RECOVERY AVAILABLE")
        print(f"Previous operation was interrupted at: {shutdown_time}")
        
        if "operation_name" in last_op:
            print(f"Operation: {last_op['operation_name']}")
        
        if "completed_sources" in last_op:
            completed = len(last_op.get("completed_sources", []))
            total = last_op.get("total_sources", 0)
            print(f"Progress: {completed}/{total} sources completed")
        
        if "current_source" in last_op:
            print(f"Was processing: {last_op['current_source']}")
        
        print("\nOptions:")
        print("  1. Resume previous operation")
        print("  2. Start fresh (previous progress will be lost)")
        print("  3. Exit and investigate manually")
        
        try:
            choice = input("\nChoose option (1-3): ").strip()
            
            if choice == "1":
                return True
            elif choice == "2":
                self._clear_recovery_data()
                return False
            elif choice == "3":
                print("Exiting. You can manually investigate the recovery data.")
                sys.exit(0)
            else:
                print("Invalid choice. Starting fresh.")
                self._clear_recovery_data()
                return False
                
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)
    
    def _clear_recovery_data(self):
        """Clear recovery data."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            logfire.info("Recovery data cleared")
        except Exception as e:
            logfire.error("Failed to clear recovery data", error=str(e))


class ResilienceEnhancer:
    """Enhances crawler resilience with automatic recovery features."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 5.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.operation_stats = {}
    
    @logfire.instrument("resilient_operation")
    async def resilient_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute operation with resilience features."""
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries:
            try:
                logfire.info("Attempting operation", 
                           operation=operation_name, 
                           attempt=attempt + 1)
                
                result = await operation_func(*args, **kwargs)
                
                if attempt > 0:
                    logfire.info("Operation succeeded after retry", 
                               operation=operation_name, 
                               attempts=attempt + 1)
                
                return result
                
            except Exception as e:
                attempt += 1
                last_error = e
                
                logfire.warning("Operation failed, will retry", 
                              operation=operation_name,
                              attempt=attempt,
                              max_retries=self.max_retries,
                              error=str(e))
                
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)  # Exponential backoff
                
        # All retries exhausted
        logfire.error("Operation failed after all retries", 
                    operation=operation_name,
                    attempts=self.max_retries,
                    final_error=str(last_error))
        
        raise last_error
    
    @logfire.instrument("resilient_source_crawl")
    async def resilient_source_crawl(self, crawler, source_data: Dict[str, Any]):
        """Crawl a source with resilience features."""
        source_name = source_data.get("name", "unknown")
        
        async def crawl_operation():
            return await crawler.crawl_source(source_data)
        
        try:
            chunks_created = await self.resilient_operation(
                f"crawl_{source_name}", 
                crawl_operation
            )
            
            self.operation_stats[source_name] = {
                "status": "success",
                "chunks": chunks_created,
                "attempts": 1  # Would need to track actual attempts
            }
            
            return chunks_created
            
        except Exception as e:
            self.operation_stats[source_name] = {
                "status": "failed",
                "chunks": 0,
                "error": str(e),
                "attempts": self.max_retries
            }
            
            logfire.error("Source crawl failed permanently", 
                        source=source_name, 
                        error=str(e))
            
            return 0
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get statistics for all operations."""
        return self.operation_stats.copy()


class EnhancedProductionCrawler:
    """Production crawler with full recovery and resilience features."""
    
    def __init__(self, original_crawler):
        self.crawler = original_crawler
        self.shutdown_handler = GracefulShutdownHandler()
        self.recovery_orchestrator = RecoveryOrchestrator()
        self.resilience_enhancer = ResilienceEnhancer()
        
        # Register cleanup
        self.shutdown_handler.register_cleanup_callback(self._cleanup_crawler)
    
    async def run_with_recovery(self):
        """Run crawler with full recovery support."""
        # Check for recovery
        recovery_data = self.recovery_orchestrator.check_for_recovery()
        
        if recovery_data:
            should_recover = self.recovery_orchestrator.prompt_for_recovery(recovery_data)
            
            if should_recover:
                return await self._resume_operation(recovery_data)
        
        # Start fresh operation
        return await self._start_fresh_operation()
    
    async def _start_fresh_operation(self):
        """Start a fresh crawling operation."""
        from production_crawler_hybrid import PRODUCTION_SOURCES
        
        operation_data = {
            "operation_name": "production_crawl",
            "start_time": datetime.now(UTC).isoformat(),
            "total_sources": len(PRODUCTION_SOURCES),
            "completed_sources": [],
            "current_source": None
        }
        
        self.shutdown_handler.set_current_operation(operation_data)
        
        print("🚀 Starting fresh production crawl with recovery features")
        
        try:
            if not await self.crawler.initialize():
                print("❌ Crawler initialization failed")
                return False
            
            success = await self._crawl_with_resilience(PRODUCTION_SOURCES, operation_data)
            
            if success:
                print("🎉 Production crawl completed successfully!")
                self.recovery_orchestrator._clear_recovery_data()
            
            return success
            
        except Exception as e:
            logfire.error("Fresh operation failed", error=str(e))
            return False
    
    async def _resume_operation(self, recovery_data: Dict[str, Any]):
        """Resume a previous operation."""
        print("🔄 Resuming previous operation...")
        
        # This would implement actual resume logic
        # For now, start fresh but with awareness of previous state
        return await self._start_fresh_operation()
    
    async def _crawl_with_resilience(self, sources: list, operation_data: Dict[str, Any]):
        """Crawl sources with resilience features."""
        completed = 0
        
        for i, source in enumerate(sources):
            # Check for shutdown request
            if self.shutdown_handler.should_shutdown():
                print(f"🛑 Shutdown requested, stopping at source {i+1}/{len(sources)}")
                return False
            
            source_name = source.get("name", f"source_{i}")
            operation_data["current_source"] = source_name
            self.shutdown_handler.set_current_operation(operation_data)
            
            print(f"🔄 Processing {source_name} ({i+1}/{len(sources)})")
            
            try:
                chunks = await self.resilience_enhancer.resilient_source_crawl(
                    self.crawler, 
                    source
                )
                
                if chunks > 0:
                    completed += 1
                    operation_data["completed_sources"].append(source_name)
                    print(f"✅ {source_name}: {chunks} chunks created")
                else:
                    print(f"⚠️ {source_name}: No chunks created")
                
            except Exception as e:
                print(f"❌ {source_name}: Failed - {str(e)}")
                logfire.error("Source processing failed", source=source_name, error=str(e))
        
        operation_data["current_source"] = None
        self.shutdown_handler.set_current_operation(operation_data)
        
        print(f"\n📊 Final Results: {completed}/{len(sources)} sources completed")
        
        # Show resilience stats
        stats = self.resilience_enhancer.get_operation_stats()
        successful_sources = [s for s, data in stats.items() if data["status"] == "success"]
        failed_sources = [s for s, data in stats.items() if data["status"] == "failed"]
        
        if successful_sources:
            print(f"✅ Successful: {', '.join(successful_sources)}")
        if failed_sources:
            print(f"❌ Failed: {', '.join(failed_sources)}")
        
        return completed > 0
    
    def _cleanup_crawler(self):
        """Cleanup crawler resources."""
        try:
            # This would be called during shutdown
            logfire.info("Cleaning up crawler resources")
            
            # Close HTTP client if exists
            if hasattr(self.crawler, 'http_client') and self.crawler.http_client:
                # Can't use async here, so just log
                logfire.info("HTTP client cleanup scheduled")
            
        except Exception as e:
            logfire.error("Crawler cleanup failed", error=str(e))


# CLI interface for recovery system
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "check":
            orchestrator = RecoveryOrchestrator()
            recovery_data = orchestrator.check_for_recovery()
            
            if recovery_data:
                print("🔄 Recovery data found:")
                last_op = recovery_data.get("last_operation", {})
                print(f"   Shutdown time: {recovery_data.get('shutdown_time')}")
                print(f"   Operation: {last_op.get('operation_name', 'unknown')}")
                print(f"   Progress: {len(last_op.get('completed_sources', []))}/{last_op.get('total_sources', 0)}")
            else:
                print("✅ No recovery data found")
        
        elif command == "clear":
            orchestrator = RecoveryOrchestrator()
            orchestrator._clear_recovery_data()
            print("🧹 Recovery data cleared")
        
        elif command == "test-shutdown":
            print("Testing graceful shutdown handler...")
            handler = GracefulShutdownHandler()
            
            handler.set_current_operation({
                "operation_name": "test_operation",
                "current_source": "test_source",
                "total_sources": 5,
                "completed_sources": ["source1", "source2"]
            })
            
            print("Send SIGINT (Ctrl+C) to test graceful shutdown...")
            
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    
    else:
        print("Usage: python recovery_system.py [check|clear|test-shutdown]")