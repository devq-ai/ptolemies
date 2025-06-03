#!/usr/bin/env python3
"""
Ptolemies Knowledge Base CLI

A command-line interface for the Ptolemies knowledge base system that allows users to:
1. Start and stop the SurrealDB database
2. Ingest content from URLs
3. Search for content (both keyword and semantic search)
4. Manage knowledge items (create, read, update, delete)
5. Export and import knowledge items
"""

import argparse
import asyncio
import json
import os
import sys
import logging
from typing import List, Dict, Any, Optional
import subprocess
import signal
import datetime
import tempfile
from urllib.parse import urlparse

import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich import print as rprint

from ptolemies.db.surrealdb_client import SurrealDBClient, SurrealDBError, ResourceNotFoundError
from ptolemies.models.knowledge_item import (
    KnowledgeItem,
    KnowledgeItemCreate,
    KnowledgeItemUpdate,
    Embedding,
    Relationship
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ptolemies-cli")

# Initialize rich console for better output formatting
console = Console()

# Global variables
SURREALDB_PROCESS = None
DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".ptolemies", "data")


class EmbeddingService:
    """Service for creating embeddings from text content."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-ada-002"):
        """
        Initialize the embedding service.
        
        Args:
            api_key: OpenAI API key, defaults to OPENAI_API_KEY env var
            model: Embedding model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        
    async def create_embedding(self, text: str) -> List[float]:
        """
        Create an embedding for the given text.
        
        Args:
            text: Text to create embedding for
            
        Returns:
            Vector embedding
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "input": text,
            "model": self.model
        }
        
        response = await self.client.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Error creating embedding: {response.text}")
        
        result = response.json()
        embedding = result["data"][0]["embedding"]
        
        return embedding


class ContentIngester:
    """Service for ingesting content from URLs."""
    
    def __init__(self, db_client: SurrealDBClient, embedding_service: EmbeddingService):
        """
        Initialize the content ingester.
        
        Args:
            db_client: SurrealDB client
            embedding_service: Service for creating embeddings
        """
        self.db_client = db_client
        self.embedding_service = embedding_service
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        
    async def ingest_url(self, url: str, tags: List[str] = None) -> KnowledgeItem:
        """
        Ingest content from a URL into the knowledge base.
        
        Args:
            url: URL to ingest
            tags: Optional list of tags to apply
            
        Returns:
            Created knowledge item
        """
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {url}")
        
        # Fetch content
        response = await self.client.get(url)
        response.raise_for_status()
        
        content = response.text
        content_type = response.headers.get("Content-Type", "").split(";")[0]
        
        # Map HTTP content type to our format
        if "text/html" in content_type:
            item_content_type = "text/html"
        elif "application/json" in content_type:
            item_content_type = "application/json"
        elif "text/plain" in content_type:
            item_content_type = "text/plain"
        elif "text/markdown" in content_type:
            item_content_type = "text/markdown"
        else:
            item_content_type = "text/plain"
        
        # Extract title from URL path
        path = parsed_url.path.strip("/")
        title = path.split("/")[-1] if path else parsed_url.netloc
        
        # Create metadata
        metadata = {
            "url": url,
            "fetched_at": datetime.datetime.utcnow().isoformat(),
            "original_content_type": content_type,
        }
        
        # Create knowledge item
        item_create = KnowledgeItemCreate(
            title=title,
            content=content,
            content_type=item_content_type,
            metadata=metadata,
            tags=tags or [],
            source=url
        )
        
        # Save to database
        item = await self.db_client.create_knowledge_item(item_create)
        
        # Create embedding
        try:
            vector = await self.embedding_service.create_embedding(content)
            
            embedding = Embedding(
                vector=vector,
                model=self.embedding_service.model,
                dimensions=len(vector)
            )
            
            await self.db_client.create_embedding(embedding, item.id)
            console.print(f"[green]Created embedding for {item.id}[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to create embedding: {str(e)}[/yellow]")
        
        return item


# Database management functions
async def start_database(data_path: str = DEFAULT_DB_PATH) -> None:
    """
    Start the SurrealDB database server.
    
    Args:
        data_path: Path to store database files
    """
    global SURREALDB_PROCESS
    
    if SURREALDB_PROCESS:
        console.print("[yellow]Database is already running[/yellow]")
        return
    
    # Create data directory if it doesn't exist
    os.makedirs(data_path, exist_ok=True)
    
    try:
        # Start SurrealDB process
        console.print("[blue]Starting SurrealDB...[/blue]")
        SURREALDB_PROCESS = subprocess.Popen(
            [
                "surreal", "start", 
                "--log", "info", 
                "--user", "root", 
                "--pass", "root",
                "file:" + data_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Give it a moment to start
        await asyncio.sleep(2)
        
        # Check if process is still running
        if SURREALDB_PROCESS.poll() is not None:
            stderr = SURREALDB_PROCESS.stderr.read().decode('utf-8')
            raise Exception(f"Failed to start SurrealDB: {stderr}")
        
        console.print("[green]SurrealDB started successfully[/green]")
    
    except FileNotFoundError:
        console.print("[red]Error: SurrealDB executable not found.[/red]")
        console.print("Please install SurrealDB: https://surrealdb.com/install")
        sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]Error starting database: {str(e)}[/red]")
        sys.exit(1)


def stop_database() -> None:
    """Stop the SurrealDB database server."""
    global SURREALDB_PROCESS
    
    if not SURREALDB_PROCESS:
        console.print("[yellow]Database is not running[/yellow]")
        return
    
    try:
        console.print("[blue]Stopping SurrealDB...[/blue]")
        
        # Send termination signal to process group
        os.killpg(os.getpgid(SURREALDB_PROCESS.pid), signal.SIGTERM)
        
        # Wait for process to terminate
        SURREALDB_PROCESS.wait(timeout=5)
        SURREALDB_PROCESS = None
        
        console.print("[green]SurrealDB stopped successfully[/green]")
    
    except subprocess.TimeoutExpired:
        console.print("[yellow]Warning: SurrealDB did not terminate gracefully, forcing...[/yellow]")
        os.killpg(os.getpgid(SURREALDB_PROCESS.pid), signal.SIGKILL)
        SURREALDB_PROCESS = None
    
    except Exception as e:
        console.print(f"[red]Error stopping database: {str(e)}[/red]")


# Knowledge item management functions
async def create_item(db_client: SurrealDBClient, args) -> None:
    """
    Create a new knowledge item.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        # Read content from file or stdin
        if args.file:
            with open(args.file, 'r') as f:
                content = f.read()
        elif args.content:
            content = args.content
        else:
            console.print("[blue]Reading content from stdin (Ctrl+D to finish):[/blue]")
            content = sys.stdin.read()
        
        # Create item
        item_create = KnowledgeItemCreate(
            title=args.title,
            content=content,
            content_type=args.content_type,
            tags=args.tags.split(',') if args.tags else [],
            source=args.source,
            metadata=json.loads(args.metadata) if args.metadata else {}
        )
        
        item = await db_client.create_knowledge_item(item_create)
        
        # Create embedding if requested
        if args.embedding:
            try:
                embedding_service = EmbeddingService()
                vector = await embedding_service.create_embedding(content)
                
                embedding = Embedding(
                    vector=vector,
                    model=embedding_service.model,
                    dimensions=len(vector)
                )
                
                await db_client.create_embedding(embedding, item.id)
                await embedding_service.close()
                
                console.print(f"[green]Created embedding for {item.id}[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to create embedding: {str(e)}[/yellow]")
        
        console.print(f"[green]Created knowledge item: {item.id}[/green]")
        display_item(item)
    
    except Exception as e:
        console.print(f"[red]Error creating knowledge item: {str(e)}[/red]")


