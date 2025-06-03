"""
Graphiti Service Wrapper for Ptolemies Knowledge Base.

This module provides a service wrapper that runs Graphiti in a separate process
to resolve pydantic version conflicts between SurrealDB (<2.0) and Graphiti (>=2.8).

The wrapper communicates via HTTP API and manages the lifecycle of the Graphiti
service, allowing seamless integration despite dependency conflicts.

Architecture:
- Main Ptolemies process (SurrealDB, pydantic 1.x)
- Separate Graphiti process (Neo4j, pydantic 2.x)  
- HTTP API communication between processes
- Shared data serialization using JSON

References:
- Process Communication: https://docs.python.org/3/library/subprocess.html
- FastAPI Service Architecture: https://fastapi.tiangolo.com/
- Microservices Integration: https://microservices.io/patterns/communication-style/messaging.html
"""

import os
import json
import asyncio
import httpx
import logging
import subprocess
import signal
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)

class GraphitiServiceConfig(BaseModel):
    """Configuration for the Graphiti service wrapper."""
    service_host: str = Field(default="localhost", description="Service host")
    service_port: int = Field(default=8001, description="Service port")
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="Ptolemis", description="Neo4j password")
    neo4j_project: str = Field(default="Ptolemis", description="Neo4j project name")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    log_level: str = Field(default="INFO", description="Service log level")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

