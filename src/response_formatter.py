#!/usr/bin/env python3
"""
Response Formatter for Ptolemies
Sophisticated response formatting system that handles different output formats,
applies intent-specific formatting, and provides rich, structured responses.
"""

import json
import time
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timezone

# Optional import for logfire  
try:
    import logfire
    HAS_LOGFIRE = True
except ImportError:
    # Mock logfire for environments where it's not available
    class MockLogfire:
        def configure(self, **kwargs): pass
        def instrument(self, name): 
            def decorator(func): return func
            return decorator
        def span(self, name, **kwargs): 
            class MockSpan:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return MockSpan()
        def info(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def warning(self, *args, **kwargs): pass
    
    logfire = MockLogfire()
    HAS_LOGFIRE = False

from query_processing_pipeline import QueryIntent, ProcessedQuery
from hybrid_query_engine import HybridSearchResult

# Configure Logfire
logfire.configure(send_to_logfire=False)

class OutputFormat(Enum):
    """Supported output formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"
    STRUCTURED = "structured"
    COMPACT = "compact"
    DETAILED = "detailed"

class ResponseStyle(Enum):
    """Response presentation styles."""
    CONCISE = "concise"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    TUTORIAL = "tutorial"
    COMPARISON = "comparison"
    TROUBLESHOOTING = "troubleshooting"
    SUMMARY = "summary"

@dataclass
class FormattingConfig:
    """Configuration for response formatting."""
    # Output preferences
    default_format: OutputFormat = OutputFormat.STRUCTURED
    max_results_per_section: int = 5
    include_metadata: bool = True
    include_sources: bool = True
    include_snippets: bool = True
    snippet_length: int = 200
    
    # Content formatting
    enable_syntax_highlighting: bool = True
    include_confidence_scores: bool = True
    show_search_strategy: bool = True
    include_related_concepts: bool = True
    
    # Layout preferences
    enable_grouping: bool = True
    group_by_source: bool = False
    group_by_topic: bool = True
    sort_by_relevance: bool = True
    
    # Intent-specific settings
    tutorial_include_steps: bool = True
    comparison_show_tables: bool = True
    troubleshooting_prioritize_solutions: bool = True
    
    # Language and localization
    language: str = "en"
    timezone: str = "UTC"
    date_format: str = "%Y-%m-%d %H:%M:%S"

@dataclass
class FormattedResponse:
    """Represents a formatted response."""
    # Core content
    formatted_content: str
    format_type: OutputFormat
    style: ResponseStyle
    
    # Metadata
    query: str
    intent: str
    results_count: int
    processing_time_ms: float
    timestamp: str
    
    # Sections and structure
    sections: List[Dict[str, Any]] = None
    summary: Optional[str] = None
    key_insights: List[str] = None
    related_queries: List[str] = None
    
    # Technical details
    search_strategy: Optional[str] = None
    confidence_score: Optional[float] = None
    sources: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.sections is None:
            self.sections = []
        if self.key_insights is None:
            self.key_insights = []
        if self.related_queries is None:
            self.related_queries = []
        if self.sources is None:
            self.sources = []

class ResponseFormatter:
    """Advanced response formatter with multiple output formats and styles."""
    
    def __init__(self, config: FormattingConfig = None):
        self.config = config or FormattingConfig()
        
        # Intent-specific formatting strategies
        self.intent_formatters = {
            QueryIntent.SEARCH: self._format_search_response,
            QueryIntent.EXPLAIN: self._format_explanation_response,
            QueryIntent.COMPARE: self._format_comparison_response,
            QueryIntent.ANALYZE: self._format_analysis_response,
            QueryIntent.SUMMARIZE: self._format_summary_response,
            QueryIntent.TUTORIAL: self._format_tutorial_response,
            QueryIntent.TROUBLESHOOT: self._format_troubleshooting_response,
            QueryIntent.DEFINITION: self._format_definition_response,
            QueryIntent.EXAMPLE: self._format_example_response
        }
        
        # Common code patterns for syntax highlighting
        self.code_patterns = {
            'python': r'```python\n(.*?)\n```',
            'javascript': r'```javascript\n(.*?)\n```',
            'json': r'```json\n(.*?)\n```',
            'yaml': r'```yaml\n(.*?)\n```',
            'sql': r'```sql\n(.*?)\n```'
        }
    
    @logfire.instrument("format_response")
    async def format_response(
        self,
        query: str,
        processed_query: ProcessedQuery,
        search_results: List[HybridSearchResult],
        format_type: OutputFormat = None,
        custom_style: ResponseStyle = None,
        processing_time_ms: float = 0
    ) -> FormattedResponse:
        """Format a complete response based on query intent and results."""
        
        with logfire.span("Response formatting", query=query[:100]):
            try:
                start_time = time.time()
                
                # Determine format and style
                format_type = format_type or self.config.default_format
                style = custom_style or self._determine_response_style(processed_query.intent)
                
                # Get intent-specific formatter
                formatter = self.intent_formatters.get(
                    processed_query.intent, 
                    self._format_search_response
                )
                
                # Apply intent-specific formatting
                sections = await formatter(
                    query, processed_query, search_results
                )
                
                # Generate summary and insights
                summary = self._generate_summary(processed_query, search_results)
                key_insights = self._extract_key_insights(search_results, processed_query.intent)
                related_queries = self._generate_related_queries(processed_query)
                
                # Format based on output type
                formatted_content = await self._apply_output_format(
                    sections, format_type, style
                )
                
                # Extract source information
                sources = self._extract_source_info(search_results)
                
                # Create formatted response
                response = FormattedResponse(
                    formatted_content=formatted_content,
                    format_type=format_type,
                    style=style,
                    query=query,
                    intent=processed_query.intent.value,
                    results_count=len(search_results),
                    processing_time_ms=processing_time_ms,
                    timestamp=datetime.now(timezone.utc).strftime(self.config.date_format),
                    sections=sections,
                    summary=summary,
                    key_insights=key_insights,
                    related_queries=related_queries,
                    search_strategy=processed_query.search_strategy.value if processed_query.search_strategy else None,
                    confidence_score=processed_query.confidence_score,
                    sources=sources
                )
                
                formatting_time = (time.time() - start_time) * 1000
                
                logfire.info("Response formatted successfully",
                           format_type=format_type.value,
                           style=style.value,
                           sections_count=len(sections),
                           formatting_time_ms=formatting_time)
                
                return response
                
            except Exception as e:
                logfire.error("Response formatting failed", error=str(e))
                # Return a basic fallback response
                return self._create_fallback_response(query, search_results, format_type or OutputFormat.TEXT)
    
    def _determine_response_style(self, intent: QueryIntent) -> ResponseStyle:
        """Determine appropriate response style based on intent."""
        style_mapping = {
            QueryIntent.SEARCH: ResponseStyle.CONCISE,
            QueryIntent.EXPLAIN: ResponseStyle.DETAILED,
            QueryIntent.COMPARE: ResponseStyle.COMPARISON,
            QueryIntent.ANALYZE: ResponseStyle.TECHNICAL,
            QueryIntent.SUMMARIZE: ResponseStyle.SUMMARY,
            QueryIntent.TUTORIAL: ResponseStyle.TUTORIAL,
            QueryIntent.TROUBLESHOOT: ResponseStyle.TROUBLESHOOTING,
            QueryIntent.DEFINITION: ResponseStyle.CONCISE,
            QueryIntent.EXAMPLE: ResponseStyle.TECHNICAL
        }
        return style_mapping.get(intent, ResponseStyle.DETAILED)
    
    async def _format_search_response(
        self, 
        query: str, 
        processed_query: ProcessedQuery, 
        results: List[HybridSearchResult]
    ) -> List[Dict[str, Any]]:
        """Format search response with grouped results."""
        
        sections = []
        
        if not results:
            sections.append({
                "title": "No Results Found",
                "content": f"No results found for '{query}'. Try rephrasing your query or using different keywords.",
                "type": "message"
            })
            return sections
        
        # Group results if enabled
        if self.config.enable_grouping:
            if self.config.group_by_topic:
                grouped_results = self._group_by_topic(results)
            elif self.config.group_by_source:
                grouped_results = self._group_by_source(results)
            else:
                grouped_results = {"Search Results": results}
        else:
            grouped_results = {"Search Results": results}
        
        # Create sections for each group
        for group_name, group_results in grouped_results.items():
            section = {
                "title": group_name,
                "type": "results",
                "results": []
            }
            
            for result in group_results[:self.config.max_results_per_section]:
                formatted_result = {
                    "title": result.title,
                    "snippet": self._create_snippet(result.content),
                    "source": result.source_name,
                    "url": result.source_url,
                    "score": result.combined_score
                }
                
                if self.config.include_confidence_scores:
                    formatted_result["confidence"] = result.combined_score
                
                if result.topics and self.config.include_related_concepts:
                    formatted_result["topics"] = result.topics
                
                section["results"].append(formatted_result)
            
            sections.append(section)
        
        return sections
    
    async def _format_explanation_response(
        self, 
        query: str, 
        processed_query: ProcessedQuery, 
        results: List[HybridSearchResult]
    ) -> List[Dict[str, Any]]:
        """Format explanation response with structured content."""
        
        sections = []
        
        if not results:
            return [{"title": "No Information Found", "content": "Unable to find explanatory content for this query.", "type": "message"}]
        
        # Overview section
        overview_content = self._create_overview(results[:3])
        sections.append({
            "title": "Overview",
            "content": overview_content,
            "type": "explanation"
        })
        
        # Key concepts section
        key_concepts = self._extract_key_concepts(results)
        if key_concepts:
            sections.append({
                "title": "Key Concepts",
                "content": key_concepts,
                "type": "concepts",
                "items": [concept for concept in key_concepts if concept]
            })
        
        # Detailed explanation
        detailed_content = self._create_detailed_explanation(results[:5])
        sections.append({
            "title": "Detailed Explanation",
            "content": detailed_content,
            "type": "detailed"
        })
        
        # Examples section
        examples = self._extract_examples(results)
        if examples:
            sections.append({
                "title": "Examples",
                "content": examples,
                "type": "examples"
            })
        
        return sections
    
    async def _format_comparison_response(
        self, 
        query: str, 
        processed_query: ProcessedQuery, 
        results: List[HybridSearchResult]
    ) -> List[Dict[str, Any]]:
        """Format comparison response with side-by-side analysis."""
        
        sections = []
        
        # Extract entities being compared
        entities = [entity["value"] for entity in processed_query.entities if entity["type"] == "technology"]
        
        if len(entities) < 2:
            # Try to extract from query text
            entities = self._extract_comparison_entities(query)
        
        if len(entities) >= 2:
            # Create comparison table
            comparison_data = self._create_comparison_table(entities, results)
            sections.append({
                "title": f"Comparison: {' vs '.join(entities[:2])}",
                "content": comparison_data,
                "type": "comparison",
                "entities": entities
            })
            
            # Pros and cons section
            pros_cons = self._extract_pros_cons(entities, results)
            if pros_cons:
                sections.append({
                    "title": "Pros and Cons",
                    "content": pros_cons,
                    "type": "pros_cons"
                })
        else:
            # Fallback to general comparison
            sections.append({
                "title": "Comparison Analysis",
                "content": self._create_general_comparison(results),
                "type": "general_comparison"
            })
        
        return sections
    
    async def _format_tutorial_response(
        self, 
        query: str, 
        processed_query: ProcessedQuery, 
        results: List[HybridSearchResult]
    ) -> List[Dict[str, Any]]:
        """Format tutorial response with step-by-step instructions."""
        
        sections = []
        
        if not results:
            return [{"title": "No Tutorial Found", "content": "Unable to find tutorial content for this topic.", "type": "message"}]
        
        # Introduction
        intro = self._create_tutorial_intro(query, results[:2])
        sections.append({
            "title": "Introduction",
            "content": intro,
            "type": "intro"
        })
        
        # Prerequisites
        prerequisites = self._extract_prerequisites(results)
        if prerequisites:
            sections.append({
                "title": "Prerequisites",
                "content": prerequisites,
                "type": "prerequisites",
                "items": prerequisites if isinstance(prerequisites, list) else [prerequisites]
            })
        
        # Step-by-step instructions
        if self.config.tutorial_include_steps:
            steps = self._extract_tutorial_steps(results)
            if steps:
                sections.append({
                    "title": "Step-by-Step Instructions",
                    "content": steps,
                    "type": "steps",
                    "steps": steps if isinstance(steps, list) else [steps]
                })
        
        # Code examples
        code_examples = self._extract_code_examples(results)
        if code_examples:
            sections.append({
                "title": "Code Examples",
                "content": code_examples,
                "type": "code_examples"
            })
        
        # Additional resources
        resources = self._extract_additional_resources(results)
        if resources:
            sections.append({
                "title": "Additional Resources",
                "content": resources,
                "type": "resources"
            })
        
        return sections
    
    async def _format_troubleshooting_response(
        self, 
        query: str, 
        processed_query: ProcessedQuery, 
        results: List[HybridSearchResult]
    ) -> List[Dict[str, Any]]:
        """Format troubleshooting response with solutions and diagnostics."""
        
        sections = []
        
        if not results:
            return [{"title": "No Solutions Found", "content": "Unable to find troubleshooting information for this issue.", "type": "message"}]
        
        # Problem identification
        problem_analysis = self._analyze_problem(query, results[:3])
        sections.append({
            "title": "Problem Analysis",
            "content": problem_analysis,
            "type": "analysis"
        })
        
        # Quick fixes
        quick_fixes = self._extract_quick_fixes(results)
        if quick_fixes:
            sections.append({
                "title": "Quick Fixes",
                "content": quick_fixes,
                "type": "quick_fixes",
                "solutions": quick_fixes if isinstance(quick_fixes, list) else [quick_fixes]
            })
        
        # Detailed solutions
        if self.config.troubleshooting_prioritize_solutions:
            solutions = self._extract_detailed_solutions(results)
            sections.append({
                "title": "Detailed Solutions",
                "content": solutions,
                "type": "solutions"
            })
        
        # Common causes
        common_causes = self._extract_common_causes(results)
        if common_causes:
            sections.append({
                "title": "Common Causes",
                "content": common_causes,
                "type": "causes"
            })
        
        # Prevention tips
        prevention = self._extract_prevention_tips(results)
        if prevention:
            sections.append({
                "title": "Prevention Tips",
                "content": prevention,
                "type": "prevention"
            })
        
        return sections
    
    async def _format_summary_response(
        self, 
        query: str, 
        processed_query: ProcessedQuery, 
        results: List[HybridSearchResult]
    ) -> List[Dict[str, Any]]:
        """Format summary response with condensed information."""
        
        sections = []
        
        if not results:
            return [{"title": "No Content to Summarize", "content": "Unable to find content to summarize for this topic.", "type": "message"}]
        
        # Executive summary
        exec_summary = self._create_executive_summary(results[:5])
        sections.append({
            "title": "Executive Summary",
            "content": exec_summary,
            "type": "executive_summary"
        })
        
        # Key points
        key_points = self._extract_key_points(results)
        sections.append({
            "title": "Key Points",
            "content": key_points,
            "type": "key_points",
            "points": key_points if isinstance(key_points, list) else [key_points]
        })
        
        # Statistics and facts
        stats = self._extract_statistics(results)
        if stats:
            sections.append({
                "title": "Key Statistics",
                "content": stats,
                "type": "statistics"
            })
        
        return sections
    
    async def _format_definition_response(
        self, 
        query: str, 
        processed_query: ProcessedQuery, 
        results: List[HybridSearchResult]
    ) -> List[Dict[str, Any]]:
        """Format definition response with clear explanations."""
        
        sections = []
        
        if not results:
            return [{"title": "Definition Not Found", "content": "Unable to find a definition for this term.", "type": "message"}]
        
        # Main definition
        definition = self._extract_definition(results[:3])
        sections.append({
            "title": "Definition",
            "content": definition,
            "type": "definition"
        })
        
        # Context and usage
        context = self._extract_context(results)
        if context:
            sections.append({
                "title": "Context and Usage",
                "content": context,
                "type": "context"
            })
        
        # Related terms
        related_terms = self._extract_related_terms(results)
        if related_terms:
            sections.append({
                "title": "Related Terms",
                "content": related_terms,
                "type": "related_terms"
            })
        
        return sections
    
    async def _format_example_response(
        self, 
        query: str, 
        processed_query: ProcessedQuery, 
        results: List[HybridSearchResult]
    ) -> List[Dict[str, Any]]:
        """Format example response with practical demonstrations."""
        
        sections = []
        
        if not results:
            return [{"title": "No Examples Found", "content": "Unable to find examples for this topic.", "type": "message"}]
        
        # Code examples
        code_examples = self._extract_code_examples(results)
        if code_examples:
            sections.append({
                "title": "Code Examples",
                "content": code_examples,
                "type": "code_examples"
            })
        
        # Practical examples
        practical_examples = self._extract_practical_examples(results)
        sections.append({
            "title": "Practical Examples",
            "content": practical_examples,
            "type": "practical_examples"
        })
        
        # Use cases
        use_cases = self._extract_use_cases(results)
        if use_cases:
            sections.append({
                "title": "Common Use Cases",
                "content": use_cases,
                "type": "use_cases"
            })
        
        return sections
    
    async def _apply_output_format(
        self, 
        sections: List[Dict[str, Any]], 
        format_type: OutputFormat, 
        style: ResponseStyle
    ) -> str:
        """Apply the specified output format to the sections."""
        
        if format_type == OutputFormat.JSON:
            return json.dumps(sections, indent=2, ensure_ascii=False)
        
        elif format_type == OutputFormat.MARKDOWN:
            return self._format_as_markdown(sections, style)
        
        elif format_type == OutputFormat.HTML:
            return self._format_as_html(sections, style)
        
        elif format_type == OutputFormat.TEXT:
            return self._format_as_text(sections, style)
        
        elif format_type == OutputFormat.STRUCTURED:
            return self._format_as_structured(sections, style)
        
        elif format_type == OutputFormat.COMPACT:
            return self._format_as_compact(sections, style)
        
        elif format_type == OutputFormat.DETAILED:
            return self._format_as_detailed(sections, style)
        
        else:
            # Default to structured format
            return self._format_as_structured(sections, style)
    
    def _format_as_markdown(self, sections: List[Dict[str, Any]], style: ResponseStyle) -> str:
        """Format sections as Markdown."""
        markdown_parts = []
        
        for section in sections:
            title = section.get("title", "Section")
            content = section.get("content", "")
            section_type = section.get("type", "")
            
            # Add section header
            markdown_parts.append(f"## {title}\n")
            
            if section_type == "results":
                # Format results list
                results = section.get("results", [])
                for result in results:
                    markdown_parts.append(f"### {result.get('title', 'Untitled')}")
                    markdown_parts.append(f"{result.get('snippet', '')}")
                    markdown_parts.append(f"**Source:** {result.get('source', 'Unknown')}")
                    if result.get('url'):
                        markdown_parts.append(f"**URL:** {result['url']}")
                    markdown_parts.append("")
            
            elif section_type == "steps":
                # Format step-by-step instructions
                steps = section.get("steps", [])
                for i, step in enumerate(steps, 1):
                    markdown_parts.append(f"{i}. {step}")
                markdown_parts.append("")
            
            elif section_type == "code_examples":
                # Format code with syntax highlighting
                if isinstance(content, list):
                    for example in content:
                        markdown_parts.append(f"```python\n{example}\n```")
                else:
                    markdown_parts.append(f"```\n{content}\n```")
                markdown_parts.append("")
            
            else:
                # Regular content
                markdown_parts.append(f"{content}\n")
        
        return "\n".join(markdown_parts)
    
    def _format_as_text(self, sections: List[Dict[str, Any]], style: ResponseStyle) -> str:
        """Format sections as plain text."""
        text_parts = []
        
        for section in sections:
            title = section.get("title", "Section")
            content = section.get("content", "")
            
            text_parts.append(f"{title.upper()}")
            text_parts.append("=" * len(title))
            text_parts.append(f"{content}")
            text_parts.append("")
        
        return "\n".join(text_parts)
    
    def _format_as_structured(self, sections: List[Dict[str, Any]], style: ResponseStyle) -> str:
        """Format sections as structured text with clear hierarchy."""
        structured_parts = []
        
        for i, section in enumerate(sections, 1):
            title = section.get("title", "Section")
            content = section.get("content", "")
            section_type = section.get("type", "")
            
            structured_parts.append(f"{i}. {title}")
            structured_parts.append("-" * (len(title) + 4))
            
            if section_type == "results":
                results = section.get("results", [])
                for j, result in enumerate(results, 1):
                    structured_parts.append(f"  {j}. {result.get('title', 'Untitled')}")
                    structured_parts.append(f"     {result.get('snippet', '')}")
                    structured_parts.append(f"     Source: {result.get('source', 'Unknown')}")
                    structured_parts.append("")
            else:
                structured_parts.append(f"{content}")
                structured_parts.append("")
        
        return "\n".join(structured_parts)
    
    # Helper methods for content extraction and processing
    def _create_snippet(self, content: str) -> str:
        """Create a snippet from content."""
        if len(content) <= self.config.snippet_length:
            return content
        
        # Try to break at sentence boundary
        snippet = content[:self.config.snippet_length]
        last_period = snippet.rfind('.')
        last_space = snippet.rfind(' ')
        
        if last_period > self.config.snippet_length * 0.7:
            return snippet[:last_period + 1]
        elif last_space > self.config.snippet_length * 0.8:
            return snippet[:last_space] + "..."
        else:
            return snippet + "..."
    
    def _group_by_topic(self, results: List[HybridSearchResult]) -> Dict[str, List[HybridSearchResult]]:
        """Group results by topic."""
        grouped = {}
        
        for result in results:
            topics = result.topics if result.topics else ["General"]
            primary_topic = topics[0] if topics else "General"
            
            if primary_topic not in grouped:
                grouped[primary_topic] = []
            grouped[primary_topic].append(result)
        
        return grouped
    
    def _group_by_source(self, results: List[HybridSearchResult]) -> Dict[str, List[HybridSearchResult]]:
        """Group results by source."""
        grouped = {}
        
        for result in results:
            source = result.source_name or "Unknown Source"
            if source not in grouped:
                grouped[source] = []
            grouped[source].append(result)
        
        return grouped
    
    def _generate_summary(self, processed_query: ProcessedQuery, results: List[HybridSearchResult]) -> str:
        """Generate a summary of the search results."""
        if not results:
            return "No relevant information found for this query."
        
        total_results = len(results)
        avg_score = sum(r.combined_score for r in results) / total_results
        
        summary_parts = [
            f"Found {total_results} relevant results with an average relevance score of {avg_score:.2f}."
        ]
        
        # Add intent-specific summary
        if processed_query.intent == QueryIntent.SEARCH:
            summary_parts.append("The results provide comprehensive information on the requested topic.")
        elif processed_query.intent == QueryIntent.EXPLAIN:
            summary_parts.append("The results offer detailed explanations and background information.")
        elif processed_query.intent == QueryIntent.COMPARE:
            summary_parts.append("The results enable comparison between different options or approaches.")
        
        return " ".join(summary_parts)
    
    def _extract_key_insights(self, results: List[HybridSearchResult], intent: QueryIntent) -> List[str]:
        """Extract key insights from results."""
        insights = []
        
        if not results:
            return insights
        
        # Find most relevant result
        top_result = max(results, key=lambda r: r.combined_score)
        insights.append(f"Most relevant information found in: {top_result.source_name}")
        
        # Count sources
        unique_sources = len(set(r.source_name for r in results))
        insights.append(f"Information gathered from {unique_sources} different sources")
        
        # Topic coverage
        all_topics = set()
        for result in results:
            if result.topics:
                all_topics.update(result.topics)
        
        if all_topics:
            insights.append(f"Covers topics: {', '.join(list(all_topics)[:3])}")
        
        return insights[:5]  # Limit to top 5 insights
    
    def _generate_related_queries(self, processed_query: ProcessedQuery) -> List[str]:
        """Generate related query suggestions."""
        related = []
        
        entities = [e["value"] for e in processed_query.entities]
        concepts = processed_query.concepts
        
        # Generate intent-based suggestions
        if processed_query.intent == QueryIntent.EXPLAIN:
            for entity in entities[:2]:
                related.append(f"How to use {entity}")
                related.append(f"{entity} best practices")
        
        elif processed_query.intent == QueryIntent.COMPARE:
            if len(entities) >= 2:
                related.append(f"{entities[0]} advantages over {entities[1]}")
                related.append(f"When to choose {entities[0]} vs {entities[1]}")
        
        elif processed_query.intent == QueryIntent.TUTORIAL:
            for entity in entities[:2]:
                related.append(f"{entity} getting started guide")
                related.append(f"Advanced {entity} techniques")
        
        # Add concept-based suggestions
        for concept in concepts[:2]:
            related.append(f"{concept} examples")
            related.append(f"{concept} troubleshooting")
        
        return related[:5]  # Limit to 5 suggestions
    
    def _extract_source_info(self, results: List[HybridSearchResult]) -> List[Dict[str, Any]]:
        """Extract source information from results."""
        sources = []
        seen_sources = set()
        
        for result in results:
            source_key = result.source_name
            if source_key not in seen_sources:
                sources.append({
                    "name": result.source_name,
                    "url": result.source_url,
                    "relevance": result.combined_score
                })
                seen_sources.add(source_key)
        
        return sources[:10]  # Limit to top 10 sources
    
    def _create_fallback_response(
        self, 
        query: str, 
        results: List[HybridSearchResult], 
        format_type: OutputFormat
    ) -> FormattedResponse:
        """Create a fallback response when formatting fails."""
        
        fallback_content = f"Results for query: {query}\n\n"
        
        if results:
            fallback_content += f"Found {len(results)} results:\n"
            for i, result in enumerate(results[:5], 1):
                fallback_content += f"{i}. {result.title}\n"
                fallback_content += f"   Source: {result.source_name}\n"
                fallback_content += f"   Score: {result.combined_score:.2f}\n\n"
        else:
            fallback_content += "No results found.\n"
        
        return FormattedResponse(
            formatted_content=fallback_content,
            format_type=format_type,
            style=ResponseStyle.CONCISE,
            query=query,
            intent="unknown",
            results_count=len(results),
            processing_time_ms=0,
            timestamp=datetime.now(timezone.utc).strftime(self.config.date_format)
        )
    
    # Additional helper methods for specific content extraction
    def _create_overview(self, results: List[HybridSearchResult]) -> str:
        """Create an overview from top results."""
        if not results:
            return "No overview available."
        
        # Combine content from top results
        overview_parts = []
        for result in results:
            snippet = self._create_snippet(result.content)
            overview_parts.append(snippet)
        
        return " ".join(overview_parts)
    
    def _extract_key_concepts(self, results: List[HybridSearchResult]) -> List[str]:
        """Extract key concepts from results."""
        concepts = set()
        
        for result in results:
            if result.topics:
                concepts.update(result.topics)
            if result.related_concepts:
                concepts.update(result.related_concepts)
        
        return list(concepts)[:10]  # Limit to 10 concepts
    
    def _create_detailed_explanation(self, results: List[HybridSearchResult]) -> str:
        """Create detailed explanation from results."""
        explanation_parts = []
        
        for result in results:
            if len(result.content) > 100:  # Only use substantial content
                explanation_parts.append(result.content[:300] + "...")
        
        return "\n\n".join(explanation_parts)
    
    def _extract_examples(self, results: List[HybridSearchResult]) -> str:
        """Extract examples from results."""
        examples = []
        
        for result in results:
            content = result.content.lower()
            if any(keyword in content for keyword in ['example', 'for instance', 'such as', '```']):
                examples.append(self._create_snippet(result.content))
        
        return "\n\n".join(examples) if examples else "No specific examples found."

# Additional formatting methods would continue here...
# This represents the core structure and key functionality of the response formatter.

if __name__ == "__main__":
    # Example usage
    async def main():
        formatter = ResponseFormatter()
        
        # Mock data for testing
        from dataclasses import dataclass
        
        @dataclass
        class MockProcessedQuery:
            intent: QueryIntent = QueryIntent.EXPLAIN
            entities: List[Dict] = None
            concepts: List[str] = None
            confidence_score: float = 0.85
            search_strategy = None
            
            def __post_init__(self):
                if self.entities is None:
                    self.entities = [{"type": "technology", "value": "fastapi"}]
                if self.concepts is None:
                    self.concepts = ["api", "web development"]
        
        @dataclass
        class MockSearchResult:
            title: str = "FastAPI Documentation"
            content: str = "FastAPI is a modern web framework for building APIs with Python."
            source_name: str = "FastAPI Docs"
            source_url: str = "https://fastapi.tiangolo.com"
            combined_score: float = 0.9
            topics: List[str] = None
            related_concepts: List[str] = None
            
            def __post_init__(self):
                if self.topics is None:
                    self.topics = ["web development", "python"]
                if self.related_concepts is None:
                    self.related_concepts = ["async", "performance"]
        
        # Test formatting
        query = "Explain how FastAPI works"
        processed_query = MockProcessedQuery()
        results = [MockSearchResult()]
        
        response = await formatter.format_response(
            query, processed_query, results, OutputFormat.MARKDOWN
        )
        
        print("Formatted Response:")
        print("=" * 50)
        print(response.formatted_content)
        print("\nMetadata:")
        print(f"Intent: {response.intent}")
        print(f"Results: {response.results_count}")
        print(f"Style: {response.style}")
    
    import asyncio
    asyncio.run(main())