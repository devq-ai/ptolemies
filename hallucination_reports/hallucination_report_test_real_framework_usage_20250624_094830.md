# AI Hallucination Detection Report

## Summary
- **Script**: test_real_framework_usage.py
- **Analysis Time**: 2025-06-24T09:48:30.516213
- **Overall Confidence**: 0.54
- **Risk Level**: Critical - Extensive potential hallucinations detected

## Statistics
- **Total Items Analyzed**: 18
- **Valid Items**: 8
- **Invalid Items**: 2
- **Uncertain Items**: 8
- **Not Found Items**: 0

## Potential Issues

### Invalid Items (High Risk)
- **fastapi.FastAPI** (class) - Invalid class name format
  - Line: 14
  - Suggestion: Check class name 'fastapi.FastAPI' for typos
- **pydantic_ai.Agent** (class) - Invalid class name format
  - Line: 36
  - Suggestion: Check class name 'pydantic_ai.Agent' for typos

### Uncertain Items (Medium Risk)
- **pydantic_ai.Agent** (import) - Confidence: 0.30
  - Unknown module, may be hallucinated
- **app.unknown_method** (method) - Confidence: 0.30
  - Method not found in knowledge base
  - Line: 46
- **app.get** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 20
- **app.get** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 24
- **app.post** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 28
- **agent.system_prompt** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 38
- **app.unknown_method** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 46
- **user.fake_attribute** (attribute) - Confidence: 0.40
  - Attribute not verified
  - Line: 47

## Recommendations
- Verify all imports are correctly spelled and available in your environment
- Verify method names exist on their respective objects using official API documentation
- Consider expanding the knowledge base with more comprehensive framework documentation
- Review and correct items marked as invalid before using this code

## Library Usage Summary
- **fastapi**: 3 imports
- **pydantic**: 1 imports
- **pydantic_ai**: 1 imports
