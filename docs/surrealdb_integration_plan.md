# SurrealDB Integration Action Plan

## Immediate Fixes (Next 48 Hours)

### 1. Implement Bulk Insert Operation

```python
async def bulk_insert_to_surrealdb(pages: List[Dict[str, Any]], target_info: Dict[str, Any]) -> int:
    """Insert multiple knowledge items in a single database transaction."""
    db = await connect_to_surrealdb()
    if not db:
        logger.error("Cannot push to SurrealDB: connection failed")
        return 0
    
    try:
        # Prepare all items first
        items = []
        for page in pages:
            url = page.get("url", "")
            url_hash = url.replace(":", "_").replace("/", "_").replace(".", "_")
            item_id = f"knowledge_item:url_{url_hash}"
            
            # Prepare tags and metadata
            parsed_url = urlparse(url)
            tags = target_info.get("tags", []).copy()
            tags.extend([f"depth:{page.get('depth', 0)}", "web-crawl", f"domain:{parsed_url.netloc.replace('.', '-')}"])
            
            # Create item data
            items.append({
                "id": item_id,
                "title": page.get("title", "No title"),
                "content": f"Content from URL: {url}",
                "content_type": "text/markdown",
                "source": url,
                "source_type": "web",
                "category": target_info.get("category", "Web Crawl"),
                "embedding_id": "",
                "version": 1,
                "tags": tags,
                "metadata": {
                    "depth": page.get("depth", 0),
                    "domain": parsed_url.netloc,
                    "path": parsed_url.path,
                    "crawl_date": datetime.now().isoformat(),
                    "target_name": target_info.get("name", ""),
                    "target_url": target_info.get("url", ""),
                    "target_category": target_info.get("category", ""),
                }
            })
        
        # Build a single transaction with all inserts
        transaction_queries = []
        for idx, item in enumerate(items):
            item_id = item.pop("id")
            transaction_queries.append(f"CREATE {item_id} CONTENT $item{idx};")
        
        # Execute the transaction
        query = "BEGIN TRANSACTION;\n" + "\n".join(transaction_queries) + "\nCOMMIT TRANSACTION;"
        
        # Prepare parameters for all items
        params = {}
        for idx, item in enumerate(items):
            params[f"item{idx}"] = item
        
        # Execute transaction
        result = await db.query(query, params)
        logger.info(f"Bulk inserted {len(items)} items")
        
        return len(items)
    
    except Exception as e:
        logger.error(f"Error in bulk insert: {e}")
        return 0
    
    finally:
        await db.close()
```

### 2. Add Error Recovery and Retry Logic

```python
async def push_to_surrealdb_with_recovery(pages: List[Dict[str, Any]], target_info: Dict[str, Any]]) -> int:
    """Push crawled URLs to SurrealDB with error recovery."""
    # Split pages into manageable batches (100 at a time)
    batch_size = 100
    batches = [pages[i:i + batch_size] for i in range(0, len(pages), batch_size)]
    
    success_count = 0
    failed_pages = []
    
    for batch_num, batch in enumerate(batches):
        logger.info(f"Processing batch {batch_num+1}/{len(batches)} ({len(batch)} pages)")
        
        try:
            # Try bulk insert first
            batch_success = await bulk_insert_to_surrealdb(batch, target_info)
            
            if batch_success == len(batch):
                success_count += batch_success
                logger.info(f"Batch {batch_num+1} completed successfully")
            else:
                # If bulk fails, try individual inserts
                logger.warning(f"Bulk insert partially failed, trying individual inserts")
                for page in batch:
                    try:
                        success = await insert_single_page(page, target_info)
                        if success:
                            success_count += 1
                        else:
                            failed_pages.append(page)
                    except Exception as e:
                        logger.error(f"Error inserting page {page.get('url')}: {e}")
                        failed_pages.append(page)
        
        except Exception as e:
            logger.error(f"Error processing batch {batch_num+1}: {e}")
            failed_pages.extend(batch)
    
    # Write failed pages to file for later recovery
    if failed_pages:
        with open("failed_pages.json", "w") as f:
            json.dump(failed_pages, f)
        logger.warning(f"Saved {len(failed_pages)} failed pages to failed_pages.json")
    
    return success_count
```

