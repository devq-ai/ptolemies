#!/usr/bin/env python3
"""
Generate Code Documentation for Ptolemies Knowledge Base
=======================================================

Analyzes Python code to extract classes, methods, and functions,
then generates documentation to fill gaps in our knowledge base.

This script prepares documentation that can be stored via context7
when the MCP server is operational.
"""

import ast
import os
import json
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import subprocess

@dataclass
class CodeElement:
    """Represents a code element (class, method, function)."""
    name: str
    full_name: str
    type: str  # 'class', 'method', 'function'
    module: str
    file_path: str
    line_number: int
    docstring: Optional[str]
    parameters: List[str]
    return_type: Optional[str]
    decorators: List[str]
    is_async: bool = False
    parent_class: Optional[str] = None

class CodeDocumentationGenerator:
    """Generates documentation for Python code elements."""
    
    def __init__(self, project_root: str = "/Users/dionedge/devqai/ptolemies"):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"
        self.code_elements: List[CodeElement] = []
        self.existing_elements: Set[str] = set()
        
    def analyze_project(self) -> Dict[str, Any]:
        """Analyze entire project for code elements."""
        print("🔍 Analyzing Ptolemies codebase...")
        
        # Get existing elements from Neo4j
        self._load_existing_elements()
        
        # Analyze all Python files
        python_files = list(self.src_dir.glob("**/*.py"))
        
        for py_file in python_files:
            if "__pycache__" not in str(py_file):
                self._analyze_file(py_file)
        
        # Identify gaps
        gaps = self._identify_documentation_gaps()
        
        return {
            "total_files": len(python_files),
            "total_elements": len(self.code_elements),
            "classes": len([e for e in self.code_elements if e.type == "class"]),
            "methods": len([e for e in self.code_elements if e.type == "method"]),
            "functions": len([e for e in self.code_elements if e.type == "function"]),
            "documented": len([e for e in self.code_elements if e.docstring]),
            "undocumented": len([e for e in self.code_elements if not e.docstring]),
            "gaps": gaps
        }
    
    def _load_existing_elements(self):
        """Load existing code elements from Neo4j."""
        query = """
        MATCH (n)
        WHERE n:Class OR n:Method OR n:Function
        RETURN n.full_name as full_name
        """
        
        try:
            cmd = [
                'cypher-shell',
                '-a', 'bolt://localhost:7687',
                '-u', 'neo4j',
                '-p', 'ptolemies',
                '-d', 'neo4j',
                '--format', 'json'
            ]
            
            result = subprocess.run(
                cmd,
                input=query,
                text=True,
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    try:
                        data = json.loads(line)
                        if data.get('full_name'):
                            self.existing_elements.add(data['full_name'])
                    except:
                        pass
                        
        except Exception as e:
            print(f"⚠️  Could not load existing elements: {e}")
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            # Add parent references for context
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    child.parent = node
            
            # Extract elements
            module_name = self._get_module_name(file_path)
            self._extract_elements(tree, module_name, str(file_path))
            
        except Exception as e:
            print(f"⚠️  Error analyzing {file_path}: {e}")
    
    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path."""
        relative_path = file_path.relative_to(self.project_root)
        module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
        return '.'.join(module_parts)
    
    def _extract_elements(self, tree: ast.AST, module: str, file_path: str):
        """Extract code elements from AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._extract_class(node, module, file_path)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Check if it's a method or function
                parent = getattr(node, 'parent', None)
                if isinstance(parent, ast.ClassDef):
                    self._extract_method(node, parent.name, module, file_path)
                else:
                    self._extract_function(node, module, file_path)
    
    def _extract_class(self, node: ast.ClassDef, module: str, file_path: str):
        """Extract class information."""
        element = CodeElement(
            name=node.name,
            full_name=f"{module}.{node.name}",
            type="class",
            module=module,
            file_path=file_path,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            parameters=[],
            return_type=None,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list]
        )
        
        self.code_elements.append(element)
    
    def _extract_method(self, node, class_name: str, module: str, file_path: str):
        """Extract method information."""
        parameters = []
        for arg in node.args.args:
            param_name = arg.arg
            if hasattr(arg, 'annotation') and arg.annotation:
                param_type = ast.unparse(arg.annotation)
                parameters.append(f"{param_name}: {param_type}")
            else:
                parameters.append(param_name)
        
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)
        
        element = CodeElement(
            name=node.name,
            full_name=f"{module}.{class_name}.{node.name}",
            type="method",
            module=module,
            file_path=file_path,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            parameters=parameters,
            return_type=return_type,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            is_async=isinstance(node, ast.AsyncFunctionDef),
            parent_class=class_name
        )
        
        self.code_elements.append(element)
    
    def _extract_function(self, node, module: str, file_path: str):
        """Extract function information."""
        parameters = []
        for arg in node.args.args:
            param_name = arg.arg
            if hasattr(arg, 'annotation') and arg.annotation:
                param_type = ast.unparse(arg.annotation)
                parameters.append(f"{param_name}: {param_type}")
            else:
                parameters.append(param_name)
        
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)
        
        element = CodeElement(
            name=node.name,
            full_name=f"{module}.{node.name}",
            type="function",
            module=module,
            file_path=file_path,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            parameters=parameters,
            return_type=return_type,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            is_async=isinstance(node, ast.AsyncFunctionDef)
        )
        
        self.code_elements.append(element)
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return f"{decorator.func.value.id}.{decorator.func.attr}"
        return "unknown"
    
    def _identify_documentation_gaps(self) -> Dict[str, List[CodeElement]]:
        """Identify gaps in documentation."""
        gaps = {
            "missing_in_neo4j": [],
            "missing_docstrings": [],
            "key_classes": [],
            "key_methods": [],
            "key_functions": []
        }
        
        # Key class patterns
        key_patterns = [
            "Crawler", "Builder", "Manager", "Engine", "Integration",
            "Server", "Client", "Handler", "Processor", "Analyzer"
        ]
        
        for element in self.code_elements:
            # Check if missing from Neo4j
            if element.full_name not in self.existing_elements:
                gaps["missing_in_neo4j"].append(element)
            
            # Check for missing docstrings
            if not element.docstring:
                gaps["missing_docstrings"].append(element)
            
            # Identify key elements
            if element.type == "class":
                if any(pattern in element.name for pattern in key_patterns):
                    gaps["key_classes"].append(element)
            elif element.type == "method" and element.name in ["__init__", "process", "execute", "run", "handle"]:
                gaps["key_methods"].append(element)
            elif element.type == "function" and any(kw in element.name for kw in ["create", "build", "process", "analyze"]):
                gaps["key_functions"].append(element)
        
        return gaps
    
    def generate_documentation_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a documentation report."""
        gaps = analysis["gaps"]
        
        report = f"""# Ptolemies Code Documentation Analysis
