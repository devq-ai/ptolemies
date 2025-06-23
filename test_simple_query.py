#!/usr/bin/env python3
"""
Simple test script to verify query processing pipeline works.
"""

import os
import sys
from pathlib import Path

# Set environment variable to disable logfire
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from query_processing_pipeline import (
        QueryProcessor,
        QueryPipelineConfig,
        QueryContext,
        QueryIntent,
        QueryComplexity
    )
    from hybrid_query_engine import QueryType
    
    def test_basic_query_processing():
        """Test basic query processing functionality."""
        print("Testing basic query processing...")
        
        # Create a simple config
        config = QueryPipelineConfig(
            enable_intent_detection=True,
            enable_entity_extraction=True,
            enable_query_expansion=False,  # Disable to avoid model dependencies
            enable_spell_correction=True
        )
        
        # Mock the embedding model initialization to avoid dependencies
        processor = QueryProcessor(config)
        processor.embedding_model = None  # Disable embedding model
        
        # Test normalization
        normalized = processor._normalize_query("  HELLO WORLD  ")
        assert normalized == "hello world", f"Expected 'hello world', got '{normalized}'"
        print("✓ Query normalization works")
        
        # Test spell correction
        corrected, was_corrected = processor._spell_correct("pyton programming")
        assert corrected == "python programming", f"Expected 'python programming', got '{corrected}'"
        assert was_corrected is True
        print("✓ Spell correction works")
        
        # Test intent detection
        intent, confidence = processor._detect_intent("explain how authentication works")
        assert intent in [QueryIntent.EXPLAIN, QueryIntent.SEARCH], f"Unexpected intent: {intent}"
        print(f"✓ Intent detection works: {intent} (confidence: {confidence})")
        
        # Test entity extraction
        entities = processor._extract_entities("How to use Python with FastAPI and Redis")
        entity_values = [e["value"] for e in entities]
        assert "python" in entity_values, f"Python not found in entities: {entity_values}"
        assert "fastapi" in entity_values, f"FastAPI not found in entities: {entity_values}"
        print(f"✓ Entity extraction works: {entity_values}")
        
        # Test keyword extraction
        keywords = processor._extract_keywords("How to implement authentication in FastAPI")
        assert "implement" in keywords, f"'implement' not found in keywords: {keywords}"
        assert "authentication" in keywords, f"'authentication' not found in keywords: {keywords}"
        print(f"✓ Keyword extraction works: {keywords}")
        
        # Test complexity assessment
        complexity = processor._assess_complexity(
            "how to use python",
            [{"type": "technology", "value": "python"}],
            []
        )
        assert complexity == QueryComplexity.SIMPLE, f"Expected SIMPLE, got {complexity}"
        print(f"✓ Complexity assessment works: {complexity}")
        
        # Test search strategy determination
        strategy = processor._determine_search_strategy(
            QueryIntent.EXPLAIN,
            QueryComplexity.SIMPLE,
            []
        )
        assert strategy == QueryType.CONCEPT_EXPANSION, f"Expected CONCEPT_EXPANSION, got {strategy}"
        print(f"✓ Search strategy determination works: {strategy}")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    if __name__ == "__main__":
        success = test_basic_query_processing()
        if success:
            print("✅ Query processing pipeline is working correctly!")
            sys.exit(0)
        else:
            print("❌ Some tests failed!")
            sys.exit(1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This might be due to missing dependencies or environment issues.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)