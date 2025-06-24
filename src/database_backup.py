#!/usr/bin/env python3
"""
Database Backup and Restore Utilities for Ptolemies
Prevents data loss by creating timestamped backups before operations
"""

import os
import json
import subprocess
import logfire
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from pathlib import Path

# Configure Logfire
logfire.configure(send_to_logfire=True if os.getenv("LOGFIRE_TOKEN") else False)

class DatabaseBackup:
    """Handles database backup and restore operations."""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
    @logfire.instrument("create_backup")
    def create_backup(self, namespace: str = "ptolemies", database: str = "knowledge") -> Optional[str]:
        """Create a timestamped backup of the database."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{namespace}_{database}_{timestamp}.surql"
        
        with logfire.span("Database backup", namespace=namespace, database=database):
            # Export all data from document_chunks table
            export_cmd = f"""
            surreal export --conn ws://localhost:8000/rpc \
            --user root --pass root \
            --ns {namespace} --db {database} \
            {backup_file}
            """
            
            try:
                result = subprocess.run(
                    export_cmd.split(),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Get backup statistics
                    stats_cmd = f"""
                    surreal sql --conn ws://localhost:8000/rpc \
                    --user root --pass root \
                    --ns {namespace} --db {database} \
                    --pretty
                    """
                    
                    stats_query = "SELECT count() as total FROM document_chunks GROUP ALL;"
                    
                    stats_result = subprocess.run(
                        stats_cmd.split(),
                        input=stats_query,
                        capture_output=True,
                        text=True
                    )
                    
                    logfire.info("Backup created successfully", 
                               backup_file=str(backup_file),
                               size_bytes=backup_file.stat().st_size)
                    
                    return str(backup_file)
                else:
                    logfire.error("Backup failed", 
                                error=result.stderr,
                                returncode=result.returncode)
                    return None
                    
            except Exception as e:
                logfire.error("Backup exception", error=str(e))
                return None
    
    @logfire.instrument("restore_backup")
    def restore_backup(self, backup_file: str, namespace: str = "ptolemies", 
                      database: str = "knowledge") -> bool:
        """Restore database from a backup file."""
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            logfire.error("Backup file not found", file=backup_file)
            return False
            
        with logfire.span("Database restore", backup_file=backup_file):
            import_cmd = f"""
            surreal import --conn ws://localhost:8000/rpc \
            --user root --pass root \
            --ns {namespace} --db {database} \
            {backup_file}
            """
            
            try:
                result = subprocess.run(
                    import_cmd.split(),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logfire.info("Backup restored successfully", 
                               backup_file=backup_file)
                    return True
                else:
                    logfire.error("Restore failed",
                                error=result.stderr,
                                returncode=result.returncode)
                    return False
                    
            except Exception as e:
                logfire.error("Restore exception", error=str(e))
                return False
    
    @logfire.instrument("list_backups")
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups with metadata."""
        backups = []
        
        for backup_file in self.backup_dir.glob("backup_*.surql"):
            stats = backup_file.stat()
            
            # Parse filename for metadata
            parts = backup_file.stem.split("_")
            if len(parts) >= 5:
                namespace = parts[1]
                database = parts[2]
                date_str = parts[3]
                time_str = parts[4]
                
                backups.append({
                    "file": str(backup_file),
                    "namespace": namespace,
                    "database": database,
                    "timestamp": f"{date_str}_{time_str}",
                    "size_mb": round(stats.st_size / 1024 / 1024, 2),
                    "created": datetime.fromtimestamp(stats.st_ctime).isoformat()
                })
        
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
    
    @logfire.instrument("auto_backup")
    def auto_backup_before_operation(self, operation_name: str,
                                   namespace: str = "ptolemies",
                                   database: str = "knowledge") -> Optional[str]:
        """Create automatic backup before potentially destructive operations."""
        with logfire.span("Auto backup", operation=operation_name):
            logfire.info("Creating automatic backup before operation",
                       operation=operation_name)
            
            backup_file = self.create_backup(namespace, database)
            
            if backup_file:
                # Keep only last 10 backups to save space
                self._cleanup_old_backups(keep_count=10)
                
            return backup_file
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backups keeping only the most recent ones."""
        backups = self.list_backups()
        
        if len(backups) > keep_count:
            for backup in backups[keep_count:]:
                try:
                    Path(backup["file"]).unlink()
                    logfire.info("Removed old backup", file=backup["file"])
                except Exception as e:
                    logfire.error("Failed to remove backup", 
                                file=backup["file"], 
                                error=str(e))


# CLI interface
if __name__ == "__main__":
    import sys
    
    backup_manager = DatabaseBackup()
    
    if len(sys.argv) < 2:
        print("Usage: python database_backup.py [create|restore|list]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        backup_file = backup_manager.create_backup()
        if backup_file:
            print(f"✅ Backup created: {backup_file}")
        else:
            print("❌ Backup failed")
            
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Usage: python database_backup.py restore <backup_file>")
            sys.exit(1)
            
        success = backup_manager.restore_backup(sys.argv[2])
        if success:
            print("✅ Backup restored successfully")
        else:
            print("❌ Restore failed")
            
    elif command == "list":
        backups = backup_manager.list_backups()
        if backups:
            print("\nAvailable backups:")
            print("-" * 80)
            for backup in backups:
                print(f"📁 {backup['timestamp']} - {backup['size_mb']}MB - {backup['file']}")
        else:
            print("No backups found")
            
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)