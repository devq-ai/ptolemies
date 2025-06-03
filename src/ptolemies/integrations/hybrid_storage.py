"""
Hybrid Storage Manager for Ptolemies Knowledge Base.

This module coordinates between SurrealDB (document storage) and Graphiti (temporal
knowledge graph) to provide unified knowledge management with both structured
storage and sophisticated relationship discovery.

Architecture:
- SurrealDB: Primary document storage, metadata, search indices
- Graphiti: Temporal relationship extraction, graph reasoning, visualization
- Hybrid Manager: Coordinated operations, cross-system references, unified queries

The hybrid approach leverages the strengths of both systems:
- SurrealDB's multi-model capabilities for fast document retrieval
- Graphiti's temporal reasoning for relationship discovery and evolution tracking

References:
- Hybrid Database Architecture: https://en.wikipedia.org/wiki/Polyglot_persistence
- Event Sourcing Patterns: https://martinfowler.com/eaaDev/EventSourcing.html
- CQRS Implementation: https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone
from uuid import uuid4

from ..db.surrealdb_client import SurrealDBClient, ResourceNotFoundError, QueryError
from ..models.knowledge_item import KnowledgeItem, KnowledgeItemCreate, KnowledgeItemUpdate
from .graphiti.service_wrapper import GraphitiServiceClient, GraphitiServiceConfig

# Configure logging
logger = logging.getLogger(__name__)

class HybridSearchResult:
    """Result from hybrid search across both storage systems."""
    
    def __init__(
        self,
        documents: List[KnowledgeItem],
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        query: str,
        processing_time: float
    ):
        self.documents = documents
        self.entities = entities
        self.relationships = relationships
        self.query = query
        self.processing_time = processing_time
        self.total_results = len(documents) + len(entities) + len(relationships)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "query": self.query,
            "documents": [doc.dict() for doc in self.documents],
            "entities": self.entities,
            "relationships": self.relationships,
            "total_results": self.total_results,
            "processing_time": self.processing_time,
            "sources": {
                "surrealdb_documents": len(self.documents),
                "graphiti_entities": len(self.entities),
                "graphiti_relationships": len(self.relationships)
            }
        }

class HybridKnowledgeManager:
    """
    Hybrid knowledge management system coordinating SurrealDB and Graphiti.
    
    Provides unified interface for:
    - Document storage and retrieval (SurrealDB)
    - Relationship extraction and temporal reasoning (Graphiti)
    - Cross-system referencing and consistency
    - Hybrid search and discovery
    """
    
    def __init__(
        self,
        surrealdb_client: Optional[SurrealDBClient] = None,
        graphiti_config: Optional[GraphitiServiceConfig] = None
    ):
        """
        Initialize the hybrid knowledge manager.
        
        Args:
            surrealdb_client: SurrealDB client instance
            graphiti_config: Graphiti service configuration
        """
        self.surrealdb_client = surrealdb_client or SurrealDBClient()
        self.graphiti_client = GraphitiServiceClient(config=graphiti_config)
        
        # Cross-reference tracking
        self._document_to_episode_map: Dict[str, str] = {}
        self._episode_to_document_map: Dict[str, str] = {}
        
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize both storage systems.
        
        Returns:
            True if both systems initialized successfully
        """
        try:
            # Initialize SurrealDB
            await self.surrealdb_client.connect()
            logger.info("SurrealDB client connected")
            
            # Initialize Graphiti service
            success = await self.graphiti_client.start_service()
            if not success:
                logger.warning("Graphiti service failed to start, operating in SurrealDB-only mode")
                
            self._initialized = True
            logger.info("Hybrid knowledge manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid manager: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Close connections to both storage systems."""
        if self.surrealdb_client:
            await self.surrealdb_client.disconnect()
        
        if self.graphiti_client:
            await self.graphiti_client.close()
        
        self._initialized = False
        logger.info("Hybrid knowledge manager closed")
    
    async def _ensure_initialized(self) -> None:
        """Ensure the manager is initialized."""
        if not self._initialized:
            await self.initialize()
    
    # Unified Knowledge Operations
    
    async def store_knowledge_item(
        self,
        item_create: KnowledgeItemCreate,
        extract_relationships: bool = True,
        group_id: Optional[str] = None
    ) -> Tuple[KnowledgeItem, Optional[Dict[str, Any]]]:
        """
        Store knowledge item in both systems with relationship extraction.
        
        Args:
            item_create: Knowledge item to store
            extract_relationships: Whether to extract relationships via Graphiti
            group_id: Optional logical grouping for Graphiti
            
        Returns:
            Tuple of (stored knowledge item, graphiti processing result)
        """
        await self._ensure_initialized()
        
        start_time = time.time()
        
        try:
            # 1. Store document in SurrealDB
            logger.info(f"Storing document: {item_create.title}")
            knowledge_item = await self.surrealdb_client.create_knowledge_item(item_create)
            
            graphiti_result = None
            
            # 2. Process through Graphiti for relationship extraction
            if extract_relationships:
                try:
                    logger.info(f"Processing document {knowledge_item.id} through Graphiti")
                    
                    # Prepare metadata for Graphiti
                    metadata = {
                        "knowledge_item_id": knowledge_item.id,
                        "title": knowledge_item.title,
                        "content_type": knowledge_item.content_type,
                        "tags": knowledge_item.tags,
                        "source": knowledge_item.source,
                        "created_at": knowledge_item.created_at.isoformat() if knowledge_item.created_at else None
                    }
                    
                    # Process through Graphiti
                    graphiti_result = await self.graphiti_client.process_episode(
                        content=knowledge_item.content,
                        metadata=metadata,
                        group_id=group_id or "ptolemies_default"
                    )
                    
                    # 3. Update SurrealDB with Graphiti references
                    if graphiti_result:
                        episode_id = graphiti_result.get("episode_id")
                        
                        update_data = KnowledgeItemUpdate(
                            metadata={
                                **knowledge_item.metadata,
                                "graphiti_episode_id": episode_id,
                                "extracted_entities": len(graphiti_result.get("entities", [])),
                                "extracted_relationships": len(graphiti_result.get("relationships", [])),
                                "processing_time": graphiti_result.get("processing_time", 0)
                            }
                        )
                        
                        knowledge_item = await self.surrealdb_client.update_knowledge_item(
                            knowledge_item.id, update_data
                        )
                        
                        # Track cross-references
                        self._document_to_episode_map[knowledge_item.id] = episode_id
                        self._episode_to_document_map[episode_id] = knowledge_item.id
                        
                        logger.info(f"Cross-referenced document {knowledge_item.id} with episode {episode_id}")
                
                except Exception as e:
                    logger.warning(f"Graphiti processing failed for {knowledge_item.id}: {str(e)}")
                    # Continue without Graphiti processing
            
            processing_time = time.time() - start_time
            logger.info(f"Stored knowledge item {knowledge_item.id} in {processing_time:.2f}s")
            
            return knowledge_item, graphiti_result
            
        except Exception as e:
            logger.error(f"Error storing knowledge item: {str(e)}")
            raise
    
    async def get_knowledge_item(
        self,
        item_id: str,
        include_relationships: bool = False
    ) -> Tuple[KnowledgeItem, Optional[Dict[str, Any]]]:
        """
        Retrieve knowledge item with optional relationship data.
        
        Args:
            item_id: Knowledge item ID
            include_relationships: Whether to fetch Graphiti relationships
            
        Returns:
            Tuple of (knowledge item, optional relationship data)
        """
        await self._ensure_initialized()
        
        try:
            # Get document from SurrealDB
            knowledge_item = await self.surrealdb_client.get_knowledge_item(item_id)
            
            relationship_data = None
            
            # Get relationships from Graphiti if requested
            if include_relationships:
                episode_id = knowledge_item.metadata.get("graphiti_episode_id")
                if episode_id:
                    try:
                        # Search for entities and relationships related to this episode
                        entities = await self.graphiti_client.search_entities(
                            query=knowledge_item.title,
                            limit=20
                        )
                        
                        relationships = await self.graphiti_client.search_relationships(
                            query=knowledge_item.title,
                            limit=20
                        )
                        
                        relationship_data = {
                            "episode_id": episode_id,
                            "entities": entities.get("results", []),
                            "relationships": relationships.get("results", [])
                        }
                        
                    except Exception as e:
                        logger.warning(f"Failed to fetch relationships for {item_id}: {str(e)}")
            
            return knowledge_item, relationship_data
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge item {item_id}: {str(e)}")
            raise
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        include_documents: bool = True,
        include_entities: bool = True,
        include_relationships: bool = True,
        filter_tags: Optional[List[str]] = None
    ) -> HybridSearchResult:
        """
        Perform hybrid search across both SurrealDB and Graphiti.
        
        Args:
            query: Search query text
            limit: Maximum results per source
            include_documents: Search SurrealDB documents
            include_entities: Search Graphiti entities
            include_relationships: Search Graphiti relationships
            filter_tags: Optional tag filtering
            
        Returns:
            Hybrid search results
        """
        await self._ensure_initialized()
        
        start_time = time.time()
        
        documents = []
        entities = []
        relationships = []
        
        try:
            # Parallel search across both systems
            search_tasks = []
            
            # SurrealDB document search
            if include_documents:
                search_tasks.append(
                    self._search_documents(query, limit, filter_tags)
                )
            else:
                search_tasks.append(asyncio.create_task(asyncio.sleep(0, result=[])))
            
            # Graphiti entity search
            if include_entities:
                search_tasks.append(
                    self._search_entities(query, limit)
                )
            else:
                search_tasks.append(asyncio.create_task(asyncio.sleep(0, result=[])))
            
            # Graphiti relationship search
            if include_relationships:
                search_tasks.append(
                    self._search_relationships(query, limit)
                )
            else:
                search_tasks.append(asyncio.create_task(asyncio.sleep(0, result=[])))
            
            # Execute searches in parallel
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results
            if not isinstance(results[0], Exception):
                documents = results[0]
            
            if not isinstance(results[1], Exception):
                entities = results[1]
            
            if not isinstance(results[2], Exception):
                relationships = results[2]
            
            processing_time = time.time() - start_time
            
            result = HybridSearchResult(
                documents=documents,
                entities=entities,
                relationships=relationships,
                query=query,
                processing_time=processing_time
            )
            
            logger.info(
                f"Hybrid search for '{query}' returned {result.total_results} results "
                f"in {processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            raise
    
    async def _search_documents(
        self,
        query: str,
        limit: int,
        filter_tags: Optional[List[str]] = None
    ) -> List[KnowledgeItem]:
        """Search documents in SurrealDB."""
        try:
            # Use SurrealDB's search capabilities
            # This is a simplified search - in practice would use full-text search
            documents = await self.surrealdb_client.list_knowledge_items(
                limit=limit,
                tags=filter_tags
            )
            
            # Filter by query text (basic implementation)
            filtered_docs = []
            query_lower = query.lower()
            
            for doc in documents:
                if (query_lower in doc.title.lower() or 
                    query_lower in doc.content.lower() or
                    any(query_lower in tag.lower() for tag in doc.tags)):
                    filtered_docs.append(doc)
                
                if len(filtered_docs) >= limit:
                    break
            
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    async def _search_entities(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search entities in Graphiti."""
        try:
            result = await self.graphiti_client.search_entities(query, limit)
            return result.get("results", [])
        except Exception as e:
            logger.error(f"Error searching entities: {str(e)}")
            return []
    
    async def _search_relationships(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search relationships in Graphiti."""
        try:
            result = await self.graphiti_client.search_relationships(query, limit)
            return result.get("results", [])
        except Exception as e:
            logger.error(f"Error searching relationships: {str(e)}")
            return []
    
    # Advanced Operations
    
    async def get_knowledge_evolution(
        self,
        concept: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Track how knowledge about a concept evolved over time.
        
        Args:
            concept: Concept to track
            start_time: Optional start time
            end_time: Optional end time
            
        Returns:
            Temporal evolution data
        """
        await self._ensure_initialized()
        
        try:
            # Get temporal evolution from Graphiti
            evolution_data = await self.graphiti_client.get_temporal_evolution(
                entity_name=concept,
                start_time=start_time,
                end_time=end_time
            )
            
            # Enhance with document references from SurrealDB
            # Search for related documents
            related_docs = await self._search_documents(concept, limit=50)
            
            # Group documents by time periods
            doc_timeline = []
            for doc in related_docs:
                if doc.created_at:
                    doc_timeline.append({
                        "timestamp": doc.created_at.isoformat(),
                        "document_id": doc.id,
                        "title": doc.title,
                        "source": doc.source
                    })
            
            # Sort by timestamp
            doc_timeline.sort(key=lambda x: x["timestamp"])
            
            # Combine with Graphiti evolution data
            evolution_data["document_timeline"] = doc_timeline
            evolution_data["total_documents"] = len(related_docs)
            
            return evolution_data
            
        except Exception as e:
            logger.error(f"Error getting knowledge evolution: {str(e)}")
            raise
    
    async def get_graph_visualization(
        self,
        query: str,
        depth: int = 3,
        layout: str = "force"
    ) -> Dict[str, Any]:
        """
        Get graph visualization data from Graphiti.
        
        Args:
            query: Search query for visualization
            depth: Graph traversal depth
            layout: Layout algorithm
            
        Returns:
            Graph visualization data
        """
        await self._ensure_initialized()
        
        try:
            viz_data = await self.graphiti_client.get_graph_visualization(
                query=query,
                depth=depth,
                layout=layout
            )
            
            # Enhance nodes with document references
            for node in viz_data.get("nodes", []):
                node_id = node.get("id")
                
                # Look for related documents
                related_docs = await self._search_documents(node.get("label", ""), limit=5)
                
                if related_docs:
                    node["document_references"] = [
                        {
                            "id": doc.id,
                            "title": doc.title,
                            "url": f"/knowledge/{doc.id}"
                        }
                        for doc in related_docs[:3]  # Limit to top 3
                    ]
            
            return viz_data
            
        except Exception as e:
            logger.error(f"Error getting graph visualization: {str(e)}")
            raise
    
    # Maintenance Operations
    
    async def sync_systems(self) -> Dict[str, Any]:
        """
        Synchronize data between SurrealDB and Graphiti.
        
        Returns:
            Synchronization report
        """
        await self._ensure_initialized()
        
        try:
            # Get all documents from SurrealDB
            documents = await self.surrealdb_client.list_knowledge_items(limit=1000)
            
            sync_report = {
                "total_documents": len(documents),
                "processed": 0,
                "errors": 0,
                "new_episodes": 0,
                "updated_references": 0
            }
            
            for doc in documents:
                try:
                    # Check if document has Graphiti episode
                    episode_id = doc.metadata.get("graphiti_episode_id")
                    
                    if not episode_id:
                        # Process through Graphiti
                        _, graphiti_result = await self.store_knowledge_item(
                            KnowledgeItemCreate(
                                title=doc.title,
                                content=doc.content,
                                content_type=doc.content_type,
                                metadata=doc.metadata,
                                tags=doc.tags,
                                source=doc.source
                            ),
                            extract_relationships=True
                        )
                        
                        if graphiti_result:
                            sync_report["new_episodes"] += 1
                    
                    sync_report["processed"] += 1
                    
                except Exception as e:
                    logger.warning(f"Error syncing document {doc.id}: {str(e)}")
                    sync_report["errors"] += 1
            
            logger.info(f"Synchronization completed: {sync_report}")
            return sync_report
            
        except Exception as e:
            logger.error(f"Error during synchronization: {str(e)}")
            raise
    
    async def cleanup(self, group_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Clean up data in both systems.
        
        Args:
            group_id: Optional group to clean up
            
        Returns:
            Cleanup report
        """
        await self._ensure_initialized()
        
        try:
            cleanup_report = {
                "surrealdb_cleanup": False,
                "graphiti_cleanup": False,
                "cross_references_cleared": 0
            }
            
            # Clean up Graphiti
            try:
                graphiti_result = await self.graphiti_client.cleanup_graph(group_id)
                cleanup_report["graphiti_cleanup"] = graphiti_result.get("success", False)
            except Exception as e:
                logger.warning(f"Graphiti cleanup failed: {str(e)}")
            
            # Clear cross-references
            if group_id is None:
                # Clear all cross-references
                cleanup_report["cross_references_cleared"] = len(self._document_to_episode_map)
                self._document_to_episode_map.clear()
                self._episode_to_document_map.clear()
            
            # Note: SurrealDB cleanup would need specific implementation
            # based on requirements (we typically don't want to delete documents)
            
            logger.info(f"Cleanup completed: {cleanup_report}")
            return cleanup_report
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()