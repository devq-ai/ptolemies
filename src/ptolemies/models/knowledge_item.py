"""
Pydantic models for the Ptolemies Knowledge Base system.

This module defines the core data models used in the Ptolemies system, 
including knowledge items, embeddings, and relationships between items.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class Relationship(BaseModel):
    """
    Represents a relationship between knowledge items.
    
    Relationships form the graph structure of the knowledge base,
    connecting items with typed, weighted edges.
    """
    type: str = Field(..., description="Relationship type (e.g., 'related_to', 'references', 'part_of')")
    source_id: str = Field(..., description="ID of the source knowledge item")
    target_id: str = Field(..., description="ID of the target knowledge item")
    weight: float = Field(1.0, description="Relationship strength (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the relationship")
    
    @validator('weight')
    def validate_weight(cls, v):
        """Ensure weight is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Weight must be between 0.0 and 1.0")
        return v


class Embedding(BaseModel):
    """
    Represents a vector embedding for a knowledge item.
    
    Embeddings are high-dimensional vector representations of content
    that enable semantic search and similarity comparisons.
    """
    id: Optional[str] = Field(None, description="Unique identifier for the embedding")
    vector: List[float] = Field(..., description="Vector representation of the content")
    model: str = Field(..., description="Name of the embedding model used (e.g., 'text-embedding-ada-002')")
    dimensions: int = Field(..., description="Number of dimensions in the vector")
    item_id: Optional[str] = Field(None, description="ID of the associated knowledge item")
    created_at: Optional[datetime] = Field(None, description="Timestamp when the embedding was created")
    
    @validator('dimensions')
    def validate_dimensions(cls, v, values):
        """Ensure dimensions match the vector length."""
        if 'vector' in values and v != len(values['vector']):
            raise ValueError(f"Dimensions ({v}) doesn't match vector length ({len(values['vector'])})")
        return v


class KnowledgeItem(BaseModel):
    """
    Represents a knowledge item in the Ptolemies Knowledge Base.
    
    A knowledge item is the core entity of the system, containing
    content along with metadata, tags, and references to related items.
    """
    id: Optional[str] = Field(None, description="Unique identifier")
    title: str = Field(..., description="Item title")
    content: str = Field(..., description="Primary content (text)")
    content_type: str = Field("text/plain", description="Type of content (e.g., 'text/plain', 'text/markdown', 'code/python')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Flexible metadata")
    tags: List[str] = Field(default_factory=list, description="List of tags")
    embedding_id: Optional[str] = Field(None, description="Reference to vector embedding")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    version: int = Field(1, description="Version number")
    source: Optional[str] = Field(None, description="Origin of the content")
    related: List[Relationship] = Field(default_factory=list, description="Graph relationships")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        """Ensure content_type follows the format 'category/subcategory'."""
        if '/' not in v:
            raise ValueError("Content type should follow format 'category/subcategory'")
        return v


class KnowledgeItemCreate(BaseModel):
    """
    Schema for creating a new knowledge item.
    
    This model omits auto-generated fields like id, created_at, updated_at.
    """
    title: str = Field(..., description="Item title")
    content: str = Field(..., description="Primary content (text)")
    content_type: str = Field("text/plain", description="Type of content (e.g., 'text/plain', 'text/markdown', 'code/python')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Flexible metadata")
    tags: List[str] = Field(default_factory=list, description="List of tags")
    source: Optional[str] = Field(None, description="Origin of the content")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        """Ensure content_type follows the format 'category/subcategory'."""
        if '/' not in v:
            raise ValueError("Content type should follow format 'category/subcategory'")
        return v


class KnowledgeItemUpdate(BaseModel):
    """
    Schema for updating an existing knowledge item.
    
    All fields are optional since updates may be partial.
    """
    title: Optional[str] = Field(None, description="Item title")
    content: Optional[str] = Field(None, description="Primary content (text)")
    content_type: Optional[str] = Field(None, description="Type of content (e.g., 'text/plain', 'text/markdown', 'code/python')")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Flexible metadata")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    source: Optional[str] = Field(None, description="Origin of the content")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        """Ensure content_type follows the format 'category/subcategory'."""
        if v is not None and '/' not in v:
            raise ValueError("Content type should follow format 'category/subcategory'")
        return v