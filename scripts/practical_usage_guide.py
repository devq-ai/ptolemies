#!/usr/bin/env python3
"""
Ptolemies Practical Usage Guide
Real-world examples showing how to integrate with the 784-page knowledge base
in production applications and development workflows.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Import Ptolemies components
from src.hybrid_query_engine import (
    HybridQueryEngine, HybridQueryConfig, QueryType, create_hybrid_engine
)
from src.redis_cache_layer import RedisCacheLayer, create_redis_cache_layer

class UsagePattern(Enum):
    """Common usage patterns for the knowledge base."""
    DOCUMENTATION_SEARCH = "documentation_search"
    CODE_EXAMPLE_FINDER = "code_example_finder"
    CONCEPT_EXPLORER = "concept_explorer"
    TROUBLESHOOTING_ASSISTANT = "troubleshooting_assistant"
    LEARNING_PATH_GENERATOR = "learning_path_generator"

@dataclass
class SearchContext:
    """Context for search operations."""
    user_id: str
    session_id: str
    application: str
    search_history: List[str]
    preferences: Dict[str, Any]

class PtolemiesKnowledgeAPI:
    """High-level API for accessing Ptolemies knowledge base."""
    
    def __init__(self):
        self.hybrid_engine: Optional[HybridQueryEngine] = None
        self.cache_layer: Optional[RedisCacheLayer] = None
        self.initialized = False
    
    async def initialize(self, enable_cache: bool = True) -> bool:
        """Initialize the knowledge API."""
        try:
            print("🚀 Initializing Ptolemies Knowledge API...")
            
            # Initialize hybrid engine
            self.hybrid_engine = await create_hybrid_engine()
            print("   ✅ Hybrid query engine initialized")
            
            # Initialize cache layer if enabled
            if enable_cache:
                self.cache_layer = await create_redis_cache_layer()
                print("   ✅ Cache layer initialized")
            
            self.initialized = True
            print("🎉 Ptolemies Knowledge API ready!")
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    async def search_documentation(
        self, 
        query: str, 
        context: SearchContext = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Search documentation with intelligent ranking."""
        if not self.initialized:
            raise RuntimeError("API not initialized")
        
        # Check cache first
        cache_key = f"doc_search_{query.replace(' ', '_')}"
        if self.cache_layer:
            cached_result, found = await self.cache_layer.get(
                cache_key, "documentation"
            )
            if found:
                cached_result['from_cache'] = True
                return cached_result
        
        # Perform hybrid search
        results, metrics = await self.hybrid_engine.search(
            query=query,
            query_type=QueryType.HYBRID_BALANCED,
            limit=max_results
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'title': result.title,
                'content': result.content,
                'source': result.source_name,
                'url': result.source_url,
                'relevance_score': result.combined_score,
                'topics': result.topics,
                'chunk_info': {
                    'index': result.chunk_index,
                    'total': result.total_chunks
                } if result.chunk_index is not None else None
            })
        
        response = {
            'query': query,
            'results': formatted_results,
            'total_found': len(results),
            'search_time_ms': metrics.total_time_ms,
            'search_strategy': 'hybrid_balanced',
            'from_cache': False,
            'metadata': {
                'semantic_time_ms': metrics.semantic_time_ms,
                'graph_time_ms': metrics.graph_time_ms,
                'fusion_time_ms': metrics.fusion_time_ms,
                'overlap_count': metrics.overlap_count,
                'query_analysis': asdict(metrics.query_analysis)
            }
        }
        
        # Cache the result
        if self.cache_layer:
            await self.cache_layer.set(
                cache_key, response, "documentation", ttl_seconds=1800
            )
        
        return response
    
    async def find_code_examples(
        self, 
        technology: str, 
        use_case: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Find code examples for specific technologies and use cases."""
        query = f"{technology} {use_case} {language} code example implementation"
        
        # Use semantic search with high similarity threshold
        results, metrics = await self.hybrid_engine.search(
            query=query,
            query_type=QueryType.SEMANTIC_THEN_GRAPH,
            limit=15
        )
        
        # Filter for code-heavy content
        code_results = []
        for result in results:
            # Simple heuristic for code content
            code_indicators = ['def ', 'class ', 'import ', 'from ', '```', 'async def']
            code_score = sum(1 for indicator in code_indicators if indicator in result.content)
            
            if code_score > 0 or 'example' in result.title.lower():
                code_results.append({
                    'title': result.title,
                    'content': result.content,
                    'source': result.source_name,
                    'url': result.source_url,
                    'relevance_score': result.combined_score,
                    'code_indicators': code_score,
                    'topics': result.topics
                })
        
        return {
            'technology': technology,
            'use_case': use_case,
            'language': language,
            'examples': code_results[:10],
            'total_found': len(code_results),
            'search_time_ms': metrics.total_time_ms
        }
    
    async def explore_concepts(
        self, 
        starting_concept: str, 
        depth: int = 2
    ) -> Dict[str, Any]:
        """Explore related concepts and build a knowledge map."""
        # Use concept expansion strategy
        results, metrics = await self.hybrid_engine.search(
            query=starting_concept,
            query_type=QueryType.CONCEPT_EXPANSION,
            limit=20
        )
        
        # Build concept map
        concept_map = {
            'central_concept': starting_concept,
            'related_concepts': [],
            'connections': [],
            'depth': depth
        }
        
        # Extract related concepts from results
        all_topics = set()
        for result in results:
            all_topics.update(result.topics)
            if result.related_concepts:
                all_topics.update(result.related_concepts)
        
        # Remove the starting concept and limit to most relevant
        related_topics = list(all_topics - {starting_concept})[:15]
        
        concept_map['related_concepts'] = [
            {
                'name': topic,
                'relevance': 1.0 - (i * 0.05),  # Decreasing relevance
                'sources': [r.source_name for r in results if topic in r.topics][:3]
            }
            for i, topic in enumerate(related_topics)
        ]
        
        # Find connections between concepts
        for i, concept1 in enumerate(related_topics[:5]):
            for concept2 in related_topics[i+1:8]:
                # Check if concepts appear together in results
                shared_results = [
                    r for r in results 
                    if concept1 in r.topics and concept2 in r.topics
                ]
                if shared_results:
                    concept_map['connections'].append({
                        'from': concept1,
                        'to': concept2,
                        'strength': len(shared_results) / len(results),
                        'evidence': len(shared_results)
                    })
        
        return {
            'concept_map': concept_map,
            'supporting_documents': [
                {
                    'title': r.title,
                    'source': r.source_name,
                    'relevance_score': r.combined_score
                }
                for r in results[:10]
            ],
            'search_metadata': {
                'total_time_ms': metrics.total_time_ms,
                'concept_expansions': metrics.concept_expansions
            }
        }
    
    async def troubleshoot_issue(
        self, 
        error_message: str, 
        technology_stack: List[str],
        context_info: str = ""
    ) -> Dict[str, Any]:
        """Help troubleshoot technical issues using the knowledge base."""
        # Build comprehensive query
        tech_stack_str = " ".join(technology_stack)
        full_query = f"{error_message} {tech_stack_str} {context_info} troubleshooting solution fix"
        
        # Use graph-then-semantic for troubleshooting
        results, metrics = await self.hybrid_engine.search(
            query=full_query,
            query_type=QueryType.GRAPH_THEN_SEMANTIC,
            limit=20
        )
        
        # Categorize results
        solutions = []
        explanations = []
        related_issues = []
        
        for result in results:
            content_lower = result.content.lower()
            title_lower = result.title.lower()
            
            # Categorize based on content
            if any(word in content_lower for word in ['solution', 'fix', 'resolve', 'solve']):
                solutions.append(result)
            elif any(word in content_lower for word in ['error', 'exception', 'problem', 'issue']):
                if any(word in content_lower for word in ['explain', 'cause', 'reason', 'why']):
                    explanations.append(result)
                else:
                    related_issues.append(result)
            else:
                explanations.append(result)  # Default to explanations
        
        return {
            'error_message': error_message,
            'technology_stack': technology_stack,
            'troubleshooting_results': {
                'solutions': [
                    {
                        'title': r.title,
                        'content': r.content[:300] + "..." if len(r.content) > 300 else r.content,
                        'source': r.source_name,
                        'url': r.source_url,
                        'confidence': r.combined_score
                    }
                    for r in solutions[:5]
                ],
                'explanations': [
                    {
                        'title': r.title,
                        'content': r.content[:200] + "..." if len(r.content) > 200 else r.content,
                        'source': r.source_name,
                        'confidence': r.combined_score
                    }
                    for r in explanations[:3]
                ],
                'related_issues': [
                    {
                        'title': r.title,
                        'source': r.source_name,
                        'similarity': r.combined_score
                    }
                    for r in related_issues[:5]
                ]
            },
            'search_metadata': {
                'total_results': len(results),
                'search_time_ms': metrics.total_time_ms,
                'query_complexity': metrics.query_analysis.complexity_score
            }
        }
    
    async def generate_learning_path(
        self, 
        target_skill: str, 
        current_level: str = "beginner",
        time_constraint: str = "flexible"
    ) -> Dict[str, Any]:
        """Generate a learning path for acquiring new skills."""
        # Search for educational content
        learning_query = f"{target_skill} tutorial guide learning {current_level}"
        
        results, metrics = await self.hybrid_engine.search(
            query=learning_query,
            query_type=QueryType.CONCEPT_EXPANSION,
            limit=25
        )
        
        # Organize into learning path
        learning_path = {
            'target_skill': target_skill,
            'current_level': current_level,
            'estimated_time': time_constraint,
            'modules': []
        }
        
        # Group content by topics and difficulty
        topic_groups = {}
        for result in results:
            for topic in result.topics:
                if topic not in topic_groups:
                    topic_groups[topic] = []
                topic_groups[topic].append(result)
        
        # Create learning modules
        priority_topics = [
            'basics', 'fundamentals', 'introduction', 'getting started',
            'intermediate', 'advanced', 'best practices', 'examples'
        ]
        
        module_index = 1
        for priority in priority_topics:
            matching_topics = [t for t in topic_groups.keys() if priority in t.lower()]
            
            for topic in matching_topics:
                if len(learning_path['modules']) >= 8:  # Limit modules
                    break
                
                module_results = topic_groups[topic][:3]  # Top 3 per module
                
                learning_path['modules'].append({
                    'module': module_index,
                    'topic': topic,
                    'difficulty': self._estimate_difficulty(topic, current_level),
                    'resources': [
                        {
                            'title': r.title,
                            'source': r.source_name,
                            'url': r.source_url,
                            'type': self._classify_content_type(r.title, r.content),
                            'estimated_time': self._estimate_reading_time(r.content)
                        }
                        for r in module_results
                    ]
                })
                module_index += 1
        
        return {
            'learning_path': learning_path,
            'total_modules': len(learning_path['modules']),
            'total_resources': sum(len(m['resources']) for m in learning_path['modules']),
            'search_metadata': {
                'search_time_ms': metrics.total_time_ms,
                'sources_consulted': len(set(r.source_name for r in results))
            }
        }
    
    def _estimate_difficulty(self, topic: str, current_level: str) -> str:
        """Estimate difficulty level for a topic."""
        beginner_indicators = ['intro', 'basic', 'getting started', 'fundamentals']
        advanced_indicators = ['advanced', 'expert', 'optimization', 'internals']
        
        topic_lower = topic.lower()
        
        if any(indicator in topic_lower for indicator in beginner_indicators):
            return 'beginner'
        elif any(indicator in topic_lower for indicator in advanced_indicators):
            return 'advanced'
        else:
            return 'intermediate'
    
    def _classify_content_type(self, title: str, content: str) -> str:
        """Classify the type of content."""
        title_lower = title.lower()
        content_lower = content.lower()
        
        if 'tutorial' in title_lower or 'guide' in title_lower:
            return 'tutorial'
        elif 'example' in title_lower or 'def ' in content_lower:
            return 'code_example'
        elif 'api' in title_lower or 'reference' in title_lower:
            return 'reference'
        elif '```' in content or 'import ' in content:
            return 'code_snippet'
        else:
            return 'documentation'
    
    def _estimate_reading_time(self, content: str) -> str:
        """Estimate reading time for content."""
        word_count = len(content.split())
        minutes = max(1, word_count // 200)  # ~200 words per minute
        
        if minutes <= 2:
            return "2-3 minutes"
        elif minutes <= 5:
            return "5-7 minutes"
        elif minutes <= 10:
            return "10-15 minutes"
        else:
            return "15+ minutes"
    
    async def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get intelligent query suggestions."""
        if not self.initialized or not self.hybrid_engine:
            return []
        
        return await self.hybrid_engine.get_query_suggestions(partial_query)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status and performance metrics."""
        status = {
            'initialized': self.initialized,
            'components': {
                'hybrid_engine': self.hybrid_engine is not None,
                'cache_layer': self.cache_layer is not None
            },
            'performance': {}
        }
        
        if self.cache_layer:
            cache_stats = await self.cache_layer.get_cache_stats()
            status['performance']['cache'] = cache_stats.get('cache_metrics', {})
        
        return status
    
    async def close(self):
        """Clean up resources."""
        if self.hybrid_engine:
            await self.hybrid_engine.vector_store.close()
            await self.hybrid_engine.graph_store.close()
        
        if self.cache_layer:
            await self.cache_layer.close()
        
        self.initialized = False

# Usage Examples and Practical Implementations

class DeveloperAssistant:
    """Example implementation: Developer coding assistant."""
    
    def __init__(self):
        self.knowledge_api = PtolemiesKnowledgeAPI()
    
    async def initialize(self):
        await self.knowledge_api.initialize()
    
    async def help_with_implementation(self, task_description: str) -> str:
        """Help developer implement a specific task."""
        # Search for relevant code examples and documentation
        result = await self.knowledge_api.find_code_examples(
            technology="FastAPI",
            use_case=task_description,
            language="python"
        )
        
        if result['examples']:
            best_example = result['examples'][0]
            return f"""
💡 Found implementation guidance for: {task_description}

📖 Best Example: {best_example['title']}
🔗 Source: {best_example['source']}
⭐ Relevance: {best_example['relevance_score']:.2f}

📝 Code snippet:
{best_example['content'][:500]}...

🔍 Related topics: {', '.join(best_example['topics'])}
"""
        else:
            return f"❌ No specific examples found for: {task_description}"

class DocumentationBot:
    """Example implementation: Documentation search bot."""
    
    def __init__(self):
        self.knowledge_api = PtolemiesKnowledgeAPI()
    
    async def initialize(self):
        await self.knowledge_api.initialize()
    
    async def answer_question(self, question: str, user_context: Dict[str, Any] = None) -> str:
        """Answer user questions based on documentation."""
        context = SearchContext(
            user_id=user_context.get('user_id', 'anonymous'),
            session_id=user_context.get('session_id', 'default'),
            application='documentation_bot',
            search_history=[],
            preferences={}
        )
        
        result = await self.knowledge_api.search_documentation(
            query=question,
            context=context,
            max_results=5
        )
        
        if result['results']:
            top_result = result['results'][0]
            response = f"""
🤖 Based on the documentation ({result['search_time_ms']:.1f}ms search):

📖 **{top_result['title']}**
📚 Source: {top_result['source']}
⭐ Relevance: {top_result['relevance_score']:.2f}

{top_result['content'][:400]}...

🔗 More info: {top_result['url']}
"""
            
            if result['from_cache']:
                response += "\n⚡ (Retrieved from cache)"
            
            return response
        else:
            return "❌ I couldn't find relevant documentation for your question."

async def demonstrate_practical_usage():
    """Demonstrate practical usage patterns."""
    print("🏛️ Ptolemies Practical Usage Demonstration")
    print("=" * 60)
    
    # Example 1: Developer Assistant
    print("\n1️⃣ Developer Assistant Example:")
    assistant = DeveloperAssistant()
    await assistant.initialize()
    
    help_result = await assistant.help_with_implementation(
        "authentication middleware with JWT tokens"
    )
    print(help_result)
    
    # Example 2: Documentation Bot
    print("\n2️⃣ Documentation Bot Example:")
    doc_bot = DocumentationBot()
    await doc_bot.initialize()
    
    answer = await doc_bot.answer_question(
        "How do I implement FastAPI middleware for authentication?",
        {"user_id": "dev123", "session_id": "session456"}
    )
    print(answer)
    
    # Example 3: Direct API Usage
    print("\n3️⃣ Direct Knowledge API Usage:")
    knowledge_api = PtolemiesKnowledgeAPI()
    await knowledge_api.initialize()
    
    # Concept exploration
    concept_map = await knowledge_api.explore_concepts("authentication", depth=2)
    print(f"🗺️ Concept exploration for 'authentication':")
    print(f"   Related concepts: {len(concept_map['concept_map']['related_concepts'])}")
    print(f"   Connections found: {len(concept_map['concept_map']['connections'])}")
    
    # Troubleshooting example
    troubleshooting = await knowledge_api.troubleshoot_issue(
        error_message="ImportError: No module named 'fastapi'",
        technology_stack=["Python", "FastAPI", "pip"],
        context_info="development environment setup"
    )
    print(f"\n🔧 Troubleshooting results:")
    print(f"   Solutions found: {len(troubleshooting['troubleshooting_results']['solutions'])}")
    print(f"   Explanations: {len(troubleshooting['troubleshooting_results']['explanations'])}")
    
    # Learning path generation
    learning_path = await knowledge_api.generate_learning_path(
        target_skill="FastAPI development",
        current_level="beginner"
    )
    print(f"\n📚 Learning path generated:")
    print(f"   Modules: {learning_path['total_modules']}")
    print(f"   Resources: {learning_path['total_resources']}")
    
    # System status
    status = await knowledge_api.get_system_status()
    print(f"\n📊 System Status:")
    print(f"   Initialized: {status['initialized']}")
    print(f"   Components: {status['components']}")
    
    # Cleanup
    await assistant.knowledge_api.close()
    await doc_bot.knowledge_api.close()
    await knowledge_api.close()
    
    print("\n✅ Practical usage demonstration completed!")

if __name__ == "__main__":
    asyncio.run(demonstrate_practical_usage())