### 3. Add Performance Monitoring

```python
class PerformanceMonitor:
    """Monitor performance of database operations."""
    
    def __init__(self):
        self.start_time = None
        self.operation_counts = {}
        self.error_counts = {}
        self.timings = {}
    
    def start_operation(self, operation_name: str):
        """Start timing an operation."""
        self.start_time = time.time()
        self.operation_counts[operation_name] = self.operation_counts.get(operation_name, 0) + 1
    
    def end_operation(self, operation_name: str, success: bool = True):
        """End timing an operation."""
        if self.start_time:
            duration = time.time() - self.start_time
            if operation_name not in self.timings:
                self.timings[operation_name] = []
            self.timings[operation_name].append(duration)
            
            if not success:
                self.error_counts[operation_name] = self.error_counts.get(operation_name, 0) + 1
            
            self.start_time = None
    
    def report(self):
        """Generate a performance report."""
        report = {
            "operations": {},
            "summary": {
                "total_operations": sum(self.operation_counts.values()),
                "total_errors": sum(self.error_counts.values()),
                "success_rate": (1 - sum(self.error_counts.values()) / sum(self.operation_counts.values())) * 100 if sum(self.operation_counts.values()) > 0 else 0,
            }
        }
        
        for op_name in self.operation_counts:
            report["operations"][op_name] = {
                "count": self.operation_counts[op_name],
                "errors": self.error_counts.get(op_name, 0),
                "avg_duration": sum(self.timings.get(op_name, [0])) / len(self.timings.get(op_name, [1])) if self.timings.get(op_name) else 0,
                "min_duration": min(self.timings.get(op_name, [0])) if self.timings.get(op_name) else 0,
                "max_duration": max(self.timings.get(op_name, [0])) if self.timings.get(op_name) else 0,
            }
        
        return report

# Initialize global performance monitor
perf_monitor = PerformanceMonitor()
```

### 4. Environment Standardization

Create a `requirements.txt` file with explicit versions:

```
httpx==0.28.1
beautifulsoup4==4.13.4
surrealdb==0.3.0
python-dotenv==1.1.0
```

Add a `Dockerfile` for containerized execution:

```Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "crawl-to-markdown.py"]
```

## Long-Term Solutions (Next 2 Weeks)

### 1. SurrealDB Client Upgrade Strategy

#### Step 1: Abstract Database Operations

Create a new `database.py` file with a proper abstraction layer:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class DatabaseClient(ABC):
    """Abstract base class for database operations."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the database."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the database."""
        pass
    
    @abstractmethod
    async def insert_knowledge_item(self, item: Dict[str, Any]) -> Optional[str]:
        """Insert a knowledge item into the database."""
        pass
    
    @abstractmethod
    async def bulk_insert_knowledge_items(self, items: List[Dict[str, Any]]) -> int:
        """Insert multiple knowledge items in a single operation."""
        pass
    
    @abstractmethod
    async def count_knowledge_items(self) -> int:
        """Count knowledge items in the database."""
        pass