=======================================

## Summary
- **Total Files Analyzed**: {analysis['total_files']}
- **Total Code Elements**: {analysis['total_elements']}
  - Classes: {analysis['classes']}
  - Methods: {analysis['methods']}
  - Functions: {analysis['functions']}
- **Documentation Coverage**:
  - Documented: {analysis['documented']} ({analysis['documented']/max(analysis['total_elements'], 1)*100:.1f}%)
  - Undocumented: {analysis['undocumented']} ({analysis['undocumented']/max(analysis['total_elements'], 1)*100:.1f}%)

## Documentation Gaps

### Missing from Neo4j Knowledge Base
Total: {len(gaps['missing_in_neo4j'])} elements

Top 10 missing elements:
"""
        
        for element in gaps['missing_in_neo4j'][:10]:
            report += f"- **{element.full_name}** ({element.type})\n"
            report += f"  - File: {element.file_path}:{element.line_number}\n"
            if element.docstring:
                report += f"  - Doc: {element.docstring[:100]}...\n"
        
        report += f"""

### Key Classes Identified
Total: {len(gaps['key_classes'])} classes

"""
        
        for cls in gaps['key_classes'][:5]:
            report += f"#### {cls.name}\n"
            report += f"- Module: `{cls.module}`\n"
            report += f"- File: {cls.file_path}:{cls.line_number}\n"
            if cls.decorators:
                report += f"- Decorators: {', '.join(cls.decorators)}\n"
            if cls.docstring:
                report += f"- Description: {cls.docstring[:200]}...\n"
            report += "\n"
        
        report += f"""

