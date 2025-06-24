#!/usr/bin/env python3
"""
AI Hallucination Detector for Ptolemies
=======================================

Main orchestrator for detecting AI hallucinations in Python code
using AST analysis and Neo4j knowledge graph validation.

Adapted from: https://github.com/coleam00/mcp-crawl4ai-rag/tree/main/knowledge_graphs
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional
import logfire

from ai_script_analyzer import AIScriptAnalyzer, ScriptAnalysis
from knowledge_graph_validator import KnowledgeGraphValidator, ValidationResult
from hallucination_reporter import HallucinationReporter

# Configure Logfire
try:
    logfire.configure()
except:
    print("⚠️  Logfire not configured, continuing without logging")

class AIHallucinationDetector:
    """Main detector class that orchestrates the hallucination detection process."""
    
    def __init__(self):
        self.analyzer = AIScriptAnalyzer()
        self.validator = KnowledgeGraphValidator()
        self.reporter = HallucinationReporter()
    
    @logfire.instrument("detect_hallucinations")
    def detect_hallucinations(self, script_path: str, 
                            save_json: bool = True, 
                            save_markdown: bool = True,
                            verbose: bool = False) -> ValidationResult:
        """Detect hallucinations in a Python script."""
        
        script_path_obj = Path(script_path)
        
        if not script_path_obj.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Step 1: Analyze the script
        print(f"🔍 Analyzing script: {script_path}")
        
        try:
            with open(script_path_obj, 'r', encoding='utf-8') as f:
                script_content = f.read()
        except Exception as e:
            raise Exception(f"Failed to read script: {e}")
        
        analysis = self.analyzer.analyze_script(script_content)
        
        if verbose:
            print(f"📊 Analysis results:")
            print(f"  - Imports: {len(analysis.imports)}")
            print(f"  - Class instantiations: {len(analysis.class_instantiations)}")
            print(f"  - Method calls: {len(analysis.method_calls)}")
            print(f"  - Function calls: {len(analysis.function_calls)}")
            print(f"  - Attribute accesses: {len(analysis.attribute_accesses)}")
        
        # Step 2: Validate against knowledge graph
        print(f"🧠 Validating against knowledge graph...")
        
        validation_result = self.validator.validate_script_analysis(script_path, analysis)
        
        if verbose:
            print(f"✅ Validation results:")
            print(f"  - Valid items: {len(validation_result.valid_items)}")
            print(f"  - Invalid items: {len(validation_result.invalid_items)}")
            print(f"  - Uncertain items: {len(validation_result.uncertain_items)}")
            print(f"  - Overall confidence: {validation_result.overall_confidence:.2f}")
        
        # Step 3: Generate reports
        print(f"📝 Generating reports...")
        
        if save_json:
            json_path = self.reporter.save_json_report(validation_result)
            print(f"📄 JSON report saved: {json_path}")
        
        if save_markdown:
            md_path = self.reporter.save_markdown_report(validation_result)
            print(f"📄 Markdown report saved: {md_path}")
        
        # Step 4: Print summary
        self.reporter.print_summary(validation_result)
        
        return validation_result
    
    def detect_batch(self, script_paths: List[str], 
                    save_reports: bool = True, 
                    verbose: bool = False) -> List[ValidationResult]:
        """Detect hallucinations in multiple scripts."""
        results = []
        
        print(f"🚀 Starting batch hallucination detection for {len(script_paths)} scripts")
        
        for i, script_path in enumerate(script_paths, 1):
            print(f"\n📍 Processing {i}/{len(script_paths)}: {script_path}")
            
            try:
                result = self.detect_hallucinations(
                    script_path, 
                    save_json=save_reports, 
                    save_markdown=save_reports,
                    verbose=verbose
                )
                results.append(result)
                
            except Exception as e:
                print(f"❌ Error processing {script_path}: {e}")
        
        # Generate batch summary
        self._print_batch_summary(results)
        
        return results
    
    def _print_batch_summary(self, results: List[ValidationResult]):
        """Print summary of batch processing results."""
        if not results:
            return
        
        total_items = sum(r.total_items for r in results)
        total_valid = sum(len(r.valid_items) for r in results)
        total_invalid = sum(len(r.invalid_items) for r in results)
        total_uncertain = sum(len(r.uncertain_items) for r in results)
        avg_confidence = sum(r.overall_confidence for r in results) / len(results)
        
        print(f"\n📈 Batch Summary:")
        print(f"📄 Scripts processed: {len(results)}")
        print(f"🔍 Total items analyzed: {total_items}")
        print(f"✅ Valid items: {total_valid} ({total_valid/max(total_items,1)*100:.1f}%)")
        print(f"❌ Invalid items: {total_invalid} ({total_invalid/max(total_items,1)*100:.1f}%)")
        print(f"⚠️  Uncertain items: {total_uncertain} ({total_uncertain/max(total_items,1)*100:.1f}%)")
        print(f"🎯 Average confidence: {avg_confidence:.2f}")
        
        # Identify most problematic scripts
        problematic = sorted(results, key=lambda r: len(r.invalid_items) + len(r.uncertain_items), reverse=True)
        if problematic:
            print(f"\n🚨 Most problematic scripts:")
            for i, result in enumerate(problematic[:3], 1):
                issues = len(result.invalid_items) + len(result.uncertain_items)
                print(f"{i}. {result.script_path}: {issues} potential issues")

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="AI Hallucination Detector for Python Scripts")
    parser.add_argument("script_path", nargs="+", help="Path(s) to Python script(s) to analyze")
    parser.add_argument("--no-json", action="store_true", help="Don't save JSON report")
    parser.add_argument("--no-markdown", action="store_true", help="Don't save Markdown report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test-knowledge-graph", action="store_true", help="Test knowledge graph connection")
    
    args = parser.parse_args()
    
    detector = AIHallucinationDetector()
    
    # Test knowledge graph connection if requested
    if args.test_knowledge_graph:
        print("🧪 Testing knowledge graph connection...")
        frameworks = detector.validator.run_neo4j_query("MATCH (f:Framework) RETURN f.name LIMIT 5")
        classes = detector.validator.run_neo4j_query("MATCH (c:Class) RETURN c.name LIMIT 5")
        
        print(f"✅ Found {len(frameworks)} frameworks in knowledge base")
        print(f"✅ Found {len(classes)} classes in knowledge base")
        
        if frameworks or classes:
            print("🎉 Knowledge graph connection successful!")
        else:
            print("⚠️  Knowledge graph appears empty - populate it first")
        return
    
    try:
        if len(args.script_path) == 1:
            # Single script
            detector.detect_hallucinations(
                args.script_path[0],
                save_json=not args.no_json,
                save_markdown=not args.no_markdown,
                verbose=args.verbose
            )
        else:
            # Batch processing
            detector.detect_batch(
                args.script_path,
                save_reports=not (args.no_json and args.no_markdown),
                verbose=args.verbose
            )
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    print(f"\n🎉 Hallucination detection complete!")

if __name__ == "__main__":
    main()