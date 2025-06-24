# AI Hallucination Detection Report

## Summary
- **Script**: test_hallucination_sample.py
- **Analysis Time**: 2025-06-24T09:43:24.986476
- **Overall Confidence**: 0.51
- **Risk Level**: Critical - Extensive potential hallucinations detected

## Statistics
- **Total Items Analyzed**: 23
- **Valid Items**: 8
- **Invalid Items**: 3
- **Uncertain Items**: 12
- **Not Found Items**: 0

## Potential Issues

### Invalid Items (High Risk)
- **fastapi.FastAPI** (class) - Invalid class name format
  - Line: 21
  - Suggestion: Check class name 'fastapi.FastAPI' for typos
- **nonexistent_framework.MagicAPI** (class) - Invalid class name format
  - Line: 28
  - Suggestion: Check class name 'nonexistent_framework.MagicAPI' for typos
- **imaginary_lib.FakeClass** (class) - Invalid class name format
  - Line: 29
  - Suggestion: Check class name 'imaginary_lib.FakeClass' for typos

### Uncertain Items (Medium Risk)
- **nonexistent_framework.MagicAPI** (import) - Confidence: 0.30
  - Unknown module, may be hallucinated
- **imaginary_lib.FakeClass** (import) - Confidence: 0.30
  - Unknown module, may be hallucinated
- **magic_app.super_method** (method) - Confidence: 0.30
  - Method not found in knowledge base
  - Line: 37
- **fake_obj.nonexistent_function** (method) - Confidence: 0.30
  - Method not found in knowledge base
  - Line: 38
- **imaginary_function** (function) - Confidence: 0.40
  - Function not found in knowledge base
  - Line: 45
- **another_fake_func** (function) - Confidence: 0.40
  - Function not found in knowledge base
  - Line: 46
- **app.get** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 32
- **magic_app.super_method** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 37
- **fake_obj.nonexistent_function** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 38
- **app.title** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 49

## Recommendations
- Verify all imports are correctly spelled and available in your environment
- Verify method names exist on their respective objects using official API documentation
- Consider expanding the knowledge base with more comprehensive framework documentation
- Review and correct items marked as invalid before using this code

## Library Usage Summary
- **os**: 1 imports
- **json**: 1 imports
- **fastapi**: 1 imports
- **pydantic**: 1 imports
- **nonexistent_framework**: 1 imports
- **imaginary_lib**: 1 imports