### Missing Docstrings
Total: {len(gaps['missing_docstrings'])} elements need documentation

Top undocumented elements:
"""
        
        for element in gaps['missing_docstrings'][:10]:
            report += f"- **{element.full_name}** ({element.type})\n"
        
        report += """

## Recommended Actions

1. **Generate Documentation for Key Classes**:
   - Use context7 to generate comprehensive docs for crawler classes
   - Focus on ProductionCrawlerHybrid, specialized crawlers, and integrations

2. **Add to Neo4j Knowledge Graph**:
   - Import class/method/function definitions
   - Create relationships between code elements
   - Link to framework documentation

3. **Create Code Examples**:
   - Document usage patterns for key classes
   - Add examples for common operations
   - Include performance considerations

4. **Fill Docstring Gaps**:
   - Generate docstrings for undocumented methods
   - Add parameter descriptions and return types
   - Include usage examples

## Context7 Integration

When context7 is operational, use these commands:

```markdown
# Store class documentation
"Use context7 to store documentation for ProductionCrawlerHybrid class"

# Search for patterns
"Use context7 to search for crawler implementation patterns"

# Generate examples
"Use context7 to generate usage examples for HybridQueryEngine"
```
"""
        
        return report
    
    def export_for_context7(self, gaps: Dict[str, List[CodeElement]]) -> List[Dict[str, Any]]:
        """Export documentation tasks for context7."""
        tasks = []
        
        # Priority 1: Key classes without docs
        for cls in gaps['key_classes'][:10]:
            tasks.append({
                "priority": "high",
                "type": "generate_class_doc",
                "element": {
                    "name": cls.name,
                    "full_name": cls.full_name,
                    "module": cls.module,
                    "file": cls.file_path,
                    "line": cls.line_number,
                    "has_docstring": bool(cls.docstring),
                    "decorators": cls.decorators
                },
                "action": f"Generate comprehensive documentation for {cls.name} class"
            })
        
        # Priority 2: Key methods
        for method in gaps['key_methods'][:10]:
            tasks.append({
                "priority": "medium",
                "type": "generate_method_doc",
                "element": {
                    "name": method.name,
                    "full_name": method.full_name,
                    "class": method.parent_class,
                    "parameters": method.parameters,
                    "return_type": method.return_type,
                    "is_async": method.is_async
                },
                "action": f"Document {method.name} method in {method.parent_class}"
            })
        
        return tasks

def main():
    """Main execution function."""
    print("🚀 Ptolemies Code Documentation Generator")
    print("=" * 45)
    
    generator = CodeDocumentationGenerator()
    
    # Analyze project
    print("\n📊 Analyzing codebase...")
    analysis = generator.analyze_project()
    
    # Generate report
    print("\n📝 Generating documentation report...")
    report = generator.generate_documentation_report(analysis)
    
    # Save report
    with open("code_documentation_gaps.md", "w") as f:
        f.write(report)
    print("✅ Saved: code_documentation_gaps.md")
    
    # Export tasks for context7
    tasks = generator.export_for_context7(analysis["gaps"])
    with open("context7_documentation_tasks.json", "w") as f:
        json.dump(tasks, f, indent=2)
    print("✅ Saved: context7_documentation_tasks.json")
    
    # Summary
    print(f"\n📈 Analysis Complete:")
    print(f"  Total elements: {analysis['total_elements']}")
    print(f"  Documentation coverage: {analysis['documented']/max(analysis['total_elements'], 1)*100:.1f}%")
    print(f"  Missing from Neo4j: {len(analysis['gaps']['missing_in_neo4j'])}")
    print(f"  Key classes found: {len(analysis['gaps']['key_classes'])}")
    
    print("\n💡 Next Steps:")
    print("1. Review code_documentation_gaps.md")
    print("2. Use context7 to generate missing documentation")
    print("3. Import generated docs into Neo4j knowledge graph")
    print("4. Link code elements to framework documentation")

if __name__ == "__main__":
    main()