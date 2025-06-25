#!/usr/bin/env python3
"""
Hallucination Reporter for Ptolemies Detection System
===================================================

Generates comprehensive reports about AI coding assistant hallucinations
detected through knowledge graph validation.

Adapted from: https://github.com/coleam00/mcp-crawl4ai-rag/tree/main/knowledge_graphs
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from knowledge_graph_validator import ValidationResult, ValidationItem, ValidationStatus

class HallucinationReporter:
    """Generates detailed reports about detected hallucinations."""
    
    def __init__(self):
        self.reports_dir = Path("hallucination_reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate_comprehensive_report(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """Generate a comprehensive report from validation results."""
        report = {
            "metadata": {
                "script_path": validation_result.script_path,
                "analysis_timestamp": datetime.now().isoformat(),
                "total_items_analyzed": validation_result.total_items,
                "overall_confidence": validation_result.overall_confidence,
                "summary": validation_result.summary
            },
            "statistics": {
                "valid_items": len(validation_result.valid_items),
                "invalid_items": len(validation_result.invalid_items),
                "uncertain_items": len(validation_result.uncertain_items),
                "not_found_items": len(validation_result.not_found_items)
            },
            "categorized_results": {
                "valid": self._categorize_items(validation_result.valid_items),
                "invalid": self._categorize_items(validation_result.invalid_items),
                "uncertain": self._categorize_items(validation_result.uncertain_items),
                "not_found": self._categorize_items(validation_result.not_found_items)
            },
            "hallucination_analysis": self._analyze_hallucinations(validation_result),
            "recommendations": self._generate_recommendations(validation_result),
            "library_usage_summary": self._generate_library_summary(validation_result)
        }
        
        return report
    
    def _categorize_items(self, items: List[ValidationItem]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize validation items by type."""
        categorized = {
            "imports": [],
            "classes": [],
            "methods": [],
            "functions": [],
            "attributes": []
        }
        
        for item in items:
            item_data = {
                "name": item.name,
                "confidence": item.confidence,
                "details": item.details,
                "suggestions": item.suggestions,
                "line_number": item.line_number
            }
            
            if item.type == "import":
                categorized["imports"].append(item_data)
            elif item.type == "class":
                categorized["classes"].append(item_data)
            elif item.type == "method":
                categorized["methods"].append(item_data)
            elif item.type == "function":
                categorized["functions"].append(item_data)
            elif item.type == "attribute":
                categorized["attributes"].append(item_data)
        
        return categorized
    
    def _analyze_hallucinations(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """Analyze patterns in detected hallucinations."""
        analysis = {
            "potential_hallucinations": len(validation_result.invalid_items) + len(validation_result.uncertain_items),
            "confidence_distribution": self._calculate_confidence_distribution(validation_result),
            "common_issues": self._identify_common_issues(validation_result),
            "risk_assessment": self._assess_risk(validation_result)
        }
        
        return analysis
    
    def _calculate_confidence_distribution(self, validation_result: ValidationResult) -> Dict[str, int]:
        """Calculate distribution of confidence scores."""
        all_items = (validation_result.valid_items + validation_result.invalid_items + 
                    validation_result.uncertain_items + validation_result.not_found_items)
        
        distribution = {
            "high_confidence": 0,  # 0.8+
            "medium_confidence": 0,  # 0.5-0.8
            "low_confidence": 0  # <0.5
        }
        
        for item in all_items:
            if item.confidence >= 0.8:
                distribution["high_confidence"] += 1
            elif item.confidence >= 0.5:
                distribution["medium_confidence"] += 1
            else:
                distribution["low_confidence"] += 1
        
        return distribution
    
    def _identify_common_issues(self, validation_result: ValidationResult) -> List[str]:
        """Identify common patterns in validation issues."""
        issues = []
        
        # Check for unknown imports
        unknown_imports = [item for item in validation_result.uncertain_items if item.type == "import"]
        if unknown_imports:
            issues.append(f"Found {len(unknown_imports)} unknown imports that may be hallucinated")
        
        # Check for invalid classes
        invalid_classes = [item for item in validation_result.invalid_items if item.type == "class"]
        if invalid_classes:
            issues.append(f"Found {len(invalid_classes)} invalid class instantiations")
        
        # Check for uncertain methods
        uncertain_methods = [item for item in validation_result.uncertain_items if item.type == "method"]
        if uncertain_methods:
            issues.append(f"Found {len(uncertain_methods)} unverified method calls")
        
        # Check for low confidence items
        low_confidence_items = [item for item in (validation_result.uncertain_items + validation_result.invalid_items) 
                               if item.confidence < 0.3]
        if low_confidence_items:
            issues.append(f"Found {len(low_confidence_items)} items with very low confidence")
        
        return issues
    
    def _assess_risk(self, validation_result: ValidationResult) -> str:
        """Assess overall risk level of potential hallucinations."""
        total_items = validation_result.total_items
        problematic_items = len(validation_result.invalid_items) + len(validation_result.uncertain_items)
        
        if total_items == 0:
            return "Unknown - no items to analyze"
        
        risk_ratio = problematic_items / total_items
        
        if risk_ratio < 0.1:
            return "Low - Few potential issues detected"
        elif risk_ratio < 0.3:
            return "Medium - Some potential hallucinations detected"
        elif risk_ratio < 0.5:
            return "High - Many potential issues detected"
        else:
            return "Critical - Extensive potential hallucinations detected"
    
    def _generate_recommendations(self, validation_result: ValidationResult) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Import recommendations
        unknown_imports = [item for item in validation_result.uncertain_items if item.type == "import"]
        if unknown_imports:
            recommendations.append("Verify all imports are correctly spelled and available in your environment")
        
        # Class recommendations
        uncertain_classes = [item for item in validation_result.uncertain_items if item.type == "class"]
        if uncertain_classes:
            recommendations.append("Check class names against official documentation for correct capitalization and spelling")
        
        # Method recommendations
        uncertain_methods = [item for item in validation_result.uncertain_items if item.type == "method"]
        if uncertain_methods:
            recommendations.append("Verify method names exist on their respective objects using official API documentation")
        
        # General recommendations
        if validation_result.overall_confidence < 0.7:
            recommendations.append("Consider expanding the knowledge base with more comprehensive framework documentation")
        
        if len(validation_result.invalid_items) > 0:
            recommendations.append("Review and correct items marked as invalid before using this code")
        
        return recommendations
    
    def _generate_library_summary(self, validation_result: ValidationResult) -> Dict[str, int]:
        """Generate a summary of library usage patterns."""
        library_counts = {}
        
        # Count imports by library
        for item in validation_result.valid_items + validation_result.uncertain_items:
            if item.type == "import":
                lib_name = item.name.split('.')[0]
                library_counts[lib_name] = library_counts.get(lib_name, 0) + 1
        
        return library_counts
    
    def save_json_report(self, validation_result: ValidationResult, filename: Optional[str] = None) -> Path:
        """Save report as JSON file."""
        if filename is None:
            script_name = Path(validation_result.script_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hallucination_report_{script_name}_{timestamp}.json"
        
        report = self.generate_comprehensive_report(validation_result)
        report_path = self.reports_dir / filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report_path
    
    def save_markdown_report(self, validation_result: ValidationResult, filename: Optional[str] = None) -> Path:
        """Save report as Markdown file."""
        if filename is None:
            script_name = Path(validation_result.script_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hallucination_report_{script_name}_{timestamp}.md"
        
        report = self.generate_comprehensive_report(validation_result)
        report_path = self.reports_dir / filename
        
        markdown_content = self._generate_markdown_content(report, validation_result)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return report_path
    
    def _generate_markdown_content(self, report: Dict[str, Any], validation_result: ValidationResult) -> str:
        """Generate Markdown content from report data."""
        content = f"""# AI Hallucination Detection Report

## Summary
- **Script**: {report['metadata']['script_path']}
- **Analysis Time**: {report['metadata']['analysis_timestamp']}
- **Overall Confidence**: {report['metadata']['overall_confidence']:.2f}
- **Risk Level**: {report['hallucination_analysis']['risk_assessment']}

## Statistics
- **Total Items Analyzed**: {report['statistics']['valid_items'] + report['statistics']['invalid_items'] + report['statistics']['uncertain_items'] + report['statistics']['not_found_items']}
- **Valid Items**: {report['statistics']['valid_items']}
- **Invalid Items**: {report['statistics']['invalid_items']}
- **Uncertain Items**: {report['statistics']['uncertain_items']}
- **Not Found Items**: {report['statistics']['not_found_items']}

## Potential Issues
"""
        
        # Add invalid items
        if validation_result.invalid_items:
            content += "\n### Invalid Items (High Risk)\n"
            for item in validation_result.invalid_items:
                content += f"- **{item.name}** ({item.type}) - {item.details}\n"
                if item.line_number:
                    content += f"  - Line: {item.line_number}\n"
                for suggestion in item.suggestions:
                    content += f"  - Suggestion: {suggestion}\n"
        
        # Add uncertain items
        if validation_result.uncertain_items:
            content += "\n### Uncertain Items (Medium Risk)\n"
            for item in validation_result.uncertain_items[:10]:  # Limit to first 10
                content += f"- **{item.name}** ({item.type}) - Confidence: {item.confidence:.2f}\n"
                content += f"  - {item.details}\n"
                if item.line_number:
                    content += f"  - Line: {item.line_number}\n"
        
        # Add recommendations
        if report['recommendations']:
            content += "\n## Recommendations\n"
            for rec in report['recommendations']:
                content += f"- {rec}\n"
        
        # Add library summary
        if report['library_usage_summary']:
            content += "\n## Library Usage Summary\n"
            for lib, count in sorted(report['library_usage_summary'].items(), key=lambda x: x[1], reverse=True):
                content += f"- **{lib}**: {count} imports\n"
        
        return content
    
    def print_summary(self, validation_result: ValidationResult):
        """Print a concise summary to console."""
        print(f"\n🔍 Hallucination Detection Summary")
        print(f"📄 Script: {validation_result.script_path}")
        print(f"🎯 Overall Confidence: {validation_result.overall_confidence:.2f}")
        print(f"📊 Items Analyzed: {validation_result.total_items}")
        print(f"✅ Valid: {len(validation_result.valid_items)}")
        print(f"❌ Invalid: {len(validation_result.invalid_items)}")
        print(f"⚠️  Uncertain: {len(validation_result.uncertain_items)}")
        
        if validation_result.invalid_items:
            print(f"\n🚨 High Risk Items:")
            for item in validation_result.invalid_items[:5]:
                print(f"  - {item.name} ({item.type}): {item.details}")
        
        if validation_result.uncertain_items:
            print(f"\n⚠️  Medium Risk Items:")
            for item in validation_result.uncertain_items[:5]:
                print(f"  - {item.name} ({item.type}): {item.confidence:.2f} confidence")
        
        report = self.generate_comprehensive_report(validation_result)
        risk_level = report['hallucination_analysis']['risk_assessment']
        print(f"\n🎲 Risk Assessment: {risk_level}")

def main():
    """Main function for testing."""
    print("Hallucination Reporter initialized")
    print(f"Reports will be saved to: {Path('hallucination_reports').absolute()}")

if __name__ == "__main__":
    main()