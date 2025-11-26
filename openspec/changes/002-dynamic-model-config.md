# Change Proposal: Dynamic Model Configuration via models.json

**ID**: 002-dynamic-model-config  
**Date**: 2025-11-26  
**Status**: ✅ Implemented  
**Type**: Feature Enhancement / Configuration Management

## Summary

Replace hardcoded model identifiers in `backend/config.py` with a dynamic `models.json` configuration file, enabling runtime model configuration changes without code modifications.

## Motivation

- **Flexibility**: Change model lineup without editing Python code
- **Experimentation**: Easy A/B testing of different model combinations
- **Deployment**: Update models in production without code changes
- **User Experience**: Potential for future UI-based model configuration
- **Maintenance**: Cleaner separation of configuration from code

## Current State

Model configuration is hardcoded in `backend/config.py`:
```python
COUNCIL_MODELS = [
    "microsoft/phi-4-mini-reasoning",
    "apollo-v0.1-4b-thinking-qx86x-hi-mlx",
    "ai21-jamba-reasoning-3b-hi-mlx",
]

CHAIRMAN_MODEL = "qwen/qwen3-4b-thinking-2507"
```

## Proposed Changes

### File Structure
Create `models.json` in project root:
```json
{
  "council": [
    {
      "id": "microsoft/phi-4-mini-reasoning",
      "name": "Phi-4 Mini Reasoning",
      "description": "Microsoft's reasoning-optimized model"
    },
    {
      "id": "apollo-v0.1-4b-thinking-qx86x-hi-mlx",
      "name": "Apollo 4B Thinking",
      "description": "Apollo's thinking model with MLX optimization"
    },
    {
      "id": "ai21-jamba-reasoning-3b-hi-mlx",
      "name": "AI21 Jamba Reasoning",
      "description": "AI21's Jamba reasoning model"
    }
  ],
  "chairman": {
    "id": "qwen/qwen3-4b-thinking-2507",
    "name": "Qwen3-4B Thinking",
    "description": "Qwen's 4B thinking model for synthesis"
  },
  "metadata": {
    "version": "1.0",
    "updated": "2025-11-26T07:40:33.437Z"
  }
}
```

### Technical Implementation

**Backend Changes** (`backend/`):

1. **New `models.py` module**:
   ```python
   import json
   import os
   from typing import List, Dict, Any
   from pathlib import Path

   def load_models_config() -> Dict[str, Any]:
       """Load model configuration from models.json"""
       
   def get_council_models() -> List[str]:
       """Get list of council model IDs"""
       
   def get_chairman_model() -> str:
       """Get chairman model ID"""
   ```

2. **Update `config.py`**:
   ```python
   from .models import get_council_models, get_chairman_model
   
   # Dynamic model loading
   COUNCIL_MODELS = get_council_models()
   CHAIRMAN_MODEL = get_chairman_model()
   ```

3. **Error Handling**:
   - Graceful fallback to hardcoded models if `models.json` missing/invalid
   - Validation of model configuration structure
   - Clear error messages for configuration issues

**Frontend Changes** (Optional Future Enhancement):
- No immediate changes required
- Future: Model selection UI in admin panel

### Configuration Schema