async def get_item(db_client: SurrealDBClient, args) -> None:
    """
    Retrieve and display a knowledge item.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        item = await db_client.get_knowledge_item(args.id)
        display_item(item)
        
        # Show embedding if requested
        if args.show_embedding:
            try:
                embedding = await db_client.get_item_embedding(args.id)
                if embedding:
                    console.print("\n[bold]Embedding:[/bold]")
                    console.print(f"Model: {embedding.model}")
                    console.print(f"Dimensions: {embedding.dimensions}")
                    
                    if args.show_vector:
                        console.print("Vector:")
                        # Show only first 10 dimensions to avoid overwhelming output
                        console.print(embedding.vector[:10] + ["..."])
                else:
                    console.print("\n[yellow]No embedding found for this item[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Error retrieving embedding: {str(e)}[/yellow]")
        
        # Show relationships if requested
        if args.show_relationships:
            try:
                relationships = await db_client.get_item_relationships(args.id, direction="both")
                
                if relationships:
                    console.print("\n[bold]Relationships:[/bold]")
                    
                    table = Table(show_header=True)
                    table.add_column("Type")
                    table.add_column("Source ID")
                    table.add_column("Target ID")
                    table.add_column("Weight")
                    
                    for rel in relationships:
                        table.add_row(
                            rel.type,
                            rel.source_id,
                            rel.target_id,
                            str(rel.weight)
                        )
                    
                    console.print(table)
                else:
                    console.print("\n[yellow]No relationships found for this item[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Error retrieving relationships: {str(e)}[/yellow]")
    
    except ResourceNotFoundError:
        console.print(f"[red]Knowledge item not found: {args.id}[/red]")
    
    except Exception as e:
        console.print(f"[red]Error retrieving knowledge item: {str(e)}[/red]")


async def update_item(db_client: SurrealDBClient, args) -> None:
    """
    Update a knowledge item.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        # Prepare update data
        update_data = {}
        
        if args.title:
            update_data["title"] = args.title
        
        if args.content:
            update_data["content"] = args.content
        elif args.file:
            with open(args.file, 'r') as f:
                update_data["content"] = f.read()
        
        if args.content_type:
            update_data["content_type"] = args.content_type
        
        if args.tags:
            update_data["tags"] = args.tags.split(',')
        
        if args.source:
            update_data["source"] = args.source
        
        if args.metadata:
            update_data["metadata"] = json.loads(args.metadata)
        
        # Create update object
        item_update = KnowledgeItemUpdate(**update_data)
        
        # Update item
        updated_item = await db_client.update_knowledge_item(args.id, item_update)
        
        # Update embedding if requested
        if args.update_embedding and "content" in update_data:
            try:
                embedding_service = EmbeddingService()
                vector = await embedding_service.create_embedding(update_data["content"])
                
                embedding = Embedding(
                    vector=vector,
                    model=embedding_service.model,
                    dimensions=len(vector)
                )
                
                await db_client.create_embedding(embedding, args.id)
                await embedding_service.close()
                
                console.print(f"[green]Updated embedding for {args.id}[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to update embedding: {str(e)}[/yellow]")
        
        console.print(f"[green]Updated knowledge item: {args.id}[/green]")
        display_item(updated_item)
    
    except ResourceNotFoundError:
        console.print(f"[red]Knowledge item not found: {args.id}[/red]")
    
    except Exception as e:
        console.print(f"[red]Error updating knowledge item: {str(e)}[/red]")


