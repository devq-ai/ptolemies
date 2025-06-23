#!/usr/bin/env python3
"""
Generate TaskMaster AI task structure for Ptolemies project.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any

class PtolemiesTaskGenerator:
    def __init__(self):
        self.tasks = []
        self.task_map = {}
        self.start_date = datetime.now()
        
    def generate_task_id(self, phase: str, task_name: str) -> str:
        """Generate unique task ID."""
        return f"ptolemies-{phase}-{task_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"
    
    def add_task(self, 
                 phase: str,
                 name: str, 
                 description: str,
                 complexity: int,
                 duration_days: int,
                 dependencies: List[str] = None,
                 subtasks: List[Dict] = None) -> str:
        """Add a task to the structure."""
        task_id = self.generate_task_id(phase, name)
        
        task = {
            "id": task_id,
            "name": name,
            "description": description,
            "phase": phase,
            "complexity": complexity,
            "status": "pending",
            "priority": "high" if phase in ["phase1", "phase2"] else "medium",
            "duration_days": duration_days,
            "dependencies": dependencies or [],
            "subtasks": subtasks or [],
            "created_at": datetime.now().isoformat(),
            "estimated_start": self.start_date.isoformat(),
            "estimated_end": (self.start_date + timedelta(days=duration_days)).isoformat(),
            "tags": ["ptolemies", "knowledge-base", phase],
            "assigned_to": "devq-ai-team",
            "metrics": {
                "test_coverage_target": 90,
                "logfire_instrumentation": True,
                "documentation_required": True
            }
        }
        
        self.tasks.append(task)
        self.task_map[name] = task_id
        return task_id
    
    def generate_phase1_tasks(self):
        """Phase 1: Foundation (Week 1)"""
        phase = "phase1"
        
        # Main phase task
        phase1_id = self.add_task(
            phase=phase,
            name="Foundation Setup",
            description="Set up core infrastructure and verify all tools for Ptolemies project",
            complexity=5,
            duration_days=7,
            subtasks=[
                {
                    "name": "TaskMaster AI Integration",
                    "description": "Set up TaskMaster AI for project management",
                    "complexity": 3,
                    "estimated_hours": 4
                },
                {
                    "name": "MCP Tools Verification",
                    "description": "Verify accessibility of all required MCP tools",
                    "complexity": 2,
                    "estimated_hours": 3
                },
                {
                    "name": "Database Configuration",
                    "description": "Configure SurrealDB and Neo4j connections",
                    "complexity": 4,
                    "estimated_hours": 6
                },
                {
                    "name": "Base FastAPI Application",
                    "description": "Implement core FastAPI application structure with Logfire",
                    "complexity": 3,
                    "estimated_hours": 5
                },
                {
                    "name": "PyTest Framework",
                    "description": "Create comprehensive PyTest framework with 90% coverage target",
                    "complexity": 3,
                    "estimated_hours": 4
                }
            ]
        )
        
        return phase1_id
    
    def generate_phase2_tasks(self):
        """Phase 2: Neo4j MCP Development (Week 2)"""
        phase = "phase2"
        phase1_dep = self.task_map.get("Foundation Setup")
        
        phase2_id = self.add_task(
            phase=phase,
            name="Neo4j MCP Server Development",
            description="Build and deploy Neo4j MCP server for graph operations",
            complexity=7,
            duration_days=7,
            dependencies=[phase1_dep] if phase1_dep else [],
            subtasks=[
                {
                    "name": "Neo4j MCP Core Implementation",
                    "description": "Build Neo4j MCP server from existing code base",
                    "complexity": 5,
                    "estimated_hours": 8
                },
                {
                    "name": "Comprehensive Test Suite",
                    "description": "Implement full test coverage for Neo4j MCP",
                    "complexity": 4,
                    "estimated_hours": 6
                },
                {
                    "name": "Logfire Instrumentation",
                    "description": "Add complete Logfire monitoring to Neo4j MCP",
                    "complexity": 3,
                    "estimated_hours": 4
                },
                {
                    "name": "Ecosystem Integration",
                    "description": "Deploy and integrate with DevQ.AI ecosystem",
                    "complexity": 4,
                    "estimated_hours": 5
                },
                {
                    "name": "API Documentation",
                    "description": "Document all Neo4j MCP API specifications",
                    "complexity": 2,
                    "estimated_hours": 3
                }
            ]
        )
        
        return phase2_id
    
    def generate_phase3_tasks(self):
        """Phase 3: Crawling Infrastructure (Week 3-4)"""
        phase = "phase3"
        phase2_dep = self.task_map.get("Neo4j MCP Server Development")
        
        phase3_id = self.add_task(
            phase=phase,
            name="Crawling Infrastructure Implementation",
            description="Build comprehensive web crawling and content processing pipeline",
            complexity=8,
            duration_days=14,
            dependencies=[phase2_dep] if phase2_dep else [],
            subtasks=[
                {
                    "name": "Crawl4AI Integration",
                    "description": "Implement Crawl4AI engine with MCP server reference",
                    "complexity": 5,
                    "estimated_hours": 10
                },
                {
                    "name": "Content Processing Pipeline",
                    "description": "Build HTML to Markdown conversion with metadata extraction",
                    "complexity": 4,
                    "estimated_hours": 8
                },
                {
                    "name": "Quality Scoring System",
                    "description": "Create relevance scoring and duplicate detection",
                    "complexity": 5,
                    "estimated_hours": 8
                },
                {
                    "name": "Incremental Update Logic",
                    "description": "Develop smart incremental crawling with version tracking",
                    "complexity": 6,
                    "estimated_hours": 10
                },
                {
                    "name": "Initial Source Testing",
                    "description": "Test with Logfire, SurrealDB, and FastAPI documentation",
                    "complexity": 3,
                    "estimated_hours": 6
                }
            ]
        )
        
        return phase3_id
    
    def generate_phase4_tasks(self):
        """Phase 4: Storage & Retrieval (Week 5-6)"""
        phase = "phase4"
        phase3_dep = self.task_map.get("Crawling Infrastructure Implementation")
        
        phase4_id = self.add_task(
            phase=phase,
            name="Storage and Retrieval System",
            description="Implement dual-database storage with hybrid query capabilities",
            complexity=9,
            duration_days=14,
            dependencies=[phase3_dep] if phase3_dep else [],
            subtasks=[
                {
                    "name": "SurrealDB Vector Storage",
                    "description": "Implement vector storage with OpenAI embeddings",
                    "complexity": 6,
                    "estimated_hours": 12
                },
                {
                    "name": "Neo4j Graph Relationships",
                    "description": "Build document structure and concept relationships",
                    "complexity": 5,
                    "estimated_hours": 10
                },
                {
                    "name": "Hybrid Query Engine",
                    "description": "Create combined semantic + graph search capabilities",
                    "complexity": 7,
                    "estimated_hours": 14
                },
                {
                    "name": "Performance Optimization",
                    "description": "Optimize for sub-100ms query response times",
                    "complexity": 5,
                    "estimated_hours": 8
                },
                {
                    "name": "Redis Caching Layer",
                    "description": "Add Redis caching with Upstash integration",
                    "complexity": 4,
                    "estimated_hours": 6
                }
            ]
        )
        
        return phase4_id
    
    def generate_phase5_tasks(self):
        """Phase 5: MCP Service Creation (Week 7)"""
        phase = "phase5"
        phase4_dep = self.task_map.get("Storage and Retrieval System")
        
        phase5_id = self.add_task(
            phase=phase,
            name="Ptolemies MCP Service",
            description="Create comprehensive MCP service for knowledge base access",
            complexity=7,
            duration_days=7,
            dependencies=[phase4_dep] if phase4_dep else [],
            subtasks=[
                {
                    "name": "MCP Interface Design",
                    "description": "Design Ptolemies MCP interface and protocols",
                    "complexity": 4,
                    "estimated_hours": 6
                },
                {
                    "name": "Core MCP Handlers",
                    "description": "Implement search, retrieve, and graph query handlers",
                    "complexity": 5,
                    "estimated_hours": 10
                },
                {
                    "name": "Authentication & Rate Limiting",
                    "description": "Add API key auth and per-client throttling",
                    "complexity": 4,
                    "estimated_hours": 6
                },
                {
                    "name": "MCP Documentation",
                    "description": "Create comprehensive MCP usage documentation",
                    "complexity": 3,
                    "estimated_hours": 5
                },
                {
                    "name": "Ecosystem Integration Testing",
                    "description": "Test integration with all DevQ.AI agents",
                    "complexity": 4,
                    "estimated_hours": 8
                }
            ]
        )
        
        return phase5_id
    
    def generate_phase6_tasks(self):
        """Phase 6: Visualization & Analytics (Week 8)"""
        phase = "phase6"
        phase5_dep = self.task_map.get("Ptolemies MCP Service")
        
        phase6_id = self.add_task(
            phase=phase,
            name="Visualization and Analytics Platform",
            description="Build comprehensive dashboards and monitoring infrastructure",
            complexity=6,
            duration_days=7,
            dependencies=[phase5_dep] if phase5_dep else [],
            subtasks=[
                {
                    "name": "SurrealDB Dashboards",
                    "description": "Build vector search and RAG performance dashboards",
                    "complexity": 4,
                    "estimated_hours": 8
                },
                {
                    "name": "Neo4j Visualizations",
                    "description": "Create interactive graph visualizations with D3.js",
                    "complexity": 5,
                    "estimated_hours": 10
                },
                {
                    "name": "Real-time Metrics",
                    "description": "Implement live metrics tracking with Logfire",
                    "complexity": 4,
                    "estimated_hours": 6
                },
                {
                    "name": "Export Capabilities",
                    "description": "Add data export in multiple formats",
                    "complexity": 3,
                    "estimated_hours": 4
                },
                {
                    "name": "Monitoring Deployment",
                    "description": "Deploy full monitoring infrastructure",
                    "complexity": 3,
                    "estimated_hours": 5
                }
            ]
        )
        
        return phase6_id
    
    def generate_dependency_graph(self) -> Dict[str, Any]:
        """Generate visual dependency graph structure."""
        nodes = []
        edges = []
        
        for task in self.tasks:
            nodes.append({
                "id": task["id"],
                "label": task["name"],
                "phase": task["phase"],
                "complexity": task["complexity"],
                "status": task["status"]
            })
            
            for dep in task["dependencies"]:
                edges.append({
                    "from": dep,
                    "to": task["id"],
                    "type": "depends_on"
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "layout": "hierarchical",
            "direction": "LR"
        }
    
    def generate_taskmaster_structure(self) -> Dict[str, Any]:
        """Generate complete TaskMaster AI compatible structure."""
        # Generate all phase tasks
        self.generate_phase1_tasks()
        self.generate_phase2_tasks()
        self.generate_phase3_tasks()
        self.generate_phase4_tasks()
        self.generate_phase5_tasks()
        self.generate_phase6_tasks()
        
        # Calculate totals
        total_complexity = sum(task["complexity"] for task in self.tasks)
        total_subtasks = sum(len(task["subtasks"]) for task in self.tasks)
        total_duration = sum(task["duration_days"] for task in self.tasks) // len(self.tasks)  # Parallel phases
        
        return {
            "project": {
                "name": "Ptolemies Knowledge Base System",
                "description": "Centralized knowledge base for DevQ.AI ecosystem with RAG and graph capabilities",
                "organization": "DevQ.AI",
                "created_at": datetime.now().isoformat(),
                "total_phases": 6,
                "total_tasks": len(self.tasks),
                "total_subtasks": total_subtasks,
                "total_complexity": total_complexity,
                "estimated_duration_weeks": 8,
                "technologies": [
                    "FastAPI", "SurrealDB", "Neo4j", "Crawl4AI", 
                    "PyTest", "Logfire", "Redis", "OpenAI"
                ]
            },
            "phases": {
                "phase1": {
                    "name": "Foundation",
                    "week": 1,
                    "focus": "Infrastructure setup and tool verification"
                },
                "phase2": {
                    "name": "Neo4j MCP Development",
                    "week": 2,
                    "focus": "Graph database MCP server creation"
                },
                "phase3": {
                    "name": "Crawling Infrastructure",
                    "week": "3-4",
                    "focus": "Web crawling and content processing"
                },
                "phase4": {
                    "name": "Storage & Retrieval",
                    "week": "5-6",
                    "focus": "Dual-database storage with hybrid queries"
                },
                "phase5": {
                    "name": "MCP Service Creation",
                    "week": 7,
                    "focus": "Ptolemies MCP server for ecosystem access"
                },
                "phase6": {
                    "name": "Visualization & Analytics",
                    "week": 8,
                    "focus": "Dashboards and monitoring infrastructure"
                }
            },
            "tasks": self.tasks,
            "dependency_graph": self.generate_dependency_graph(),
            "metrics": {
                "total_estimated_hours": sum(
                    sum(st["estimated_hours"] for st in task["subtasks"]) 
                    for task in self.tasks
                ),
                "average_complexity": total_complexity / len(self.tasks),
                "critical_path_weeks": 8,
                "documentation_sources": 18,
                "target_pages": 5000,
                "test_coverage_target": 90
            }
        }

def main():
    """Generate and save TaskMaster AI task structure."""
    generator = PtolemiesTaskGenerator()
    task_structure = generator.generate_taskmaster_structure()
    
    # Save main task structure
    output_path = "/Users/dionedge/devqai/ptolemies/.taskmaster/ptolemies_tasks.json"
    with open(output_path, 'w') as f:
        json.dump(task_structure, f, indent=2)
    
    print(f"✅ Generated TaskMaster AI task structure: {output_path}")
    print(f"📊 Total Tasks: {len(task_structure['tasks'])}")
    print(f"🔧 Total Subtasks: {task_structure['metrics']['total_estimated_hours']} hours")
    print(f"📈 Average Complexity: {task_structure['metrics']['average_complexity']:.1f}")
    
    # Generate summary report
    summary_path = "/Users/dionedge/devqai/ptolemies/.taskmaster/task_summary.md"
    with open(summary_path, 'w') as f:
        f.write("# Ptolemies Project - TaskMaster AI Task Summary\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Project Overview\n")
        f.write(f"- **Total Phases**: 6\n")
        f.write(f"- **Total Tasks**: {len(task_structure['tasks'])}\n")
        f.write(f"- **Total Estimated Hours**: {task_structure['metrics']['total_estimated_hours']}\n")
        f.write(f"- **Duration**: 8 weeks\n\n")
        
        f.write("## Phase Breakdown\n\n")
        for phase_key, phase_info in task_structure['phases'].items():
            phase_tasks = [t for t in task_structure['tasks'] if t['phase'] == phase_key]
            if phase_tasks:
                task = phase_tasks[0]
                f.write(f"### {phase_info['name']} (Week {phase_info['week']})\n")
                f.write(f"**Focus**: {phase_info['focus']}\n")
                f.write(f"**Complexity**: {task['complexity']}/10\n")
                f.write(f"**Subtasks**:\n")
                for subtask in task['subtasks']:
                    f.write(f"- {subtask['name']} ({subtask['estimated_hours']}h)\n")
                f.write("\n")
    
    print(f"📄 Generated task summary: {summary_path}")

if __name__ == "__main__":
    main()