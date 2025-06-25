#!/usr/bin/env python3
"""
AI Script Analyzer for Ptolemies Hallucination Detection
=======================================================

Analyzes Python scripts using AST to extract imports, classes, methods,
functions, and attributes for validation against knowledge graphs.

Adapted from: https://github.com/coleam00/mcp-crawl4ai-rag/tree/main/knowledge_graphs
"""

import ast
import sys
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ScriptAnalysis:
    """Results of Python script analysis."""
    imports: List[str]
    class_instantiations: List[Dict[str, Any]]
    method_calls: List[Dict[str, Any]]
    function_calls: List[Dict[str, Any]]
    attribute_accesses: List[Dict[str, Any]]
    variables: Dict[str, str]  # variable_name -> inferred_type

class AIScriptAnalyzer:
    """Analyzes Python scripts using AST to identify potential hallucinations."""
    
    def __init__(self):
        self.imports = []
        self.class_instantiations = []
        self.method_calls = []
        self.function_calls = []
        self.attribute_accesses = []
        self.variables = {}
        self.context_stack = []  # Track context for method calls
        
    def analyze_script(self, script_content: str) -> ScriptAnalysis:
        """Analyze a Python script and extract all relevant elements."""
        try:
            tree = ast.parse(script_content)
            self._analyze_node(tree)
            
            return ScriptAnalysis(
                imports=self.imports.copy(),
                class_instantiations=self.class_instantiations.copy(),
                method_calls=self.method_calls.copy(),
                function_calls=self.function_calls.copy(),
                attribute_accesses=self.attribute_accesses.copy(),
                variables=self.variables.copy()
            )
        except SyntaxError as e:
            print(f"Syntax error in script: {e}")
            return ScriptAnalysis([], [], [], [], [], {})
    
    def _analyze_node(self, node: ast.AST):
        """Recursively analyze AST nodes."""
        if isinstance(node, ast.Import):
            self._handle_import(node)
        elif isinstance(node, ast.ImportFrom):
            self._handle_import_from(node)
        elif isinstance(node, ast.Assign):
            self._handle_assignment(node)
        elif isinstance(node, ast.Call):
            self._handle_call(node)
        elif isinstance(node, ast.Attribute):
            self._handle_attribute(node)
        elif isinstance(node, ast.With):
            self._handle_with(node)
        
        # Recursively analyze child nodes
        for child in ast.iter_child_nodes(node):
            self._analyze_node(child)
    
    def _handle_import(self, node: ast.Import):
        """Handle import statements."""
        for alias in node.names:
            import_name = alias.asname if alias.asname else alias.name
            self.imports.append(alias.name)
            
            # Track imported modules as variables
            self.variables[import_name] = f"module:{alias.name}"
    
    def _handle_import_from(self, node: ast.ImportFrom):
        """Handle from...import statements."""
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            import_name = alias.asname if alias.asname else alias.name
            
            self.imports.append(full_name)
            self.variables[import_name] = f"imported:{full_name}"
    
    def _handle_assignment(self, node: ast.Assign):
        """Handle variable assignments."""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            var_type = self._infer_type(node.value)
            self.variables[var_name] = var_type
    
    def _handle_call(self, node: ast.Call):
        """Handle function and method calls."""
        if isinstance(node.func, ast.Name):
            # Function call: func()
            func_name = node.func.id
            args = self._extract_args(node)
            
            # Check if this is a class instantiation
            if func_name in self.variables:
                var_type = self.variables[func_name]
                if var_type.startswith("imported:") and func_name[0].isupper():
                    # Likely class instantiation
                    class_name = var_type.split(":", 1)[1]
                    self.class_instantiations.append({
                        "class_name": class_name,
                        "args": args,
                        "line": getattr(node, 'lineno', 0)
                    })
                else:
                    self.function_calls.append({
                        "function_name": func_name,
                        "args": args,
                        "line": getattr(node, 'lineno', 0)
                    })
            else:
                # Could be class instantiation or function call
                if func_name[0].isupper():
                    self.class_instantiations.append({
                        "class_name": func_name,
                        "args": args,
                        "line": getattr(node, 'lineno', 0)
                    })
                else:
                    self.function_calls.append({
                        "function_name": func_name,
                        "args": args,
                        "line": getattr(node, 'lineno', 0)
                    })
        
        elif isinstance(node.func, ast.Attribute):
            # Method call: obj.method()
            obj_name = self._get_object_name(node.func.value)
            method_name = node.func.attr
            args = self._extract_args(node)
            
            # Determine object type
            obj_type = self.variables.get(obj_name, "unknown")
            
            self.method_calls.append({
                "object_name": obj_name,
                "object_type": obj_type,
                "method_name": method_name,
                "full_call": f"{obj_name}.{method_name}",
                "args": args,
                "line": getattr(node, 'lineno', 0)
            })
    
    def _handle_attribute(self, node: ast.Attribute):
        """Handle attribute access."""
        if not isinstance(node.ctx, ast.Load):
            return  # Only track attribute reads, not writes
            
        obj_name = self._get_object_name(node.value)
        attr_name = node.attr
        
        # Determine object type
        obj_type = self.variables.get(obj_name, "unknown")
        
        self.attribute_accesses.append({
            "object_name": obj_name,
            "object_type": obj_type,
            "attribute_name": attr_name,
            "full_access": f"{obj_name}.{attr_name}",
            "line": getattr(node, 'lineno', 0)
        })
    
    def _handle_with(self, node: ast.With):
        """Handle context managers (with statements)."""
        for item in node.items:
            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                var_name = item.optional_vars.id
                context_type = self._infer_type(item.context_expr)
                self.variables[var_name] = context_type
    
    def _extract_args(self, node: ast.Call) -> List[str]:
        """Extract argument names/values from a function call."""
        args = []
        
        for arg in node.args:
            args.append(self._node_to_string(arg))
        
        for keyword in node.keywords:
            args.append(f"{keyword.arg}={self._node_to_string(keyword.value)}")
        
        return args
    
    def _get_object_name(self, node: ast.AST) -> str:
        """Get the name of an object from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_object_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_object_name(node.func)
        else:
            return "unknown"
    
    def _infer_type(self, node: ast.AST) -> str:
        """Infer the type of a value from an AST node."""
        if isinstance(node, ast.Call):
            func_name = self._get_object_name(node.func)
            if func_name in self.variables:
                var_type = self.variables[func_name]
                if var_type.startswith("imported:"):
                    return f"instance:{var_type.split(':', 1)[1]}"
            return f"instance:{func_name}"
        elif isinstance(node, ast.Name):
            return self.variables.get(node.id, "unknown")
        elif isinstance(node, ast.Str):
            return "str"
        elif isinstance(node, ast.Num):
            return "number"
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        else:
            return "unknown"
    
    def _node_to_string(self, node: ast.AST) -> str:
        """Convert an AST node to a string representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Str):
            return f"'{node.s}'"
        elif isinstance(node, ast.Num):
            return str(node.n)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return f"'{node.value}'"
            return str(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{self._node_to_string(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            func = self._node_to_string(node.func)
            args = [self._node_to_string(arg) for arg in node.args]
            return f"{func}({', '.join(args)})"
        else:
            return "unknown"

def main():
    """Main function for command-line usage."""
    if len(sys.argv) != 2:
        print("Usage: python ai_script_analyzer.py <script_path>")
        sys.exit(1)
    
    script_path = Path(sys.argv[1])
    if not script_path.exists():
        print(f"Error: Script {script_path} does not exist")
        sys.exit(1)
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        analyzer = AIScriptAnalyzer()
        analysis = analyzer.analyze_script(script_content)
        
        print(f"Analysis of {script_path}:")
        print(f"Imports: {len(analysis.imports)}")
        for imp in analysis.imports:
            print(f"  - {imp}")
        
        print(f"\nClass Instantiations: {len(analysis.class_instantiations)}")
        for cls in analysis.class_instantiations:
            print(f"  - {cls['class_name']} (line {cls['line']})")
        
        print(f"\nMethod Calls: {len(analysis.method_calls)}")
        for method in analysis.method_calls:
            print(f"  - {method['full_call']} (line {method['line']})")
        
        print(f"\nFunction Calls: {len(analysis.function_calls)}")
        for func in analysis.function_calls:
            print(f"  - {func['function_name']} (line {func['line']})")
        
        print(f"\nAttribute Accesses: {len(analysis.attribute_accesses)}")
        for attr in analysis.attribute_accesses:
            print(f"  - {attr['full_access']} (line {attr['line']})")
        
    except Exception as e:
        print(f"Error analyzing script: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()