**JSON Schema for `models.json`**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["council", "chairman"],
  "properties": {
    "council": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"},
          "description": {"type": "string"}
        }
      }
    },
    "chairman": {
      "type": "object",
      "required": ["id", "name"],
      "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"}
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "version": {"type": "string"},
        "updated": {"type": "string"}
      }
    }
  }
}
```

### Validation & Error Handling

**Configuration Validation**:
- JSON syntax validation
- Schema validation against required fields
- Model ID format validation
- Duplicate model ID detection

**Fallback Strategy**:
```python
DEFAULT_COUNCIL_MODELS = [
    "microsoft/phi-4-mini-reasoning",
    "apollo-v0.1-4b-thinking-qx86x-hi-mlx", 
    "ai21-jamba-reasoning-3b-hi-mlx"
]
DEFAULT_CHAIRMAN_MODEL = "qwen/qwen3-4b-thinking-2507"
```

## Impact Assessment

### Breaking Changes
- **Configuration**: Introduces new dependency on `models.json`
- **Deployment**: Requires `models.json` file in production
- **Backward Compatibility**: Maintains fallback to hardcoded values

### Performance Considerations
- **Startup**: Minimal overhead loading JSON at startup
- **Runtime**: No impact once loaded
- **Caching**: Models loaded once at startup

### Risk Mitigation
- **Fallback**: Default to hardcoded models if JSON fails
- **Validation**: Comprehensive error checking
- **Documentation**: Clear configuration examples

## Implementation Plan

### Phase 1: Core Implementation
1. Create `models.py` module with loading functions
2. Create default `models.json` with current configuration
3. Update `config.py` to use dynamic loading
4. Add validation and error handling
5. Test with various configurations

### Phase 2: Enhanced Features
1. Add JSON schema validation
2. Create configuration validation tools
3. Add hot-reloading capability (optional)
4. Enhanced error reporting

### Phase 3: Documentation & Tooling
1. Update README.md with configuration instructions
2. Update project documentation
3. Create model configuration guide
4. Add configuration validation script

## Validation Criteria

- [ ] `models.json` loads successfully at startup
- [ ] Council and chairman models are correctly identified
- [ ] Invalid JSON gracefully falls back to defaults
- [ ] Missing file falls back to defaults
- [ ] All existing functionality preserved
- [ ] Configuration changes work without code restart
- [ ] Clear error messages for invalid configurations

## File Structure Changes

```
llm-council/
├── models.json                 # New: Model configuration
├── backend/
│   ├── config.py              # Modified: Use dynamic loading
│   ├── models.py              # New: Model configuration loader
│   └── ...
├── README.md                  # Modified: Configuration docs
└── openspec/
    └── project.md             # Modified: Architecture update
```

## Configuration Examples

**Minimal Configuration**:
```json
{
  "council": [
    {"id": "microsoft/phi-4-mini-reasoning", "name": "Phi-4"}
  ],
  "chairman": {"id": "qwen/qwen3-4b-thinking-2507", "name": "Qwen3-4B"}
}
```

**Development Configuration**:
```json
{
  "council": [
    {"id": "test-model-1", "name": "Test Model 1"},
    {"id": "test-model-2", "name": "Test Model 2"}
  ],
  "chairman": {"id": "test-chairman", "name": "Test Chairman"},
  "metadata": {
    "version": "dev",
    "environment": "development"
  }
}
```

## Questions for Approval

1. Should hot-reloading be included (restart-free config changes)?
2. Should we include model metadata like expected response times?
3. Should configuration validation be strict (fail fast) or permissive?
4. Should we add environment-specific configurations (dev/prod)?

---

## Implementation Summary

**Completed**: 2025-11-26

### Changes Made:
✅ **Phase 1: Core Implementation**
- ✅ Created `backend/models.py` module with dynamic loading functions
- ✅ Created `models.json` configuration file with current model setup
- ✅ Updated `backend/config.py` to use dynamic loading
- ✅ Added comprehensive validation and error handling
- ✅ Implemented fallback to hardcoded defaults

✅ **Phase 2: Enhanced Features** 
- ✅ Added JSON schema validation with detailed error messages
- ✅ Created `validate_models.py` configuration validation tool
- ✅ Enhanced error reporting for invalid configurations
- ✅ Support for model metadata (name, description)

✅ **Phase 3: Documentation & Tooling**
- ✅ Updated README.md with models.json configuration instructions  
- ✅ Updated project documentation and architecture notes
- ✅ Created comprehensive model configuration guide
- ✅ Added validation script for configuration testing

### New Files Created:
- `models.json` - Dynamic model configuration
- `backend/models.py` - Configuration loading module  
- `validate_models.py` - Configuration validation tool

### Configuration Benefits:
- **Flexibility**: Change models without editing Python code
- **Validation**: Comprehensive error checking and fallback
- **Maintainability**: Clean separation of config from code
- **User-Friendly**: Simple JSON format with validation tools

**Next Steps**: Configuration is ready for production use. Models can be changed by editing `models.json` and restarting the backend.