async def delete_item(db_client: SurrealDBClient, args) -> None:
    """
    Delete a knowledge item.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        # First get the item to check if it exists
        try:
            item = await db_client.get_knowledge_item(args.id)
            
            # Confirm deletion if not forced
            if not args.force:
                console.print(f"[yellow]Are you sure you want to delete the item '{item.title}' ({args.id})? [y/N][/yellow]")
                response = input().lower()
                if response != 'y' and response != 'yes':
                    console.print("[blue]Deletion cancelled[/blue]")
                    return
            
            # Delete embedding if it exists
            if item.embedding_id:
                try:
                    await db_client.delete_embedding(item.embedding_id)
                    console.print(f"[green]Deleted embedding: {item.embedding_id}[/green]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to delete embedding: {str(e)}[/yellow]")
            
            # Delete the item
            result = await db_client.delete_knowledge_item(args.id)
            
            if result:
                console.print(f"[green]Deleted knowledge item: {args.id}[/green]")
            else:
                console.print(f"[yellow]Warning: Delete operation returned false for {args.id}[/yellow]")
        
        except ResourceNotFoundError:
            console.print(f"[red]Knowledge item not found: {args.id}[/red]")
    
    except Exception as e:
        console.print(f"[red]Error deleting knowledge item: {str(e)}[/red]")


async def list_items(db_client: SurrealDBClient, args) -> None:
    """
    List knowledge items.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        # Parse tags
        tags = args.tags.split(',') if args.tags else None
        
        # List items
        items = await db_client.list_knowledge_items(
            limit=args.limit,
            offset=args.offset,
            tags=tags,
            content_type=args.content_type
        )
        
        if not items:
            console.print("[yellow]No knowledge items found[/yellow]")
            return
        
        console.print(f"[green]Found {len(items)} knowledge items[/green]")
        
        # Create table
        table = Table(show_header=True)
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Content Type")
        table.add_column("Tags")
        table.add_column("Created At")
        table.add_column("Has Embedding")
        
        for item in items:
            table.add_row(
                item.id,
                item.title,
                item.content_type,
                ", ".join(item.tags),
                item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else "N/A",
                "Yes" if item.embedding_id else "No"
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error listing knowledge items: {str(e)}[/red]")


# URL content ingestion
async def ingest_url(db_client: SurrealDBClient, args) -> None:
    """
    Ingest content from a URL.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        embedding_service = EmbeddingService()
        ingester = ContentIngester(db_client, embedding_service)
        
        # Parse tags
        tags = args.tags.split(',') if args.tags else []
        
        with Progress() as progress:
            task = progress.add_task("[blue]Ingesting URL...[/blue]", total=1)
            
            item = await ingester.ingest_url(args.url, tags)
            
            progress.update(task, advance=1)
        
        await ingester.close()
        await embedding_service.close()
        
        console.print(f"[green]Successfully ingested URL: {args.url}[/green]")
        display_item(item)
    
    except Exception as e:
        console.print(f"[red]Error ingesting URL: {str(e)}[/red]")


# Search functions
async def search_keyword(db_client: SurrealDBClient, args) -> None:
    """
    Perform keyword search on knowledge items.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        # This is a basic implementation using a custom query
        # In a real system, you might want to use a more sophisticated approach
        query = """
            SELECT * FROM knowledge_item
            WHERE 
                title CONTAINS $keyword
                OR content CONTAINS $keyword
            LIMIT $limit
            OFFSET $offset;
        """
        
        params = {
            "keyword": args.query,
            "limit": args.limit,
            "offset": args.offset
        }
        
        result = await db_client.execute_custom_query(query, params)
        
        if not result or not result[0]["result"]:
            console.print(f"[yellow]No results found for keyword: {args.query}[/yellow]")
            return
        
        items = []
        for item_data in result[0]["result"]:
            try:
                items.append(KnowledgeItem.parse_obj(item_data))
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to parse item: {str(e)}[/yellow]")
        
        console.print(f"[green]Found {len(items)} results for keyword: {args.query}[/green]")
        
        # Create table
        table = Table(show_header=True)
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Content Type")
        table.add_column("Tags")
        
        for item in items:
            table.add_row(
                item.id,
                item.title,
                item.content_type,
                ", ".join(item.tags)
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error performing keyword search: {str(e)}[/red]")


async def search_semantic(db_client: SurrealDBClient, args) -> None:
    """
    Perform semantic search on knowledge items.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        embedding_service = EmbeddingService()
        
        # Generate embedding for the query
        query_vector = await embedding_service.create_embedding(args.query)
        await embedding_service.close()
        
        # Parse filter tags
        filter_tags = args.tags.split(',') if args.tags else None
        
        # Perform search
        results = await db_client.semantic_search(
            query_vector=query_vector,
            limit=args.limit,
            threshold=args.threshold,
            filter_tags=filter_tags,
            filter_content_type=args.content_type
        )
        
        if not results:
            console.print(f"[yellow]No semantic search results found for: {args.query}[/yellow]")
            return
        
        console.print(f"[green]Found {len(results)} semantic search results for: {args.query}[/green]")
        
        # Create table
        table = Table(show_header=True)
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Content Type")
        table.add_column("Tags")
        table.add_column("Similarity")
        
        for item, score in results:
            table.add_row(
                item.id,
                item.title,
                item.content_type,
                ", ".join(item.tags),
                f"{score:.4f}"
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error performing semantic search: {str(e)}[/red]")


# Import and export functions
async def export_items(db_client: SurrealDBClient, args) -> None:
    """
    Export knowledge items to a JSON file.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        # Parse tags for filtering
        tags = args.tags.split(',') if args.tags else None
        
        # List items based on filters
        items = await db_client.list_knowledge_items(
            limit=args.limit,
            offset=0,  # Always start from the beginning for export
            tags=tags,
            content_type=args.content_type
        )
        
        if not items:
            console.print("[yellow]No knowledge items found to export[/yellow]")
            return
        
        # Prepare items for export
        export_data = []
        
        with Progress() as progress:
            task = progress.add_task("[blue]Exporting items...[/blue]", total=len(items))
            
            for item in items:
                # Convert to dict for serialization
                item_dict = item.dict()
                
                # Get embedding if requested and available
                if args.include_embeddings and item.embedding_id:
                    try:
                        embedding = await db_client.get_item_embedding(item.id)
                        if embedding:
                            item_dict["embedding"] = embedding.dict()
                    except Exception as e:
                        console.print(f"[yellow]Warning: Failed to get embedding for {item.id}: {str(e)}[/yellow]")
                
                # Get relationships if requested
                if args.include_relationships:
                    try:
                        relationships = await db_client.get_item_relationships(item.id, direction="both")
                        if relationships:
                            item_dict["relationships"] = [rel.dict() for rel in relationships]
                    except Exception as e:
                        console.print(f"[yellow]Warning: Failed to get relationships for {item.id}: {str(e)}[/yellow]")
                
                export_data.append(item_dict)
                progress.update(task, advance=1)
        
        # Write to file
        with open(args.output, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        console.print(f"[green]Successfully exported {len(export_data)} items to {args.output}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error exporting knowledge items: {str(e)}[/red]")


async def import_items(db_client: SurrealDBClient, args) -> None:
    """
    Import knowledge items from a JSON file.
    
    Args:
        db_client: SurrealDB client
        args: Command line arguments
    """
    try:
        # Read import file
        with open(args.input, 'r') as f:
            import_data = json.load(f)
        
        if not import_data:
            console.print("[yellow]No items found in import file[/yellow]")
            return
        
        console.print(f"[blue]Found {len(import_data)} items to import[/blue]")
        
        # Process items
        with Progress() as progress:
            task = progress.add_task("[blue]Importing items...[/blue]", total=len(import_data))
            
            imported_count = 0
            for item_data in import_data:
                try:
                    # Extract embedding and relationship data if present
                    embedding_data = item_data.pop("embedding", None)
                    relationships_data = item_data.pop("relationships", None)
                    
                    # Handle datetime fields (convert strings back to datetime)
                    for field in ["created_at", "updated_at"]:
                        if field in item_data and item_data[field] and isinstance(item_data[field], str):
                            try:
                                item_data[field] = datetime.datetime.fromisoformat(item_data[field])
                            except ValueError:
                                # If parsing fails, remove the field
                                item_data.pop(field, None)
                    
                    # Create item
                    # First, check if item exists by ID if provided
                    item_id = item_data.get("id")
                    if item_id and not args.force:
                        try:
                            # Check if item already exists
                            await db_client.get_knowledge_item(item_id)
                            
                            if not args.update_existing:
                                console.print(f"[yellow]Skipping existing item: {item_id}[/yellow]")
                                progress.update(task, advance=1)
                                continue
                            
                            # Update existing item
                            update_data = {}
                            for field in ["title", "content", "content_type", "metadata", "tags", "source"]:
                                if field in item_data:
                                    update_data[field] = item_data[field]
                            
                            item_update = KnowledgeItemUpdate(**update_data)
                            item = await db_client.update_knowledge_item(item_id, item_update)
                            console.print(f"[green]Updated existing item: {item_id}[/green]")
                        
                        except ResourceNotFoundError:
                            # Item doesn't exist, create it
                            create_data = {}
                            for field in ["title", "content", "content_type", "metadata", "tags", "source"]:
                                if field in item_data:
                                    create_data[field] = item_data[field]
                            
                            item_create = KnowledgeItemCreate(**create_data)
                            item = await db_client.create_knowledge_item(item_create)
                            console.print(f"[green]Created new item: {item.id}[/green]")
                    else:
                        # Create new item
                        create_data = {}
                        for field in ["title", "content", "content_type", "metadata", "tags", "source"]:
                            if field in item_data:
                                create_data[field] = item_data[field]
                        
                        item_create = KnowledgeItemCreate(**create_data)
                        item = await db_client.create_knowledge_item(item_create)
                        console.print(f"[green]Created new item: {item.id}[/green]")
                    
                    # Import embedding if available
                    if embedding_data and args.include_embeddings:
                        try:
                            embedding = Embedding(
                                vector=embedding_data["vector"],
                                model=embedding_data["model"],
                                dimensions=embedding_data["dimensions"]
                            )
                            
                            await db_client.create_embedding(embedding, item.id)
                            console.print(f"[green]Created embedding for {item.id}[/green]")
                        except Exception as e:
                            console.print(f"[yellow]Warning: Failed to create embedding for {item.id}: {str(e)}[/yellow]")
                    
                    # Import relationships if available
                    if relationships_data and args.include_relationships:
                        for rel_data in relationships_data:
                            try:
                                # Adjust source_id to the new item ID if it was the imported item
                                if rel_data["source_id"] == item_data.get("id"):
                                    rel_data["source_id"] = item.id
                                
                                relationship = Relationship(**rel_data)
                                await db_client.create_relationship(relationship)
                                console.print(f"[green]Created relationship: {relationship.type} from {relationship.source_id} to {relationship.target_id}[/green]")
                            except Exception as e:
                                console.print(f"[yellow]Warning: Failed to create relationship: {str(e)}[/yellow]")
                    
                    imported_count += 1
                
                except Exception as e:
                    console.print(f"[red]Error importing item: {str(e)}[/red]")
                
                progress.update(task, advance=1)
        
        console.print(f"[green]Successfully imported {imported_count} items[/green]")
    
    except Exception as e:
        console.print(f"[red]Error importing knowledge items: {str(e)}[/red]")


# Helper functions
def display_item(item: KnowledgeItem) -> None:
    """
    Display a knowledge item in a formatted way.
    
    Args:
        item: Knowledge item to display
    """
    console.print(f"\n[bold]ID:[/bold] {item.id}")
    console.print(f"[bold]Title:[/bold] {item.title}")
    console.print(f"[bold]Content Type:[/bold] {item.content_type}")
    console.print(f"[bold]Tags:[/bold] {', '.join(item.tags)}")
    
    if item.source:
        console.print(f"[bold]Source:[/bold] {item.source}")
    
    if item.created_at:
        console.print(f"[bold]Created:[/bold] {item.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if item.updated_at:
        console.print(f"[bold]Updated:[/bold] {item.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if item.embedding_id:
        console.print(f"[bold]Embedding ID:[/bold] {item.embedding_id}")
    
    if item.metadata:
        console.print("[bold]Metadata:[/bold]")
        for key, value in item.metadata.items():
            console.print(f"  {key}: {value}")
    
    # Display truncated content
    console.print("\n[bold]Content:[/bold]")
    if len(item.content) > 1000:
        console.print(f"{item.content[:1000]}...\n[dim](content truncated, full length: {len(item.content)} characters)[/dim]")
    else:
        console.print(item.content)


async def init_db_client() -> SurrealDBClient:
    """
    Initialize and connect to SurrealDB.
    
    Returns:
        Connected SurrealDB client
    """
    db_client = SurrealDBClient()
    try:
        await db_client.connect()
        return db_client
    except SurrealDBError as e:
        console.print(f"[red]Error connecting to SurrealDB: {str(e)}[/red]")
        console.print("[yellow]Is the database running? Try 'ptolemies-cli db start' first.[/yellow]")
        sys.exit(1)


async def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Ptolemies Knowledge Base CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Database management commands
    db_parser = subparsers.add_parser("db", help="Database management commands")
    db_subparsers = db_parser.add_subparsers(dest="db_command", help="Database command")
    
    # Start database
    start_parser = db_subparsers.add_parser("start", help="Start SurrealDB database")
    start_parser.add_argument(
        "--data-path", 
        default=DEFAULT_DB_PATH,
        help="Path to store database files"
    )
    
    # Stop database
    db_subparsers.add_parser("stop", help="Stop SurrealDB database")
    
    # Knowledge item management commands
    item_parser = subparsers.add_parser("item", help="Knowledge item management commands")
    item_subparsers = item_parser.add_subparsers(dest="item_command", help="Item command")
    
    # Create item
    create_parser = item_subparsers.add_parser("create", help="Create a new knowledge item")
    create_parser.add_argument("--title", required=True, help="Item title")
    create_parser.add_argument("--content", help="Item content")
    create_parser.add_argument("--file", help="File containing item content")
    create_parser.add_argument("--content-type", default="text/plain", help="Content type (e.g., text/plain, text/markdown)")
    create_parser.add_argument("--tags", help="Comma-separated list of tags")
    create_parser.add_argument("--source", help="Source of the content")
    create_parser.add_argument("--metadata", help="JSON metadata")
    create_parser.add_argument("--embedding", action="store_true", help="Create embedding for the item")
    
    # Get item
    get_parser = item_subparsers.add_parser("get", help="Get a knowledge item")
    get_parser.add_argument("id", help="Item ID")
    get_parser.add_argument("--show-embedding", action="store_true", help="Show embedding information")
    get_parser.add_argument("--show-vector", action="store_true", help="Show embedding vector")
    get_parser.add_argument("--show-relationships", action="store_true", help="Show relationships")
    
    # Update item
    update_parser = item_subparsers.add_parser("update", help="Update a knowledge item")
    update_parser.add_argument("id", help="Item ID")
    update_parser.add_argument("--title", help="Item title")
    update_parser.add_argument("--content", help="Item content")
    update_parser.add_argument("--file", help="File containing item content")
    update_parser.add_argument("--content-type", help="Content type (e.g., text/plain, text/markdown)")
    update_parser.add_argument("--tags", help="Comma-separated list of tags")
    update_parser.add_argument("--source", help="Source of the content")
    update_parser.add_argument("--metadata", help="JSON metadata")
    update_parser.add_argument("--update-embedding", action="store_true", help="Update embedding for the item")
    
    # Delete item
    delete_parser = item_subparsers.add_parser("delete", help="Delete a knowledge item")
    delete_parser.add_argument("id", help="Item ID")
    delete_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")
    
    # List items
    list_parser = item_subparsers.add_parser("list", help="List knowledge items")
    list_parser.add_argument("--limit", type=int, default=100, help="Maximum number of items to return")
    list_parser.add_argument("--offset", type=int, default=0, help="Number of items to skip")
    list_parser.add_argument("--tags", help="Filter by comma-separated list of tags")
    list_parser.add_argument("--content-type", help="Filter by content type")
    
    # URL ingestion commands
    ingest_parser = subparsers.add_parser("ingest", help="Content ingestion commands")
    ingest_subparsers = ingest_parser.add_subparsers(dest="ingest_command", help="Ingestion command")
    
    # Ingest URL
    url_parser = ingest_subparsers.add_parser("url", help="Ingest content from a URL")
    url_parser.add_argument("url", help="URL to ingest")
    url_parser.add_argument("--tags", help="Comma-separated list of tags")
    
    # Search commands
    search_parser = subparsers.add_parser("search", help="Search commands")
    search_subparsers = search_parser.add_subparsers(dest="search_command", help="Search command")
    
    # Keyword search
    keyword_parser = search_subparsers.add_parser("keyword", help="Perform keyword search")
    keyword_parser.add_argument("query", help="Search query")
    keyword_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results")
    keyword_parser.add_argument("--offset", type=int, default=0, help="Number of results to skip")
    
    # Semantic search
    semantic_parser = search_subparsers.add_parser("semantic", help="Perform semantic search")
    semantic_parser.add_argument("query", help="Search query")
    semantic_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results")
    semantic_parser.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold (0.0 to 1.0)")
    semantic_parser.add_argument("--tags", help="Filter by comma-separated list of tags")
    semantic_parser.add_argument("--content-type", help="Filter by content type")
    
    # Import/export commands
    import_export_parser = subparsers.add_parser("data", help="Import/export commands")
    import_export_subparsers = import_export_parser.add_subparsers(dest="data_command", help="Data command")
    
    # Export
    export_parser = import_export_subparsers.add_parser("export", help="Export knowledge items to JSON")
    export_parser.add_argument("--output", required=True, help="Output file path")
    export_parser.add_argument("--limit", type=int, default=1000, help="Maximum number of items to export")
    export_parser.add_argument("--tags", help="Filter by comma-separated list of tags")
    export_parser.add_argument("--content-type", help="Filter by content type")
    export_parser.add_argument("--include-embeddings", action="store_true", help="Include embeddings in export")
    export_parser.add_argument("--include-relationships", action="store_true", help="Include relationships in export")
    
    # Import
    import_parser = import_export_subparsers.add_parser("import", help="Import knowledge items from JSON")
    import_parser.add_argument("--input", required=True, help="Input file path")
    import_parser.add_argument("--force", action="store_true", help="Force import of items with existing IDs")
    import_parser.add_argument("--update-existing", action="store_true", help="Update existing items")
    import_parser.add_argument("--include-embeddings", action="store_true", help="Import embeddings")
    import_parser.add_argument("--include-relationships", action="store_true", help="Import relationships")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if not args.command:
        parser.print_help()
        return
    
    # Database management
    if args.command == "db":
        if not args.db_command:
            db_parser.print_help()
            return
        
        if args.db_command == "start":
            await start_database(args.data_path)
        
        elif args.db_command == "stop":
            stop_database()
    
    # Knowledge item management
    elif args.command == "item":
        if not args.item_command:
            item_parser.print_help()
            return
        
        db_client = await init_db_client()
        
        try:
            if args.item_command == "create":
                await create_item(db_client, args)
            
            elif args.item_command == "get":
                await get_item(db_client, args)
            
            elif args.item_command == "update":
                await update_item(db_client, args)
            
            elif args.item_command == "delete":
                await delete_item(db_client, args)
            
            elif args.item_command == "list":
                await list_items(db_client, args)
        
        finally:
            await db_client.disconnect()
    
    # URL ingestion
    elif args.command == "ingest":
        if not args.ingest_command:
            ingest_parser.print_help()
            return
        
        db_client = await init_db_client()
        
        try:
            if args.ingest_command == "url":
                await ingest_url(db_client, args)
        
        finally:
            await db_client.disconnect()
    
    # Search
    elif args.command == "search":
        if not args.search_command:
            search_parser.print_help()
            return
        
        db_client = await init_db_client()
        
        try:
            if args.search_command == "keyword":
                await search_keyword(db_client, args)
            
            elif args.search_command == "semantic":
                await search_semantic(db_client, args)
        
        finally:
            await db_client.disconnect()
    
    # Import/export
    elif args.command == "data":
        if not args.data_command:
            import_export_parser.print_help()
            return
        
        db_client = await init_db_client()
        
        try:
            if args.data_command == "export":
                await export_items(db_client, args)
            
            elif args.data_command == "import":
                await import_items(db_client, args)
        
        finally:
            await db_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unhandled error: {str(e)}[/red]")
        sys.exit(1)