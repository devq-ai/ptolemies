#!/usr/bin/env python3
"""
Knowledge Graph Validator for Ptolemies Hallucination Detection
==============================================================

Validates AI-generated code elements against Neo4j knowledge graph
to detect potential hallucinations.

Adapted from: https://github.com/coleam00/mcp-crawl4ai-rag/tree/main/knowledge_graphs
"""

import asyncio
import subprocess
import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

class ValidationStatus(Enum):
    """Status of validation for a code element."""
    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"
    NOT_FOUND = "not_found"

@dataclass
class ValidationItem:
    """Single validation result item."""
    name: str
    type: str  # 'import', 'class', 'method', 'function', 'attribute'
    status: ValidationStatus
    confidence: float
    details: str
    suggestions: List[str]
    line_number: Optional[int] = None

@dataclass
class ValidationResult:
    """Complete validation results."""
    script_path: str
    total_items: int
    valid_items: List[ValidationItem]
    invalid_items: List[ValidationItem]
    uncertain_items: List[ValidationItem]
    not_found_items: List[ValidationItem]
    overall_confidence: float
    summary: str

class KnowledgeGraphValidator:
    """Validates code elements against Neo4j knowledge graph."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", 
                 neo4j_password: str = "ptolemies"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.cache = {}  # Simple cache for repeated queries
    
    def run_neo4j_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute Neo4j query and return results."""
        if query in self.cache:
            return self.cache[query]
        
        cmd = [
            'cypher-shell',
            '-a', self.neo4j_uri,
            '-u', self.neo4j_user,
            '-p', self.neo4j_password,
            '-d', 'neo4j',
            '--format', 'plain'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input=query,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse plain format results
                lines = result.stdout.strip().split('\n')
                if len(lines) < 2:  # No data rows
                    self.cache[query] = []
                    return []
                
                # Skip header line, parse data
                results = []
                headers = [h.strip('"') for h in lines[0].split(', ')]
                
                for line in lines[1:]:
                    if line.strip():
                        values = [v.strip('"') for v in line.split(', ')]
                        if len(values) == len(headers):
                            row_dict = dict(zip(headers, values))
                            results.append(row_dict)
                
                self.cache[query] = results
                return results
            else:
                print(f"Neo4j query failed: {result.stderr}")
                return []
                
        except Exception as e:
            print(f"Neo4j query error: {e}")
            return []
    
    def validate_imports(self, imports: List[str]) -> List[ValidationItem]:
        """Validate import statements against known frameworks."""
        validation_items = []
        
        # Get known frameworks and modules
        query = """
        MATCH (f:Framework)
        RETURN f.name as framework_name, f.language as language
        """
        
        frameworks = self.run_neo4j_query(query)
        known_frameworks = {f.get('framework_name', '').lower() for f in frameworks}
        
        # Standard library modules (partial list)
        stdlib_modules = {
            'os', 'sys', 'json', 'ast', 'subprocess', 'datetime', 'time', 'typing',
            'dataclasses', 'enum', 're', 'math', 'random', 'collections', 'itertools',
            'functools', 'pathlib', 'urllib', 'http', 'sqlite3', 'csv', 'io', 'asyncio'
        }
        
        for import_name in imports:
            base_module = import_name.split('.')[0].lower()
            
            if base_module in stdlib_modules:
                validation_items.append(ValidationItem(
                    name=import_name,
                    type="import",
                    status=ValidationStatus.VALID,
                    confidence=1.0,
                    details="Standard library module",
                    suggestions=[]
                ))
            elif base_module in known_frameworks:
                validation_items.append(ValidationItem(
                    name=import_name,
                    type="import",
                    status=ValidationStatus.VALID,
                    confidence=0.9,
                    details="Known framework in knowledge base",
                    suggestions=[]
                ))
            elif base_module in {'fastapi', 'pydantic', 'logfire', 'openai', 'requests', 'httpx'}:
                validation_items.append(ValidationItem(
                    name=import_name,
                    type="import",
                    status=ValidationStatus.VALID,
                    confidence=0.8,
                    details="Common third-party library",
                    suggestions=[]
                ))
            else:
                validation_items.append(ValidationItem(
                    name=import_name,
                    type="import",
                    status=ValidationStatus.UNCERTAIN,
                    confidence=0.3,
                    details="Unknown module, may be hallucinated",
                    suggestions=[f"Verify that '{import_name}' exists and is correctly named"]
                ))
        
        return validation_items
    
    def validate_class_instantiations(self, class_instantiations: List[Dict[str, Any]]) -> List[ValidationItem]:
        """Validate class instantiations against known classes."""
        validation_items = []
        
        # Get known classes
        query = """
        MATCH (c:Class)
        RETURN c.name as class_name, c.full_name as full_name, c.module as module
        """
        
        known_classes = self.run_neo4j_query(query)
        class_names = {c.get('class_name', '') for c in known_classes}
        full_names = {c.get('full_name', '') for c in known_classes}
        
        for class_inst in class_instantiations:
            class_name = class_inst.get('class_name', '')
            line_num = class_inst.get('line', 0)
            
            if class_name in class_names or any(class_name in fn for fn in full_names):
                validation_items.append(ValidationItem(
                    name=class_name,
                    type="class",
                    status=ValidationStatus.VALID,
                    confidence=0.9,
                    details="Class found in knowledge base",
                    suggestions=[],
                    line_number=line_num
                ))
            else:
                # Check if it looks like a valid class name
                if class_name and class_name[0].isupper() and class_name.isidentifier():
                    validation_items.append(ValidationItem(
                        name=class_name,
                        type="class",
                        status=ValidationStatus.UNCERTAIN,
                        confidence=0.4,
                        details="Class not found in knowledge base",
                        suggestions=[f"Verify that class '{class_name}' exists"],
                        line_number=line_num
                    ))
                else:
                    validation_items.append(ValidationItem(
                        name=class_name,
                        type="class",
                        status=ValidationStatus.INVALID,
                        confidence=0.1,
                        details="Invalid class name format",
                        suggestions=[f"Check class name '{class_name}' for typos"],
                        line_number=line_num
                    ))
        
        return validation_items
    
    def validate_method_calls(self, method_calls: List[Dict[str, Any]]) -> List[ValidationItem]:
        """Validate method calls against known methods."""
        validation_items = []
        
        # Get known methods
        query = """
        MATCH (m:Method)
        RETURN m.name as method_name, m.full_name as full_name
        """
        
        known_methods = self.run_neo4j_query(query)
        method_names = {m.get('method_name', '') for m in known_methods}
        method_full_names = {m.get('full_name', '') for m in known_methods}
        
        # Common method patterns
        common_methods = {
            'get', 'post', 'put', 'delete', 'patch',  # HTTP methods
            'read', 'write', 'close', 'open',  # File operations
            'append', 'insert', 'remove', 'pop',  # List operations
            'keys', 'values', 'items', 'get',  # Dict operations
            'strip', 'split', 'join', 'replace',  # String operations
            'start', 'stop', 'run', 'execute'  # General operations
        }
        
        for method_call in method_calls:
            method_name = method_call.get('method_name', '')
            full_call = method_call.get('full_call', '')
            line_num = method_call.get('line', 0)
            
            if method_name in method_names or any(method_name in fn for fn in method_full_names):
                validation_items.append(ValidationItem(
                    name=full_call,
                    type="method",
                    status=ValidationStatus.VALID,
                    confidence=0.9,
                    details="Method found in knowledge base",
                    suggestions=[],
                    line_number=line_num
                ))
            elif method_name in common_methods:
                validation_items.append(ValidationItem(
                    name=full_call,
                    type="method",
                    status=ValidationStatus.VALID,
                    confidence=0.7,
                    details="Common method pattern",
                    suggestions=[],
                    line_number=line_num
                ))
            elif method_name.startswith('_'):
                validation_items.append(ValidationItem(
                    name=full_call,
                    type="method",
                    status=ValidationStatus.UNCERTAIN,
                    confidence=0.5,
                    details="Private method, may be implementation-specific",
                    suggestions=[],
                    line_number=line_num
                ))
            else:
                validation_items.append(ValidationItem(
                    name=full_call,
                    type="method",
                    status=ValidationStatus.UNCERTAIN,
                    confidence=0.3,
                    details="Method not found in knowledge base",
                    suggestions=[f"Verify that method '{method_name}' exists on this object"],
                    line_number=line_num
                ))
        
        return validation_items
    
    def validate_function_calls(self, function_calls: List[Dict[str, Any]]) -> List[ValidationItem]:
        """Validate function calls against known functions."""
        validation_items = []
        
        # Get known functions
        query = """
        MATCH (f:Function)
        RETURN f.name as function_name, f.full_name as full_name
        """
        
        known_functions = self.run_neo4j_query(query)
        function_names = {f.get('function_name', '') for f in known_functions}
        
        # Built-in Python functions
        builtin_functions = {
            'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
            'enumerate', 'zip', 'range', 'sum', 'max', 'min', 'sorted', 'reversed',
            'isinstance', 'hasattr', 'getattr', 'setattr', 'type', 'open', 'super',
            'abs', 'round', 'pow', 'divmod', 'all', 'any', 'filter', 'map'
        }
        
        for func_call in function_calls:
            func_name = func_call.get('function_name', '')
            line_num = func_call.get('line', 0)
            
            if func_name in builtin_functions:
                validation_items.append(ValidationItem(
                    name=func_name,
                    type="function",
                    status=ValidationStatus.VALID,
                    confidence=1.0,
                    details="Built-in Python function",
                    suggestions=[],
                    line_number=line_num
                ))
            elif func_name in function_names:
                validation_items.append(ValidationItem(
                    name=func_name,
                    type="function",
                    status=ValidationStatus.VALID,
                    confidence=0.9,
                    details="Function found in knowledge base",
                    suggestions=[],
                    line_number=line_num
                ))
            else:
                validation_items.append(ValidationItem(
                    name=func_name,
                    type="function",
                    status=ValidationStatus.UNCERTAIN,
                    confidence=0.4,
                    details="Function not found in knowledge base",
                    suggestions=[f"Verify that function '{func_name}' exists and is imported"],
                    line_number=line_num
                ))
        
        return validation_items
    
    def validate_attribute_accesses(self, attribute_accesses: List[Dict[str, Any]]) -> List[ValidationItem]:
        """Validate attribute accesses against known attributes."""
        validation_items = []
        
        # Common attribute patterns
        common_attributes = {
            'name', 'id', 'value', 'data', 'content', 'text', 'url', 'path',
            'status', 'code', 'message', 'result', 'response', 'error',
            'size', 'length', 'count', 'index', 'key', 'type'
        }
        
        for attr_access in attribute_accesses:
            attr_name = attr_access.get('attribute_name', '')
            full_access = attr_access.get('full_access', '')
            line_num = attr_access.get('line', 0)
            
            if attr_name in common_attributes:
                validation_items.append(ValidationItem(
                    name=full_access,
                    type="attribute",
                    status=ValidationStatus.VALID,
                    confidence=0.7,
                    details="Common attribute pattern",
                    suggestions=[],
                    line_number=line_num
                ))
            elif attr_name.startswith('_'):
                validation_items.append(ValidationItem(
                    name=full_access,
                    type="attribute",
                    status=ValidationStatus.UNCERTAIN,
                    confidence=0.5,
                    details="Private attribute access",
                    suggestions=[],
                    line_number=line_num
                ))
            else:
                validation_items.append(ValidationItem(
                    name=full_access,
                    type="attribute",
                    status=ValidationStatus.UNCERTAIN,
                    confidence=0.4,
                    details="Attribute not verified",
                    suggestions=[f"Verify that attribute '{attr_name}' exists on this object"],
                    line_number=line_num
                ))
        
        return validation_items
    
    def validate_script_analysis(self, script_path: str, analysis: Any) -> ValidationResult:
        """Validate complete script analysis results."""
        all_validation_items = []
        
        # Validate each category
        all_validation_items.extend(self.validate_imports(analysis.imports))
        all_validation_items.extend(self.validate_class_instantiations(analysis.class_instantiations))
        all_validation_items.extend(self.validate_method_calls(analysis.method_calls))
        all_validation_items.extend(self.validate_function_calls(analysis.function_calls))
        all_validation_items.extend(self.validate_attribute_accesses(analysis.attribute_accesses))
        
        # Categorize results
        valid_items = [item for item in all_validation_items if item.status == ValidationStatus.VALID]
        invalid_items = [item for item in all_validation_items if item.status == ValidationStatus.INVALID]
        uncertain_items = [item for item in all_validation_items if item.status == ValidationStatus.UNCERTAIN]
        not_found_items = [item for item in all_validation_items if item.status == ValidationStatus.NOT_FOUND]
        
        # Calculate overall confidence
        if all_validation_items:
            total_confidence = sum(item.confidence for item in all_validation_items)
            overall_confidence = total_confidence / len(all_validation_items)
        else:
            overall_confidence = 0.0
        
        # Generate summary
        total_items = len(all_validation_items)
        valid_count = len(valid_items)
        invalid_count = len(invalid_items)
        uncertain_count = len(uncertain_items)
        
        summary = f"Analyzed {total_items} code elements: {valid_count} valid, {invalid_count} invalid, {uncertain_count} uncertain"
        
        return ValidationResult(
            script_path=script_path,
            total_items=total_items,
            valid_items=valid_items,
            invalid_items=invalid_items,
            uncertain_items=uncertain_items,
            not_found_items=not_found_items,
            overall_confidence=overall_confidence,
            summary=summary
        )

def main():
    """Main function for testing."""
    validator = KnowledgeGraphValidator()
    
    # Test query
    print("Testing knowledge graph connection...")
    frameworks = validator.run_neo4j_query("MATCH (f:Framework) RETURN f.name LIMIT 3")
    print(f"Found {len(frameworks)} frameworks in knowledge base")
    
    if frameworks:
        print("Knowledge graph validator is ready!")
    else:
        print("Warning: No frameworks found in knowledge base")

if __name__ == "__main__":
    main()