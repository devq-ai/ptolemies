"""
SurrealDB client for the Ptolemies Knowledge Base system.

This module provides a client for interacting with a SurrealDB database,
implementing operations for managing knowledge items, embeddings, and relationships.

Follows the official SurrealDB Python client patterns as documented at:
https://github.com/surrealdb/surrealdb.py

Implementation patterns are based on the SurrealDB documentation:
- Connection management using context managers
- Schema-full table definitions for structured data
- Graph relationship traversal using RELATE statements
- Built-in vector search capabilities for semantic queries

References:
- SurrealDB Python SDK: https://github.com/surrealdb/surrealdb.py
- SurrealQL Documentation: https://surrealdb.com/docs/surrealql/
- Graph Relationships: https://surrealdb.com/docs/surrealql/datamodel/graph
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime

from surrealdb import Surreal
from dotenv import load_dotenv
from pydantic import ValidationError

from ..models.knowledge_item import (
    KnowledgeItem, 
    KnowledgeItemCreate,
    KnowledgeItemUpdate,
    Embedding,
    Relationship
)

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class SurrealDBError(Exception):
    """Base exception for SurrealDB client errors."""
    pass


class ConnectionError(SurrealDBError):
    """Error establishing connection to SurrealDB."""
    pass


class QueryError(SurrealDBError):
    """Error executing query on SurrealDB."""
    pass


class ResourceNotFoundError(SurrealDBError):
    """Requested resource not found in database."""
    pass


class SurrealDBClient:
    """
    Client for interacting with SurrealDB to manage knowledge items.
    
    This client provides methods for CRUD operations on knowledge items,
    as well as managing embeddings and relationships between items.
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        namespace: Optional[str] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize the SurrealDB client.
        
        Args:
            url: SurrealDB server URL, defaults to SURREALDB_URL env var
            namespace: SurrealDB namespace, defaults to SURREALDB_NAMESPACE env var
            database: SurrealDB database name, defaults to SURREALDB_DATABASE env var
            username: SurrealDB username, defaults to SURREALDB_USERNAME env var
            password: SurrealDB password, defaults to SURREALDB_PASSWORD env var
        """
        self.url = url or os.getenv("SURREALDB_URL", "http://localhost:8000")
        self.namespace = namespace or os.getenv("SURREALDB_NAMESPACE", "ptolemies")
        self.database = database or os.getenv("SURREALDB_DATABASE", "knowledge")
        self.username = username or os.getenv("SURREALDB_USERNAME", "root")
        self.password = password or os.getenv("SURREALDB_PASSWORD", "root")
        
        # Use the official SurrealDB client
        self.client = Surreal(self.url)
        self._connected = False
    
    async def connect(self) -> None:
        """
        Establish connection to SurrealDB using the official client pattern.
        
        Follows the SurrealDB connection pattern:
        1. Connect to the database server
        2. Authenticate with credentials
        3. Select namespace and database
        
        Reference: https://github.com/surrealdb/surrealdb.py#connection-management
        
        Raises:
            ConnectionError: If connection to SurrealDB fails
        """
        try:
            # Connect to the database
            await self.client.connect()
            
            # Sign in with credentials
            await self.client.signin({"user": self.username, "pass": self.password})
            
            # Select namespace and database
            await self.client.use(self.namespace, self.database)
            
            self._connected = True
            logger.info(f"Connected to SurrealDB at {self.url}")
        
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to SurrealDB: {str(e)}")
            raise ConnectionError(f"Failed to connect to SurrealDB: {str(e)}")
    
    async def disconnect(self) -> None:
        """Close the connection to SurrealDB."""
        if self.client:
            await self.client.close()
            self._connected = False
            logger.info("Disconnected from SurrealDB")
    
    async def _ensure_connected(self) -> None:
        """Ensure client is connected to SurrealDB."""
        if not self._connected:
            await self.connect()
    
    # Knowledge Item CRUD Operations
    
    async def create_knowledge_item(
        self, item: KnowledgeItemCreate
    ) -> KnowledgeItem:
        """
        Create a new knowledge item in the database.
        
        Args:
            item: Knowledge item to create
            
        Returns:
            Created knowledge item with ID and timestamps
            
        Raises:
            QueryError: If creation fails
        """
        try:
            await self._ensure_connected()
            
            # Prepare item data
            item_dict = item.dict()
            
            # Extract category from metadata if present
            if "category" in item_dict.get("metadata", {}):
                item_dict["category"] = item_dict["metadata"]["category"]
            
            # Extract source_type from metadata if present  
            if "source_type" in item_dict.get("metadata", {}):
                item_dict["source_type"] = item_dict["metadata"]["source_type"]
            
            # Create the item using the official SurrealDB client
            # Uses the CREATE statement for document insertion as documented:
            # https://surrealdb.com/docs/surrealql/statements/create
            # Let SurrealDB handle the timestamps via query
            now_iso = datetime.utcnow().isoformat() + 'Z'
            
            # Use SurrealQL CREATE with string timestamps
            create_query = """
                CREATE knowledge_item CONTENT {
                    title: $title,
                    content: $content,
                    content_type: $content_type,
                    metadata: $metadata,
                    tags: $tags,
                    source: $source,
                    category: $category,
                    source_type: $source_type,
                    created_at: $now,
                    updated_at: $now,
                    version: 1
                }
            """
            
            params = {
                **item_dict,
                "now": now_iso
            }
            
            result = await self.client.query(create_query, params)
            
            # Extract the created item from the result
            if result and len(result) > 0 and "result" in result[0]:
                created_items = result[0]["result"]
                if created_items and len(created_items) > 0:
                    created_item = created_items[0]
                    return KnowledgeItem.parse_obj(created_item)
                else:
                    raise QueryError("No item created")
            else:
                raise QueryError("Query failed")
            
            raise QueryError("Failed to create knowledge item: No result returned")
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise QueryError(f"Validation error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error creating knowledge item: {str(e)}")
            raise QueryError(f"Error creating knowledge item: {str(e)}")
    
    async def get_knowledge_item(self, item_id: str) -> KnowledgeItem:
        """
        Retrieve a knowledge item by ID.
        
        Args:
            item_id: ID of the knowledge item to retrieve
            
        Returns:
            Retrieved knowledge item
            
        Raises:
            ResourceNotFoundError: If item doesn't exist
            QueryError: If retrieval fails
        """
        try:
            await self._ensure_connected()
            
            # Get the item using the official SurrealDB client
            item = await self.client.select(f"knowledge_item:{item_id}")
            
            if item and len(item) > 0:
                return KnowledgeItem.parse_obj(item[0])
            
            raise ResourceNotFoundError(f"Knowledge item not found: {item_id}")
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise QueryError(f"Validation error: {str(e)}")
        
        except ResourceNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error retrieving knowledge item: {str(e)}")
            raise QueryError(f"Error retrieving knowledge item: {str(e)}")
    
    async def update_knowledge_item(
        self, item_id: str, update: KnowledgeItemUpdate
    ) -> KnowledgeItem:
        """
        Update an existing knowledge item.
        
        Args:
            item_id: ID of the knowledge item to update
            update: Update data
            
        Returns:
            Updated knowledge item
            
        Raises:
            ResourceNotFoundError: If item doesn't exist
            QueryError: If update fails
        """
        try:
            # First check if the item exists
            await self.get_knowledge_item(item_id)
            
            await self._ensure_connected()
            
            # Prepare update data
            update_dict = {k: v for k, v in update.dict().items() if v is not None}
            update_dict["updated_at"] = datetime.utcnow().isoformat()
            
            # Update the item using the official SurrealDB client
            updated_item = await self.client.update(f"knowledge_item:{item_id}", update_dict)
            
            if updated_item and len(updated_item) > 0:
                return KnowledgeItem.parse_obj(updated_item[0])
            
            raise QueryError(f"Failed to update knowledge item: {item_id}")
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise QueryError(f"Validation error: {str(e)}")
        
        except ResourceNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error updating knowledge item: {str(e)}")
            raise QueryError(f"Error updating knowledge item: {str(e)}")
    
    async def delete_knowledge_item(self, item_id: str) -> bool:
        """
        Delete a knowledge item by ID.
        
        Args:
            item_id: ID of the knowledge item to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            ResourceNotFoundError: If item doesn't exist
            QueryError: If deletion fails
        """
        try:
            # First check if the item exists
            await self.get_knowledge_item(item_id)
            
            await self._ensure_connected()
            
            # Delete the item using the official SurrealDB client
            deleted = await self.client.delete(f"knowledge_item:{item_id}")
            
            # The delete method typically returns the number of deleted records
            return deleted is not None
        
        except ResourceNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error deleting knowledge item: {str(e)}")
            raise QueryError(f"Error deleting knowledge item: {str(e)}")
    
    async def list_knowledge_items(
        self, 
        limit: int = 100, 
        offset: int = 0,
        tags: Optional[List[str]] = None,
        content_type: Optional[str] = None,
    ) -> List[KnowledgeItem]:
        """
        List knowledge items with optional filtering.
        
        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip
            tags: Optional list of tags to filter by
            content_type: Optional content type to filter by
            
        Returns:
            List of knowledge items
            
        Raises:
            QueryError: If listing fails
        """
        try:
            await self._ensure_connected()
            
            # Build the query based on filters
            conditions = []
            params = {
                "limit": limit,
                "offset": offset,
            }
            
            # Add filters if provided
            if tags:
                tags_conditions = []
                for i, tag in enumerate(tags):
                    param_name = f"tag_{i}"
                    tags_conditions.append(f"$tag_{i} INSIDE tags")
                    params[param_name] = tag
                
                if tags_conditions:
                    conditions.append(f"({' AND '.join(tags_conditions)})")
            
            if content_type:
                conditions.append("content_type = $content_type")
                params["content_type"] = content_type
            
            # Construct the query
            # SurrealDB v0.3.0 doesn't support OFFSET, just use LIMIT
            query = "SELECT * FROM knowledge_item"
            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"
            query += f" LIMIT {limit}"
            
            # Execute the query using the official SurrealDB client
            result = await self.client.query(query, params)
            
            # Process the results
            items = []
            if result and len(result) > 0 and "result" in result[0]:
                items_data = result[0]["result"]
                for item_data in items_data:
                    try:
                        items.append(KnowledgeItem.parse_obj(item_data))
                    except ValidationError:
                        # Skip invalid items
                        pass
            
            return items
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise QueryError(f"Validation error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error listing knowledge items: {str(e)}")
            raise QueryError(f"Error listing knowledge items: {str(e)}")
    
    # Embedding Operations
    
    async def create_embedding(
        self, embedding: Embedding, item_id: Optional[str] = None
    ) -> Embedding:
        """
        Create a new embedding in the database.
        
        Args:
            embedding: Embedding to create
            item_id: Optional ID of the associated knowledge item
            
        Returns:
            Created embedding with ID
            
        Raises:
            QueryError: If creation fails
        """
        try:
            # Prepare embedding data
            embedding_dict = embedding.dict(exclude={"id", "created_at"})
            embedding_dict["created_at"] = datetime.utcnow()
            
            # If item_id is provided, associate the embedding with the item
            if item_id:
                embedding_dict["item_id"] = item_id
            
            # Create the embedding
            query = """
                CREATE embedding CONTENT $data
                RETURN AFTER;
            """
            
            result = await self._execute_query(query, {"data": embedding_dict})
            
            # Extract the created embedding from the result
            if result and len(result) > 0 and "result" in result[0]:
                created_embeddings = result[0]["result"]
                if created_embeddings and len(created_embeddings) > 0:
                    created_embedding = Embedding.parse_obj(created_embeddings[0])
                    
                    # If this embedding is associated with an item, update the item
                    if item_id:
                        update_item_query = """
                            UPDATE knowledge_item:$item_id
                            SET embedding_id = $embedding_id
                            RETURN NONE;
                        """
                        
                        await self._execute_query(
                            update_item_query,
                            {
                                "item_id": item_id,
                                "embedding_id": created_embedding.id,
                            },
                        )
                    
                    return created_embedding
            
            raise QueryError("Failed to create embedding: No result returned")
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise QueryError(f"Validation error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise QueryError(f"Error creating embedding: {str(e)}")
    
    async def get_embedding(self, embedding_id: str) -> Embedding:
        """
        Retrieve an embedding by ID.
        
        Args:
            embedding_id: ID of the embedding to retrieve
            
        Returns:
            Retrieved embedding
            
        Raises:
            ResourceNotFoundError: If embedding doesn't exist
            QueryError: If retrieval fails
        """
        try:
            query = """
                SELECT * FROM embedding:$id;
            """
            
            result = await self._execute_query(query, {"id": embedding_id})
            
            # Extract the embedding from the result
            if result and len(result) > 0 and "result" in result[0]:
                embeddings = result[0]["result"]
                if embeddings and len(embeddings) > 0:
                    return Embedding.parse_obj(embeddings[0])
            
            raise ResourceNotFoundError(f"Embedding not found: {embedding_id}")
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise QueryError(f"Validation error: {str(e)}")
        
        except ResourceNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error retrieving embedding: {str(e)}")
            raise QueryError(f"Error retrieving embedding: {str(e)}")
    
    async def get_item_embedding(self, item_id: str) -> Optional[Embedding]:
        """
        Retrieve the embedding associated with a knowledge item.
        
        Args:
            item_id: ID of the knowledge item
            
        Returns:
            Associated embedding or None if no embedding exists
            
        Raises:
            ResourceNotFoundError: If item doesn't exist
            QueryError: If retrieval fails
        """
        try:
            # First get the item to check if it exists and has an embedding
            item = await self.get_knowledge_item(item_id)
            
            if not item.embedding_id:
                return None
            
            # Get the embedding
            return await self.get_embedding(item.embedding_id)
        
        except ResourceNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error retrieving item embedding: {str(e)}")
            raise QueryError(f"Error retrieving item embedding: {str(e)}")
    
    async def delete_embedding(self, embedding_id: str) -> bool:
        """
        Delete an embedding by ID.
        
        Args:
            embedding_id: ID of the embedding to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            ResourceNotFoundError: If embedding doesn't exist
            QueryError: If deletion fails
        """
        try:
            # First check if the embedding exists
            embedding = await self.get_embedding(embedding_id)
            
            # If the embedding is associated with an item, update the item
            if embedding.item_id:
                update_item_query = """
                    UPDATE knowledge_item:$item_id
                    SET embedding_id = NULL
                    RETURN NONE;
                """
                
                await self._execute_query(
                    update_item_query,
                    {"item_id": embedding.item_id},
                )
            
            # Delete the embedding
            query = """
                DELETE embedding:$id;
            """
            
            result = await self._execute_query(query, {"id": embedding_id})
            
            # Check if deletion was successful
            if result and len(result) > 0 and "result" in result[0]:
                return True
            
            return False
        
        except ResourceNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error deleting embedding: {str(e)}")
            raise QueryError(f"Error deleting embedding: {str(e)}")
    
    # Relationship Operations
    
    async def create_relationship(self, relationship: Relationship) -> Relationship:
        """
        Create a relationship between knowledge items.
        
        Args:
            relationship: Relationship to create
            
        Returns:
            Created relationship
            
        Raises:
            ResourceNotFoundError: If source or target items don't exist
            QueryError: If creation fails
        """
        try:
            # Check if source and target items exist
            await self.get_knowledge_item(relationship.source_id)
            await self.get_knowledge_item(relationship.target_id)
            
            # Create the relationship using SurrealDB's graph RELATE statement
            # Reference: https://surrealdb.com/docs/surrealql/statements/relate
            # This creates a graph edge between two knowledge items
            query = """
                RELATE 
                    knowledge_item:$source_id 
                    ->$rel_type-> 
                    knowledge_item:$target_id
                CONTENT {
                    weight: $weight,
                    metadata: $metadata
                }
                RETURN AFTER;
            """
            
            params = {
                "source_id": relationship.source_id,
                "rel_type": relationship.type,
                "target_id": relationship.target_id,
                "weight": relationship.weight,
                "metadata": relationship.metadata,
            }
            
            result = await self._execute_query(query, params)
            
            # Extract the created relationship from the result
            if result and len(result) > 0 and "result" in result[0]:
                created_rels = result[0]["result"]
                if created_rels and len(created_rels) > 0:
                    # Add the relationship to the source item's related list
                    update_query = """
                        UPDATE knowledge_item:$id
                        SET related = array::append(related, $rel)
                        RETURN NONE;
                    """
                    
                    rel_data = relationship.dict()
                    
                    await self._execute_query(
                        update_query,
                        {
                            "id": relationship.source_id,
                            "rel": rel_data,
                        },
                    )
                    
                    return relationship
            
            raise QueryError("Failed to create relationship")
        
        except ResourceNotFoundError as e:
            raise
        
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            raise QueryError(f"Error creating relationship: {str(e)}")
    
    async def get_item_relationships(
        self, item_id: str, direction: str = "outgoing"
    ) -> List[Relationship]:
        """
        Get relationships for a knowledge item.
        
        Args:
            item_id: ID of the knowledge item
            direction: "outgoing", "incoming", or "both"
            
        Returns:
            List of relationships
            
        Raises:
            ResourceNotFoundError: If item doesn't exist
            QueryError: If retrieval fails
            ValueError: If direction is invalid
        """
        try:
            # Check if the item exists
            await self.get_knowledge_item(item_id)
            
            if direction not in ["outgoing", "incoming", "both"]:
                raise ValueError(f"Invalid direction: {direction}")
            
            relationships = []
            
            # Get outgoing relationships
            if direction in ["outgoing", "both"]:
                outgoing_query = """
                    SELECT ->* AS relationships 
                    FROM knowledge_item:$id;
                """
                
                outgoing_result = await self._execute_query(outgoing_query, {"id": item_id})
                
                if (outgoing_result and len(outgoing_result) > 0 and 
                    "result" in outgoing_result[0] and outgoing_result[0]["result"]):
                    
                    outgoing_data = outgoing_result[0]["result"][0].get("relationships", [])
                    
                    for rel in outgoing_data:
                        rel_data = {
                            "type": rel.get("type", ""),
                            "source_id": item_id,
                            "target_id": rel.get("in", "").split(":")[1],
                            "weight": rel.get("weight", 1.0),
                            "metadata": rel.get("metadata", {}),
                        }
                        relationships.append(Relationship.parse_obj(rel_data))
            
            # Get incoming relationships
            if direction in ["incoming", "both"]:
                incoming_query = """
                    SELECT <-* AS relationships 
                    FROM knowledge_item:$id;
                """
                
                incoming_result = await self._execute_query(incoming_query, {"id": item_id})
                
                if (incoming_result and len(incoming_result) > 0 and 
                    "result" in incoming_result[0] and incoming_result[0]["result"]):
                    
                    incoming_data = incoming_result[0]["result"][0].get("relationships", [])
                    
                    for rel in incoming_data:
                        rel_data = {
                            "type": rel.get("type", ""),
                            "source_id": rel.get("out", "").split(":")[1],
                            "target_id": item_id,
                            "weight": rel.get("weight", 1.0),
                            "metadata": rel.get("metadata", {}),
                        }
                        relationships.append(Relationship.parse_obj(rel_data))
            
            return relationships
        
        except ResourceNotFoundError:
            raise
        
        except ValueError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting item relationships: {str(e)}")
            raise QueryError(f"Error getting item relationships: {str(e)}")
    
    async def delete_relationship(
        self, source_id: str, target_id: str, rel_type: str
    ) -> bool:
        """
        Delete a relationship between knowledge items.
        
        Args:
            source_id: ID of the source item
            target_id: ID of the target item
            rel_type: Type of the relationship
            
        Returns:
            True if deletion was successful
            
        Raises:
            QueryError: If deletion fails
        """
        try:
            # Delete the relationship
            query = """
                DELETE 
                    knowledge_item:$source_id
                    ->$rel_type->
                    knowledge_item:$target_id;
            """
            
            params = {
                "source_id": source_id,
                "rel_type": rel_type,
                "target_id": target_id,
            }
            
            result = await self._execute_query(query, params)
            
            # Update the source item's related list
            update_query = """
                UPDATE knowledge_item:$id
                SET related = array::filter(related, function($rel) {
                    return !($rel.source_id == $source_id 
                        AND $rel.target_id == $target_id 
                        AND $rel.type == $rel_type);
                })
                RETURN NONE;
            """
            
            await self._execute_query(
                update_query,
                {
                    "id": source_id,
                    "source_id": source_id,
                    "target_id": target_id,
                    "rel_type": rel_type,
                },
            )
            
            # Check if deletion was successful
            if result and len(result) > 0:
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error deleting relationship: {str(e)}")
            raise QueryError(f"Error deleting relationship: {str(e)}")
    
    # Semantic Search (interface only)
    
    async def semantic_search(
        self,
        query_vector: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        filter_tags: Optional[List[str]] = None,
        filter_content_type: Optional[str] = None,
    ) -> List[Tuple[KnowledgeItem, float]]:
        """
        Perform semantic search on knowledge items using SurrealDB's vector search capabilities.
        
        This method uses the fn::similarity_search function defined in the database
        and applies additional filtering based on tags and content_type.
        
        Args:
            query_vector: Vector representation of the query
            limit: Maximum number of results to return
            threshold: Minimum similarity score threshold
            filter_tags: Optional list of tags to filter by
            filter_content_type: Optional content type to filter by
            
        Returns:
            List of tuples containing knowledge items and their similarity scores
            
        Raises:
            QueryError: If search execution fails
        """
        try:
            # Start with the base query using SurrealDB's vector search capabilities
            # Reference: https://surrealdb.com/docs/surrealql/functions/vector
            # This uses SurrealDB's built-in similarity search function
            base_query = """
                LET $results = fn::similarity_search($query_vector, $limit, $threshold);
            """
            
            # If we have filters, we need to filter the results after
            if filter_tags or filter_content_type:
                filter_query = """
                    LET $filtered = SELECT *
                    FROM $results
                """
                
                conditions = []
                params = {
                    "query_vector": query_vector,
                    "limit": limit,
                    "threshold": threshold,
                }
                
                # Add tag filters
                if filter_tags:
                    tags_conditions = []
                    for i, tag in enumerate(filter_tags):
                        param_name = f"tag_{i}"
                        tags_conditions.append(f"$tag_{i} INSIDE tags")
                        params[param_name] = tag
                    
                    if tags_conditions:
                        conditions.append(f"({' AND '.join(tags_conditions)})")
                
                # Add content_type filter
                if filter_content_type:
                    conditions.append("content_type = $content_type")
                    params["content_type"] = filter_content_type
                
                # Add WHERE clause if there are conditions
                if conditions:
                    filter_query += f" WHERE {' AND '.join(conditions)}"
                
                # Complete the query with ordering and final return
                complete_query = f"""
                    {base_query}
                    {filter_query}
                    ORDER BY score DESC
                    LIMIT $limit;
                    
                    RETURN $filtered;
                """
            else:
                # If no filters, just return the similarity search results
                complete_query = f"""
                    {base_query}
                    RETURN $results;
                """
                params = {
                    "query_vector": query_vector,
                    "limit": limit,
                    "threshold": threshold,
                }
            
            # Execute the query
            result = await self._execute_query(complete_query, params)
            
            # Extract and parse the results
            items_with_scores = []
            if result and len(result) > 0 and "result" in result[0]:
                search_results = result[0]["result"]
                if search_results and len(search_results) > 0:
                    for item_data in search_results:
                        # Extract the score from the result
                        score = item_data.pop("score", 0.0)
                        
                        # Parse the knowledge item
                        try:
                            knowledge_item = KnowledgeItem.parse_obj(item_data)
                            items_with_scores.append((knowledge_item, score))
                        except ValidationError as e:
                            logger.warning(f"Failed to parse knowledge item: {str(e)}")
                            continue
            
            return items_with_scores
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise QueryError(f"Validation error in semantic search: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            raise QueryError(f"Error in semantic search: {str(e)}")
    
    # Custom Query Execution
    
    async def execute_custom_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Execute a custom SurrealQL query.
        
        Args:
            query: SurrealQL query string
            params: Optional parameters for the query
            
        Returns:
            List of query results
            
        Raises:
            QueryError: If query execution fails
        """
        return await self._execute_query(query, params)
    
    async def query(self, query_str: str, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Execute a raw SurrealQL query.
        
        Args:
            query_str: SurrealQL query string
            params: Optional parameters for the query
            
        Returns:
            List of query results
            
        Raises:
            QueryError: If query execution fails
        """
        await self._ensure_connected()
        return await self.client.query(query_str, params)