#!/usr/bin/env python3
"""
Transaction Manager for Reliable Batch Operations
Handles chunk storage with batching, rollback, and recovery
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
import logfire
from pathlib import Path

logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

class TransactionManager:
    """Manages batch transactions for reliable chunk storage."""
    
    def __init__(self, batch_size: int = 50, checkpoint_dir: str = "checkpoints"):
        self.batch_size = batch_size
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.current_batch = []
        self.total_stored = 0
        self.failed_chunks = []
        
    @logfire.instrument("start_transaction")
    def start_transaction(self, source_name: str) -> str:
        """Start a new transaction for a source."""
        transaction_id = f"txn_{source_name}_{int(time.time())}"
        
        self.current_batch = []
        self.transaction_id = transaction_id
        self.source_name = source_name
        
        # Create transaction checkpoint
        checkpoint_data = {
            "transaction_id": transaction_id,
            "source_name": source_name,
            "start_time": datetime.now(UTC).isoformat(),
            "status": "active",
            "total_chunks": 0,
            "stored_chunks": 0,
            "failed_chunks": 0
        }
        
        checkpoint_file = self.checkpoint_dir / f"{transaction_id}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logfire.info("Transaction started", 
                   transaction_id=transaction_id,
                   source=source_name)
        
        return transaction_id
    
    @logfire.instrument("add_chunk_to_batch")
    def add_chunk_to_batch(self, chunk_data: Dict[str, Any]) -> bool:
        """Add chunk to current batch."""
        self.current_batch.append(chunk_data)
        
        # If batch is full, commit it
        if len(self.current_batch) >= self.batch_size:
            return self.commit_batch()
        
        return True
    
    @logfire.instrument("commit_batch")
    def commit_batch(self) -> bool:
        """Commit current batch to database."""
        if not self.current_batch:
            return True
        
        batch_size = len(self.current_batch)
        successful_stores = 0
        
        with logfire.span("Batch commit", batch_size=batch_size):
            # Try to store each chunk in the batch
            for chunk_data in self.current_batch:
                try:
                    if self._store_single_chunk(chunk_data):
                        successful_stores += 1
                    else:
                        self.failed_chunks.append(chunk_data)
                        logfire.warning("Chunk storage failed in batch",
                                      chunk_title=chunk_data.get('title', 'unknown'))
                        
                except Exception as e:
                    self.failed_chunks.append(chunk_data)
                    logfire.error("Chunk storage exception in batch",
                                error=str(e),
                                chunk_title=chunk_data.get('title', 'unknown'))
            
            self.total_stored += successful_stores
            
            # Update checkpoint
            self._update_checkpoint(successful_stores, len(self.current_batch) - successful_stores)
            
            # Clear batch
            self.current_batch = []
            
            logfire.info("Batch committed",
                       successful=successful_stores,
                       failed=batch_size - successful_stores,
                       total_stored=self.total_stored)
            
            return successful_stores > 0
    
    def _store_single_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """Store a single chunk - interface for actual storage."""
        # This will be overridden by the crawler
        # For now, simulate storage
        from production_crawler_hybrid import run_surreal_query
        
        try:
            # Safely escape content for SQL
            content = chunk_data['content'].replace("'", "''").replace('"', '""')[:2500]
            title = chunk_data['title'].replace("'", "''").replace('"', '""')[:200]
            source_name = chunk_data['source_name'].replace("'", "''")
            source_url = chunk_data['source_url'].replace("'", "''")
            
            # Format embedding safely
            embedding = chunk_data.get('embedding', [])
            if embedding and len(embedding) > 0:
                embedding_safe = embedding[:1536]
                embedding_str = "[" + ", ".join(f"{float(x):.6f}" for x in embedding_safe) + "]"
            else:
                embedding_str = "[]"
            
            # Format topics safely
            topics = chunk_data.get('topics', [])
            topics_safe = [str(topic).replace("'", "''")[:50] for topic in topics[:10]]
            topics_str = "[" + ", ".join(f"'{topic}'" for topic in topics_safe) + "]"
            
            query = f"""
            CREATE document_chunks SET
                source_name = '{source_name}',
                source_url = '{source_url}',
                title = '{title}',
                content = '{content}',
                chunk_index = {chunk_data.get('chunk_index', 0)},
                total_chunks = {chunk_data.get('total_chunks', 1)},
                quality_score = {chunk_data.get('quality_score', 0.5)},
                topics = {topics_str},
                embedding = {embedding_str},
                created_at = time::now();
            """
            
            return run_surreal_query(query)
            
        except Exception as e:
            logfire.error("Single chunk storage failed", error=str(e))
            return False
    
    @logfire.instrument("finalize_transaction")
    def finalize_transaction(self) -> Dict[str, Any]:
        """Finalize transaction and return summary."""
        # Commit any remaining chunks
        if self.current_batch:
            self.commit_batch()
        
        # Update final checkpoint
        self._update_checkpoint(0, 0, status="completed")
        
        summary = {
            "transaction_id": self.transaction_id,
            "source_name": self.source_name,
            "total_stored": self.total_stored,
            "failed_count": len(self.failed_chunks),
            "success_rate": self.total_stored / (self.total_stored + len(self.failed_chunks)) if (self.total_stored + len(self.failed_chunks)) > 0 else 0
        }
        
        logfire.info("Transaction finalized",
                   transaction_id=self.transaction_id,
                   total_stored=self.total_stored,
                   failed_count=len(self.failed_chunks))
        
        return summary
    
    @logfire.instrument("rollback_transaction")
    def rollback_transaction(self) -> bool:
        """Rollback transaction (delete stored chunks)."""
        try:
            from production_crawler_hybrid import run_surreal_query
            
            # Delete all chunks for this source created in this transaction
            delete_query = f"""
            DELETE document_chunks WHERE source_name = '{self.source_name}' 
            AND created_at > '{datetime.now(UTC).replace(hour=0, minute=0).isoformat()}';
            """
            
            success = run_surreal_query(delete_query)
            
            if success:
                self._update_checkpoint(0, 0, status="rolled_back")
                logfire.info("Transaction rolled back", transaction_id=self.transaction_id)
            else:
                logfire.error("Transaction rollback failed", transaction_id=self.transaction_id)
            
            return success
            
        except Exception as e:
            logfire.error("Rollback exception", error=str(e), transaction_id=self.transaction_id)
            return False
    
    def _update_checkpoint(self, stored_count: int, failed_count: int, status: str = "active"):
        """Update transaction checkpoint."""
        try:
            checkpoint_file = self.checkpoint_dir / f"{self.transaction_id}.json"
            
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
            else:
                checkpoint_data = {}
            
            checkpoint_data.update({
                "stored_chunks": self.total_stored,
                "failed_chunks": len(self.failed_chunks),
                "last_update": datetime.now(UTC).isoformat(),
                "status": status
            })
            
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
                
        except Exception as e:
            logfire.error("Checkpoint update failed", error=str(e))
    
    @logfire.instrument("get_failed_chunks")
    def get_failed_chunks(self) -> List[Dict[str, Any]]:
        """Get list of chunks that failed to store."""
        return self.failed_chunks.copy()
    
    @logfire.instrument("retry_failed_chunks")
    def retry_failed_chunks(self) -> int:
        """Retry storing failed chunks."""
        if not self.failed_chunks:
            return 0
        
        retry_count = 0
        remaining_failed = []
        
        with logfire.span("Retry failed chunks", total=len(self.failed_chunks)):
            for chunk_data in self.failed_chunks:
                try:
                    if self._store_single_chunk(chunk_data):
                        retry_count += 1
                        self.total_stored += 1
                    else:
                        remaining_failed.append(chunk_data)
                except Exception as e:
                    remaining_failed.append(chunk_data)
                    logfire.error("Retry failed", error=str(e))
            
            self.failed_chunks = remaining_failed
            
            if retry_count > 0:
                self._update_checkpoint(retry_count, 0)
            
            logfire.info("Retry completed", 
                       successful_retries=retry_count,
                       still_failed=len(remaining_failed))
            
            return retry_count


class RecoveryManager:
    """Manages recovery from interrupted transactions."""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        
    @logfire.instrument("find_incomplete_transactions")
    def find_incomplete_transactions(self) -> List[Dict[str, Any]]:
        """Find transactions that were interrupted."""
        incomplete = []
        
        for checkpoint_file in self.checkpoint_dir.glob("txn_*.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                
                if checkpoint_data.get("status") == "active":
                    incomplete.append(checkpoint_data)
                    
            except Exception as e:
                logfire.error("Failed to read checkpoint", 
                            file=str(checkpoint_file), 
                            error=str(e))
        
        return incomplete
    
    @logfire.instrument("cleanup_old_checkpoints")
    def cleanup_old_checkpoints(self, days_old: int = 7):
        """Clean up old completed checkpoints."""
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        cleaned = 0
        
        for checkpoint_file in self.checkpoint_dir.glob("txn_*.json"):
            try:
                if checkpoint_file.stat().st_mtime < cutoff_time:
                    with open(checkpoint_file, 'r') as f:
                        checkpoint_data = json.load(f)
                    
                    if checkpoint_data.get("status") in ["completed", "rolled_back"]:
                        checkpoint_file.unlink()
                        cleaned += 1
                        
            except Exception as e:
                logfire.error("Failed to cleanup checkpoint", 
                            file=str(checkpoint_file), 
                            error=str(e))
        
        logfire.info("Checkpoint cleanup completed", files_cleaned=cleaned)
        return cleaned


# Integration with production crawler
def enhance_crawler_with_transactions(crawler_class):
    """Enhance crawler with transaction management."""
    
    original_store_chunk = crawler_class.store_chunk
    
    def store_chunk_with_transaction(self, chunk_data: Dict[str, Any]) -> bool:
        """Enhanced store_chunk with transaction support."""
        if hasattr(self, 'transaction_manager') and self.transaction_manager:
            return self.transaction_manager.add_chunk_to_batch(chunk_data)
        else:
            # Fall back to original method
            return original_store_chunk(self, chunk_data)
    
    crawler_class.store_chunk = store_chunk_with_transaction
    return crawler_class


if __name__ == "__main__":
    # Test transaction manager
    tm = TransactionManager(batch_size=5)
    
    # Simulate transaction
    txn_id = tm.start_transaction("TestSource")
    
    # Add some test chunks
    for i in range(12):
        chunk_data = {
            'source_name': 'TestSource',
            'source_url': f'https://test.com/page{i}',
            'title': f'Test Page {i}',
            'content': f'This is test content for page {i}' * 20,
            'chunk_index': i,
            'total_chunks': 12,
            'quality_score': 0.8,
            'topics': ['test', 'example'],
            'embedding': [0.1] * 1536
        }
        tm.add_chunk_to_batch(chunk_data)
    
    # Finalize
    summary = tm.finalize_transaction()
    print(f"Transaction completed: {summary}")
    
    # Test recovery
    recovery = RecoveryManager()
    incomplete = recovery.find_incomplete_transactions()
    print(f"Found {len(incomplete)} incomplete transactions")