class GraphitiServiceClient:
    """
    Client for communicating with the Graphiti service.
    
    This client handles all communication with the separate Graphiti process,
    including service lifecycle management, request/response handling, and
    error recovery.
    """
    
    def __init__(self, config: Optional[GraphitiServiceConfig] = None):
        """
        Initialize the Graphiti service client.
        
        Args:
            config: Service configuration
        """
        self.config = config or GraphitiServiceConfig()
        self._load_env_config()
        
        self.base_url = f"http://{self.config.service_host}:{self.config.service_port}"
        self.client = httpx.AsyncClient(timeout=self.config.timeout)
        self._service_process: Optional[subprocess.Popen] = None
        self._service_ready = False
    
    def _load_env_config(self) -> None:
        """Load configuration from environment variables."""
        env_mapping = {
            "NEO4J_URI": "neo4j_uri",
            "NEO4J_USER": "neo4j_user", 
            "NEO4J_PASSWORD": "neo4j_password",
            "NEO4J_PROJECT": "neo4j_project",
            "OPENAI_API_KEY": "openai_api_key",
            "ANTHROPIC_API_KEY": "anthropic_api_key"
        }
        
        for env_var, config_attr in env_mapping.items():
            value = os.getenv(env_var)
            if value:
                setattr(self.config, config_attr, value)
        
        # Convert HTTP URI to Bolt URI if needed
        if self.config.neo4j_uri.startswith("http://"):
            self.config.neo4j_uri = self.config.neo4j_uri.replace("http://", "bolt://").replace(":7474", ":7687")
    
    async def start_service(self) -> bool:
        """
        Start the Graphiti service in a separate process.
        
        Returns:
            True if service started successfully
        """
        if self._service_process and self._service_process.poll() is None:
            logger.info("Graphiti service already running")
            return True
        
        try:
            # Path to the Graphiti virtual environment
            venv_path = Path("/Users/dionedge/devqai/ptolemies/venv_graphiti")
            python_path = venv_path / "bin" / "python3"
            
            if not python_path.exists():
                logger.error(f"Graphiti venv not found at {python_path}")
                return False
            
            # Create the service script path
            service_script = Path(__file__).parent / "graphiti_service.py"
            
            # Environment for the service process
            service_env = os.environ.copy()
            service_env.update({
                "NEO4J_URI": self.config.neo4j_uri,
                "NEO4J_USER": self.config.neo4j_user,
                "NEO4J_PASSWORD": self.config.neo4j_password,
                "NEO4J_PROJECT": self.config.neo4j_project,
                "SERVICE_PORT": str(self.config.service_port),
                "LOG_LEVEL": self.config.log_level
            })
            
            if self.config.openai_api_key:
                service_env["OPENAI_API_KEY"] = self.config.openai_api_key
            if self.config.anthropic_api_key:
                service_env["ANTHROPIC_API_KEY"] = self.config.anthropic_api_key
            
            # Start the service process
            logger.info(f"Starting Graphiti service on port {self.config.service_port}")
            self._service_process = subprocess.Popen(
                [str(python_path), str(service_script)],
                env=service_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group for clean shutdown
            )
            
            # Wait for service to be ready
            await self._wait_for_service_ready()
            
            if self._service_ready:
                logger.info("Graphiti service started successfully")
                return True
            else:
                logger.error("Graphiti service failed to start")
                await self.stop_service()
                return False
                
        except Exception as e:
            logger.error(f"Error starting Graphiti service: {str(e)}")
            return False
    
    async def _wait_for_service_ready(self, max_wait: int = 30) -> None:
        """Wait for the service to become ready."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = await self.client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    self._service_ready = True
                    return
            except Exception:
                pass  # Service not ready yet
            
            await asyncio.sleep(1)
        
        logger.error("Service did not become ready within timeout")
    
    async def stop_service(self) -> None:
        """Stop the Graphiti service process."""
        if self._service_process:
            try:
                # Send SIGTERM to the process group
                os.killpg(os.getpgid(self._service_process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self._service_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if not shutdown gracefully
                    os.killpg(os.getpgid(self._service_process.pid), signal.SIGKILL)
                
                logger.info("Graphiti service stopped")
                
            except Exception as e:
                logger.error(f"Error stopping Graphiti service: {str(e)}")
            
            finally:
                self._service_process = None
                self._service_ready = False
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to the Graphiti service with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "GET":
                    response = await self.client.get(url, params=params)
                elif method.upper() == "POST":
                    response = await self.client.post(url, json=data, params=params)
                elif method.upper() == "PUT":
                    response = await self.client.put(url, json=data, params=params)
                elif method.upper() == "DELETE":
                    response = await self.client.delete(url, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.RequestError as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.config.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise
    
    # API Methods for Graphiti operations
    
    async def process_episode(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process content through Graphiti for relationship extraction.
        
        Args:
            content: Text content to process
            metadata: Optional metadata
            group_id: Optional logical grouping
            
        Returns:
            Processing results
        """
        data = {
            "content": content,
            "metadata": metadata or {},
            "group_id": group_id or "default"
        }
        
        return await self._make_request("POST", "/episodes", data=data)
    
    async def search_entities(
        self,
        query: str,
        limit: int = 10,
        group_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for entities in the knowledge graph.
        
        Args:
            query: Search query
            limit: Maximum results
            group_ids: Optional group filtering
            
        Returns:
            Search results
        """
        params = {
            "query": query,
            "limit": limit
        }
        
        if group_ids:
            params["group_ids"] = ",".join(group_ids)
        
        return await self._make_request("GET", "/entities/search", params=params)
    
    async def search_relationships(
        self,
        query: str,
        limit: int = 10,
        group_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for relationships in the knowledge graph.
        
        Args:
            query: Search query
            limit: Maximum results
            group_ids: Optional group filtering
            
        Returns:
            Search results
        """
        params = {
            "query": query,
            "limit": limit
        }
        
        if group_ids:
            params["group_ids"] = ",".join(group_ids)
        
        return await self._make_request("GET", "/relationships/search", params=params)
    
    async def get_graph_visualization(
        self,
        query: str,
        depth: int = 3,
        layout: str = "force"
    ) -> Dict[str, Any]:
        """
        Get graph visualization data.
        
        Args:
            query: Search query
            depth: Graph depth
            layout: Layout algorithm
            
        Returns:
            Visualization data
        """
        params = {
            "query": query,
            "depth": depth,
            "layout": layout
        }
        
        return await self._make_request("GET", "/graph/visualize", params=params)
    
    async def get_temporal_evolution(
        self,
        entity_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get temporal evolution of an entity.
        
        Args:
            entity_name: Entity to track
            start_time: Optional start time
            end_time: Optional end time
            
        Returns:
            Temporal evolution data
        """
        params = {"entity_name": entity_name}
        
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()
        
        return await self._make_request("GET", "/temporal/evolution", params=params)
    
    async def cleanup_graph(self, group_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Clean up graph data.
        
        Args:
            group_id: Optional group to clean
            
        Returns:
            Cleanup results
        """
        params = {}
        if group_id:
            params["group_id"] = group_id
        
        return await self._make_request("DELETE", "/graph/cleanup", params=params)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return await self._make_request("GET", "/health")
    
    async def close(self) -> None:
        """Close the client and stop the service."""
        await self.client.aclose()
        await self.stop_service()
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        success = await self.start_service()
        if not success:
            raise RuntimeError("Failed to start Graphiti service")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()