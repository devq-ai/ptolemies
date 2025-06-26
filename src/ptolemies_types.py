#!/usr/bin/env python3
"""
Ptolemies MCP Server - Type Definitions
======================================

Type definitions, Pydantic models, and schemas for the unified
ptolemies MCP server providing access to SurrealDB, Neo4j, and
Dehallucinator services.
"""

from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class FrameworkType(str, Enum):
    """Framework categorization types."""
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    TOOL = "tool"
    LIBRARY = "library"


class ConfidenceLevel(str, Enum):
    """Confidence levels for validation results."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RelationshipType(str, Enum):
    """Neo4j relationship types."""
    IMPLEMENTS = "IMPLEMENTS"
    DEPENDS_ON = "DEPENDS_ON"
    DOCUMENTED_BY = "DOCUMENTED_BY"
    CONTAINS = "CONTAINS"
    RELATED_TO = "RELATED_TO"
    INHERITS_FROM = "INHERITS_FROM"
    USES = "USES"


# === Base Models ===

class BaseResponse(BaseModel):
    """Base response model for all ptolemies MCP tools."""
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "ptolemies-mcp"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = False
    error_type: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None


# === Framework Models ===

class Framework(BaseModel):
    """Framework information from Neo4j knowledge graph."""
    name: str
    type: FrameworkType
    language: str
    description: Optional[str] = None
    version: Optional[str] = None
    documentation_url: Optional[str] = None
    github_url: Optional[str] = None


class FrameworkRelationship(BaseModel):
    """Framework relationship information."""
    source_framework: str
    target_framework: str
    relationship_type: RelationshipType
    description: Optional[str] = None
    strength: Optional[float] = Field(None, ge=0.0, le=1.0)


# === Knowledge Search Models ===

class KnowledgeChunk(BaseModel):
    """Document chunk from SurrealDB vector store."""
    id: str
    content: str
    source: str
    topic: str
    framework: Optional[str] = None
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class GraphNode(BaseModel):
    """Neo4j graph node representation."""
    id: str
    labels: List[str]
    properties: Dict[str, Any]


class GraphRelationship(BaseModel):
    """Neo4j graph relationship representation."""
    id: str
    type: str
    start_node: str
    end_node: str
    properties: Optional[Dict[str, Any]] = None


class HybridSearchResult(BaseResponse):
    """Result from hybrid knowledge search."""
    query: str
    total_results: int
    vector_results: List[KnowledgeChunk]
    graph_results: List[GraphNode]
    combined_results: List[Dict[str, Any]]
    frameworks_found: List[str]
    topics_found: List[str]
    search_metadata: Dict[str, Any]


# === Code Validation Models ===

class HallucinationIssue(BaseModel):
    """Individual hallucination issue detected."""
    type: str
    line: Optional[int] = None
    code: Optional[str] = None
    framework: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    severity: ValidationSeverity
    description: str
    suggestion: Optional[str] = None


class CodeValidationResult(BaseResponse):
    """Code validation result from dehallucinator."""
    code_snippet: str
    is_valid: bool
    overall_confidence: float = Field(ge=0.0, le=1.0)
    frameworks_detected: List[str]
    issues: List[HallucinationIssue]
    patterns_detected: List[str]
    suggestions: List[str]
    analysis_metadata: Dict[str, Any]


class FrameworkUsageAnalysis(BaseResponse):
    """Framework usage pattern analysis."""
    code_snippet: str
    frameworks_used: List[str]
    usage_patterns: List[Dict[str, Any]]
    best_practices: List[str]
    potential_issues: List[str]
    improvement_suggestions: List[str]
    confidence_score: float = Field(ge=0.0, le=1.0)


# === Relationship Discovery Models ===

class DependencyNode(BaseModel):
    """Framework dependency node."""
    framework: str
    version: Optional[str] = None
    dependency_type: str
    is_direct: bool = True
    depth: int = 0


class DependencyGraph(BaseResponse):
    """Framework dependency analysis result."""
    root_framework: str
    total_dependencies: int
    direct_dependencies: int
    transitive_dependencies: int
    dependency_nodes: List[DependencyNode]
    dependency_relationships: List[FrameworkRelationship]
    circular_dependencies: List[List[str]]
    analysis_depth: int


class TopicRelationship(BaseModel):
    """Topic relationship information."""
    source_topic: str
    target_topic: str
    relationship_strength: float = Field(ge=0.0, le=1.0)
    relationship_type: str
    shared_frameworks: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


class TopicAnalysis(BaseResponse):
    """Topic relationship analysis result."""
    topic: str
    related_topics: List[TopicRelationship]
    frameworks_associated: List[str]
    documentation_coverage: float = Field(ge=0.0, le=1.0)
    knowledge_density: float = Field(ge=0.0, le=1.0)


# === Learning Path Models ===

class LearningStep(BaseModel):
    """Individual step in a learning path."""
    step_number: int
    framework: str
    topic: str
    description: str
    prerequisites: List[str]
    resources: List[str]
    estimated_time: Optional[str] = None
    difficulty_level: str


class LearningPath(BaseResponse):
    """Learning path discovery result."""
    start_framework: str
    end_framework: str
    path_length: int
    total_steps: int
    estimated_duration: Optional[str] = None
    difficulty_rating: str
    learning_steps: List[LearningStep]
    alternative_paths: List[Dict[str, Any]]
    prerequisites: List[str]


# === Meta-Analysis Models ===

class CoverageMetrics(BaseModel):
    """Knowledge coverage metrics for a framework."""
    framework: str
    total_documentation_chunks: int
    unique_topics_covered: int
    average_quality_score: float = Field(ge=0.0, le=1.0)
    documentation_completeness: float = Field(ge=0.0, le=1.0)
    last_updated: Optional[datetime] = None


class KnowledgeGap(BaseModel):
    """Identified knowledge gap in documentation."""
    framework: str
    topic: str
    gap_type: str
    severity: ValidationSeverity
    description: str
    suggested_resources: List[str]


class CoverageAnalysis(BaseResponse):
    """Knowledge coverage analysis result."""
    framework: str
    coverage_metrics: CoverageMetrics
    knowledge_gaps: List[KnowledgeGap]
    comparison_frameworks: List[Dict[str, Any]]
    recommendations: List[str]


class EcosystemStats(BaseModel):
    """DevQ.ai ecosystem statistics."""
    total_frameworks: int
    frameworks_by_type: Dict[FrameworkType, int]
    total_relationships: int
    relationships_by_type: Dict[RelationshipType, int]
    total_documentation_chunks: int
    average_quality_score: float = Field(ge=0.0, le=1.0)
    most_connected_frameworks: List[str]
    trending_topics: List[str]


class EcosystemOverview(BaseResponse):
    """Complete ecosystem overview."""
    stats: EcosystemStats
    featured_frameworks: List[Framework]
    framework_categories: Dict[str, List[str]]
    learning_paths: List[Dict[str, Any]]
    recent_updates: List[Dict[str, Any]]
    health_metrics: Dict[str, Any]


# === Tool Input Models ===

class HybridSearchInput(BaseModel):
    """Input for hybrid knowledge search."""
    query: str = Field(..., description="Search query")
    frameworks: Optional[List[str]] = Field(None, description="Filter by specific frameworks")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of results")
    include_code_examples: bool = Field(True, description="Include code examples in results")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class FrameworkQueryInput(BaseModel):
    """Input for framework knowledge query."""
    framework: str = Field(..., description="Framework name")
    topic: str = Field(..., description="Topic to query")
    depth: int = Field(2, ge=1, le=5, description="Relationship traversal depth")
    include_examples: bool = Field(True, description="Include code examples")


class CodeValidationInput(BaseModel):
    """Input for code validation."""
    code: str = Field(..., description="Code snippet to validate")
    framework: Optional[str] = Field(None, description="Expected framework context")
    confidence_threshold: float = Field(0.75, ge=0.0, le=1.0, description="Minimum confidence for issues")
    include_suggestions: bool = Field(True, description="Include improvement suggestions")


class DependencyAnalysisInput(BaseModel):
    """Input for dependency analysis."""
    framework: str = Field(..., description="Framework to analyze")
    include_transitive: bool = Field(False, description="Include transitive dependencies")
    max_depth: int = Field(3, ge=1, le=10, description="Maximum traversal depth")


class LearningPathInput(BaseModel):
    """Input for learning path discovery."""
    start_framework: str = Field(..., description="Starting framework")
    end_framework: str = Field(..., description="Target framework")
    include_prerequisites: bool = Field(True, description="Include prerequisite analysis")
    difficulty_preference: Optional[str] = Field(None, description="Preferred difficulty level")


# === Response Union Types ===

PtolemiesResponse = Union[
    HybridSearchResult,
    CodeValidationResult,
    FrameworkUsageAnalysis,
    DependencyGraph,
    TopicAnalysis,
    LearningPath,
    CoverageAnalysis,
    EcosystemOverview,
    ErrorResponse
]

# === Utility Types ===

class ConnectionStatus(BaseModel):
    """Database connection status."""
    service: str
    connected: bool
    last_ping: Optional[datetime] = None
    error_message: Optional[str] = None


class SystemHealth(BaseModel):
    """Overall system health status."""
    neo4j_status: ConnectionStatus
    surrealdb_status: ConnectionStatus
    dehallucinator_status: ConnectionStatus
    overall_healthy: bool
    last_check: datetime = Field(default_factory=datetime.now)
