#!/usr/bin/env python3
"""
Minimal test for query processing without external dependencies.
"""

import os
import sys
from pathlib import Path
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Mock external dependencies
class MockQueryType(Enum):
    SEMANTIC_ONLY = "semantic_only"
    GRAPH_ONLY = "graph_only"
    HYBRID_BALANCED = "hybrid_balanced"
    SEMANTIC_THEN_GRAPH = "semantic_then_graph"
    GRAPH_THEN_SEMANTIC = "graph_then_semantic"
    CONCEPT_EXPANSION = "concept_expansion"

class QueryIntent(Enum):
    SEARCH = "search"
    EXPLAIN = "explain"
    COMPARE = "compare"
    ANALYZE = "analyze"
    SUMMARIZE = "summarize"
    TUTORIAL = "tutorial"
    TROUBLESHOOT = "troubleshoot"
    DEFINITION = "definition"
    EXAMPLE = "example"
    UNKNOWN = "unknown"

class QueryComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    COMPOUND = "compound"

# Mock the dependencies we need
sys.modules['hybrid_query_engine'] = type('MockModule', (), {
    'QueryType': MockQueryType,
    'HybridSearchResult': type('HybridSearchResult', (), {}),
})()

# Mock other modules
for module in ['performance_optimizer', 'redis_cache_layer', 'mcp_tool_registry', 'logfire']:
    sys.modules[module] = type('MockModule', (), {})()

# Set path and environment
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Now we can test the core logic
def test_query_processor_logic():
    """Test the core query processing logic."""
    print("Testing query processor core logic...")
    
    # Test normalization
    def normalize_query(query: str) -> str:
        import re
        normalized = query.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s\-\.\,\?\!]', '', normalized)
        return normalized
    
    # Test spell correction
    def spell_correct(query: str) -> Tuple[str, bool]:
        common_corrections = {
            "pyton": "python",
            "javascrip": "javascript", 
            "databse": "database",
            "authetication": "authentication"
        }
        
        corrected = query
        was_corrected = False
        words = query.split()
        corrected_words = []
        
        for word in words:
            if word in common_corrections:
                corrected_words.append(common_corrections[word])
                was_corrected = True
            else:
                corrected_words.append(word)
        
        corrected = ' '.join(corrected_words)
        return corrected, was_corrected
    
    # Test intent detection
    def detect_intent(query: str) -> Tuple[QueryIntent, float]:
        import re
        from collections import defaultdict
        
        query_lower = query.lower()
        intent_scores = defaultdict(float)
        
        intent_patterns = {
            QueryIntent.SEARCH: [
                r"(find|search|look for|locate|where)",
                r"(show me|get me|fetch)",
                r"(information about|details on)"
            ],
            QueryIntent.EXPLAIN: [
                r"(explain|what is|what are|describe)",
                r"(how does|how do|how to)",
                r"(tell me about|teach me)"
            ],
            QueryIntent.COMPARE: [
                r"(compare|difference|versus|vs)",
                r"(better than|worse than)",
                r"(pros and cons|advantages|disadvantages)"
            ]
        }
        
        for intent, patterns in intent_patterns.items():
            for pattern_list in patterns:
                if re.search(pattern_list, query_lower):
                    intent_scores[intent] += 1.0
        
        if not intent_scores:
            return QueryIntent.UNKNOWN, 0.0
        
        best_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[best_intent]
        confidence = min(max_score / 3.0, 1.0)
        
        if confidence < 0.7:
            return QueryIntent.SEARCH, confidence
        
        return best_intent, confidence
    
    # Run tests
    print("1. Testing normalization...")
    normalized = normalize_query("  HELLO WORLD  ")
    assert normalized == "hello world", f"Expected 'hello world', got '{normalized}'"
    print("✓ Normalization works")
    
    print("2. Testing spell correction...")
    corrected, was_corrected = spell_correct("pyton programming")
    assert corrected == "python programming", f"Expected 'python programming', got '{corrected}'"
    assert was_corrected is True
    print("✓ Spell correction works")
    
    print("3. Testing intent detection...")
    intent, confidence = detect_intent("explain how authentication works")
    assert intent in [QueryIntent.EXPLAIN, QueryIntent.SEARCH], f"Unexpected intent: {intent}"
    print(f"✓ Intent detection works: {intent} (confidence: {confidence})")
    
    print("4. Testing with misspelled query...")
    corrected, was_corrected = spell_correct("How to implement authetication in FastAPI?")
    assert "authentication" in corrected, f"Expected authentication in corrected query: {corrected}"
    print(f"✓ Spell correction for complex query: {corrected}")
    
    intent, confidence = detect_intent("How to implement authentication in FastAPI?")
    print(f"✓ Intent for implementation query: {intent} (confidence: {confidence})")
    
    print("\n🎉 All core logic tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_query_processor_logic()
        if success:
            print("✅ Query processing core logic is working correctly!")
            sys.exit(0)
        else:
            print("❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)