class SurrealDBClientV0(DatabaseClient):
    """SurrealDB client using v0.3.0 API."""
    
    def __init__(self, url, namespace, database, username, password):
        self.url = url
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.client = None
    
    async def connect(self) -> bool:
        """Connect to SurrealDB."""
        try:
            from surrealdb import Surreal
            self.client = Surreal(self.url)
            await self.client.connect()
            await self.client.signin({"user": self.username, "pass": self.password})
            await self.client.use(self.namespace, self.database)
            return True
        except Exception as e:
            logger.error(f"Error connecting to SurrealDB: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from SurrealDB."""
        if self.client:
            await self.client.close()
            self.client = None
    
    # Implement remaining methods using v0.3.0 API...

class SurrealDBClientV1(DatabaseClient):
    """SurrealDB client using v1.0.4 API."""
    
    # Implementation using new API...
```

#### Step 2: Feature Parity Test Suite

Create a comprehensive test suite to ensure both implementations produce identical results:

```python
import unittest
import asyncio

class DatabaseClientTests(unittest.TestCase):
    """Test suite for database client implementations."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_items = [
            {"title": "Test 1", "content": "Content 1"},
            {"title": "Test 2", "content": "Content 2"},
        ]
    
    async def _test_client(self, client: DatabaseClient):
        """Test a database client implementation."""
        # Connect
        connected = await client.connect()
        self.assertTrue(connected)
        
        # Count initial items
        initial_count = await client.count_knowledge_items()
        
        # Insert single item
        item_id = await client.insert_knowledge_item(self.test_items[0])
        self.assertIsNotNone(item_id)
        
        # Verify count increased
        new_count = await client.count_knowledge_items()
        self.assertEqual(new_count, initial_count + 1)
        
        # Bulk insert
        success_count = await client.bulk_insert_knowledge_items([self.test_items[1]])
        self.assertEqual(success_count, 1)
        
        # Verify count increased again
        final_count = await client.count_knowledge_items()
        self.assertEqual(final_count, initial_count + 2)
        
        # Disconnect
        await client.disconnect()
    
    def test_v0_client(self):
        """Test v0.3.0 client implementation."""
        client = SurrealDBClientV0(
            url="http://localhost:8000",
            namespace="ptolemies",
            database="knowledge",
            username="root",
            password="root"
        )
        asyncio.run(self._test_client(client))
    
    def test_v1_client(self):
        """Test v1.0.4 client implementation."""
        client = SurrealDBClientV1(
            url="http://localhost:8000",
            namespace="ptolemies",
            database="knowledge",
            username="root",
            password="root"
        )
        asyncio.run(self._test_client(client))
```

### 2. Production Monitoring & Observability

Create a comprehensive monitoring system with:

1. **Structured Logging**:
```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()
```

2. **Prometheus Metrics**:
```python
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
DB_OPERATIONS = Counter('db_operations_total', 'Total database operations', ['operation', 'status'])
DB_OPERATION_DURATION = Histogram('db_operation_duration_seconds', 'Duration of database operations', ['operation'])

# Start metrics server
start_http_server(8000)
```

3. **Health Check Endpoint**:
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class HealthStatus(BaseModel):
    status: str
    db_connected: bool
    crawled_urls: int
    stored_items: int

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    db_client = get_db_client()
    connected = await db_client.connect()
    
    if not connected:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    item_count = await db_client.count_knowledge_items()
    await db_client.disconnect()
    
    return {
        "status": "healthy",
        "db_connected": connected,
        "crawled_urls": get_crawler_stats()["urls_crawled"],
        "stored_items": item_count
    }
```

### 3. Comprehensive Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test database operations with real SurrealDB instance
3. **End-to-End Tests**: Test complete workflow from crawl to storage
4. **Performance Tests**: Verify system can handle the required load
5. **CI/CD Pipeline**: Automate testing and deployment

### 4. Documentation & Standards

1. **API Documentation**: Document all database operations and interfaces
2. **Architecture Diagram**: Create a visual representation of the system
3. **Runbook**: Create operational procedures for common tasks
4. **Code Style**: Enforce consistent code style and documentation

## Implementation Timeline

### Week 1: Immediate Fixes & Stabilization
- Day 1-2: Implement bulk insert and error recovery
- Day 3-4: Add performance monitoring and environment standardization
- Day 5: Run full crawler with 662 URLs and validate results

### Week 2: Technical Debt Reduction
- Day 1-3: Create database abstraction layer and SurrealDB client implementations
- Day 4-5: Implement comprehensive test suite and verify parity

### Week 3: Production Readiness
- Day 1-2: Implement monitoring and observability
- Day 3-4: Create documentation and operational procedures
- Day 5: Final review and deployment

## Metrics for Success

1. **Reliability**: >99% success rate for URL storage
2. **Performance**: Process 662 URLs in <5 minutes
3. **Code Quality**: >90% test coverage
4. **Documentation**: Complete API documentation and operational procedures

This plan addresses both the immediate needs for fixing the SurrealDB integration and the long-term requirements for building a robust, maintainable system that meets DevQ.ai standards.