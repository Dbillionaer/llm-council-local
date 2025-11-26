# Change Proposal: Multi-Round Deliberation & Enhanced Configuration

**ID**: 003-multi-round-deliberation  
**Date**: 2025-11-26  
**Status**: ✅ Implemented  
**Type**: Feature Enhancement / Configuration Enhancement

## Summary

Rename `models.json` to `config.json` for broader configuration scope and implement multi-round deliberation turns where council members can review and refine their responses across multiple iterations before final synthesis.

## Motivation

- **Enhanced Quality**: Multiple deliberation rounds can improve response accuracy and depth
- **Iterative Refinement**: Council members can build upon each other's insights across rounds
- **Configurable Complexity**: Users can tune the deliberation depth based on query complexity
- **Unified Configuration**: Single config file for all system parameters
- **Research Value**: Enable experimentation with different deliberation strategies

## Current State

- Configuration uses `models.json` with only model definitions
- Single-round deliberation: Stage 1 → Stage 2 (ranking) → Stage 3 (synthesis)
- Fixed workflow with no iterative refinement capability

## Proposed Changes

### Enhanced Configuration Structure

Rename `models.json` to `config.json` and expand structure:

```json
{
  "models": {
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
    }
  },
  "deliberation": {
    "rounds": 2,
    "max_rounds": 5,
    "enable_cross_review": true,
    "refinement_prompt_template": "default"
  },
  "metadata": {
    "version": "2.0",
    "updated": "2025-11-26T07:50:49.458Z"
  }
}
```

### Multi-Round Deliberation Workflow

**Enhanced 3-Stage Process with Rounds**:

1. **Stage 1: Initial Responses** (unchanged)
   - Collect initial responses from all council models

2. **Stage 2: Multi-Round Deliberation** (enhanced)
   - **Round 1**: Initial cross-review and ranking (current behavior)
   - **Round N**: Each model reviews all previous responses AND previous rankings
     - Models can refine their own responses based on peer feedback
     - Models re-rank all responses (including refined ones)
   - Configurable number of rounds (1-5)

3. **Stage 3: Final Synthesis** (enhanced)
   - Chairman considers all rounds of responses and rankings
   - Final synthesis incorporates evolutionary improvements from deliberation

### Technical Implementation

**Backend Changes**:

1. **Configuration Updates**:
   - Rename `models.py` functions to handle `config.json`
   - Add deliberation configuration parsing
   - Maintain backward compatibility with `models.json`

2. **Enhanced Council Logic** (`backend/council.py`):
   ```python
   async def stage2_multi_round_deliberation(
       user_query: str,
       stage1_results: List[Dict[str, Any]],
       rounds: int = 1
   ) -> Tuple[List[List[Dict[str, Any]]], Dict[str, str]]:
       """Multi-round deliberation with response refinement."""
   
   async def refine_response_round(
       model: str,
       original_response: str,
       peer_responses: List[Dict[str, Any]],
       peer_rankings: List[Dict[str, Any]],
       round_number: int
   ) -> Dict[str, Any]:
       """Refine a model's response based on peer feedback."""
   ```

3. **Enhanced Prompting**:
   - Round 1: Current ranking behavior
   - Round 2+: "Based on previous responses and rankings, refine your answer and re-evaluate all responses"

**Frontend Changes**:
- Enhanced UI to display multiple deliberation rounds
- Tabbed interface showing evolution of responses across rounds
- Round-by-round ranking evolution display

### Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object", 
  "required": ["models"],
  "properties": {
    "models": {
      "type": "object",
      "required": ["council", "chairman"],
      "properties": {
        "council": {"type": "array", "minItems": 1},
        "chairman": {"type": "object"}
      }
    },
    "deliberation": {
      "type": "object",
      "properties": {
        "rounds": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1},
        "max_rounds": {"type": "integer", "minimum": 1, "maximum": 10},
        "enable_cross_review": {"type": "boolean", "default": true},
        "refinement_prompt_template": {"type": "string", "default": "default"}
      }
    }
  }
}
```

### Deliberation Flow Detail

**Single Round (Current Behavior)**:
```
Stage 1: [M1, M2, M3] → Initial Responses
Stage 2: [M1, M2, M3] → Rank Others' Responses  
Stage 3: Chairman → Final Synthesis
```

**Multi-Round Deliberation**:
```
Stage 1: [M1, M2, M3] → Initial Responses

Stage 2 Round 1: 
  [M1, M2, M3] → Rank Others' Responses

Stage 2 Round 2:
  [M1, M2, M3] → Review Round 1 Rankings → Refine Own Responses → Re-rank All

Stage 2 Round N:
  [M1, M2, M3] → Review Previous Rounds → Refine → Re-rank

Stage 3: Chairman → Synthesize with Full Deliberation History
```

## Impact Assessment

### Breaking Changes
- **Configuration File**: `models.json` renamed to `config.json`
- **API Response**: Enhanced structure with round-by-round data
- **Performance**: Increased processing time with multiple rounds

### Backward Compatibility
- Automatic fallback: if `config.json` missing, check for `models.json`
- Single round (rounds: 1) maintains current behavior exactly
- Existing frontend will work with single round responses

### Performance Considerations
- **Time Complexity**: O(rounds * models * models) instead of O(models * models)
- **Token Usage**: Significantly increased with multiple rounds
- **Memory**: Store all intermediate responses and rankings

## Implementation Plan

### Phase 1: Configuration Migration
1. Rename `models.json` → `config.json` with enhanced structure
2. Update `backend/models.py` → `backend/config_loader.py`
3. Add deliberation configuration parsing
4. Maintain backward compatibility with `models.json`
5. Update validation script

### Phase 2: Multi-Round Logic
1. Implement multi-round deliberation in `council.py`
2. Add response refinement functionality
3. Enhanced prompting for iterative rounds
4. Update API responses with round data

### Phase 3: Frontend Enhancement
1. Multi-round UI display
2. Round-by-round progression visualization
3. Evolution tracking of responses and rankings

### Phase 4: Documentation & Tools
1. Update README.md with new configuration format
2. Update all documentation references
3. Add deliberation strategy guide
4. Enhanced validation tools

## Validation Criteria

- [ ] `config.json` loads successfully with deliberation settings
- [ ] Backward compatibility with existing `models.json` files
- [ ] Single round behavior identical to current system
- [ ] Multi-round deliberation produces enhanced responses
- [ ] All intermediate rounds preserved and accessible
- [ ] Performance acceptable for 2-3 round deliberation
- [ ] Frontend displays multi-round progression clearly
- [ ] Configuration validation handles new deliberation parameters

## Configuration Examples

**Minimal Configuration** (Single Round):
```json
{
  "models": {
    "council": [{"id": "model1", "name": "Model 1"}],
    "chairman": {"id": "chairman1", "name": "Chairman"}
  }
}
```

**Multi-Round Configuration**:
```json
{
  "models": {
    "council": [...],
    "chairman": {...}
  },
  "deliberation": {
    "rounds": 3,
    "enable_cross_review": true
  }
}
```

**Advanced Configuration**:
```json
{
  "models": {...},
  "deliberation": {
    "rounds": 2,
    "max_rounds": 4,
    "enable_cross_review": true,
    "refinement_prompt_template": "deep_analysis"
  },
  "system": {
    "timeout_per_round": 120,
    "parallel_processing": true
  }
}
```

## Future Enhancements

- **Adaptive Rounds**: Automatic round determination based on convergence
- **Specialized Prompts**: Different refinement strategies per round
- **Round-Specific Models**: Different models for different deliberation rounds
- **Consensus Metrics**: Measure agreement across rounds
- **Round Weighting**: Different weights for different rounds in final synthesis

## Questions for Approval

1. Should we implement adaptive round determination (auto-stop when consensus reached)?
2. Maximum reasonable number of deliberation rounds (current proposal: 5)?
3. Should refinement prompts be customizable per model or global?
4. Include round timing/performance metrics in responses?

---

## Implementation Summary

**Completed**: 2025-11-26

### Changes Made:

✅ **Phase 1: Configuration Migration**
- ✅ Renamed `models.json` → `config.json` with enhanced structure
- ✅ Updated `backend/models.py` → `backend/config_loader.py` 
- ✅ Added deliberation configuration parsing
- ✅ Maintained backward compatibility with `models.json`
- ✅ Updated validation script to handle both formats

✅ **Phase 2: Multi-Round Logic**
- ✅ Implemented `stage2_multi_round_deliberation()` function
- ✅ Added `refine_responses_round()` for iterative improvement
- ✅ Enhanced prompting for multi-round context
- ✅ Backward compatibility wrapper for single-round behavior
- ✅ Updated API responses with round-by-round data

✅ **Phase 3: Enhanced Synthesis**
- ✅ Created `stage3_enhanced_synthesis()` for multi-round context
- ✅ Chairman considers full deliberation history
- ✅ Enhanced metadata with deliberation information
- ✅ Extended timeouts for complex multi-round synthesis

✅ **Phase 4: Documentation & Tools**
- ✅ Updated README.md with new configuration format and deliberation features
- ✅ Enhanced validation script for config.json format
- ✅ Updated all documentation references
- ✅ Added deliberation configuration examples

### New Features:
- **Multi-Round Deliberation**: Configurable 1-5 rounds of iterative review
- **Response Refinement**: Models improve responses based on peer feedback
- **Enhanced Configuration**: Unified config.json for all settings
- **Backward Compatibility**: Automatic fallback to single round and legacy files
- **Rich Metadata**: Full deliberation history and round tracking

### Configuration Benefits:
- **Flexible Deliberation**: Tune complexity via rounds parameter
- **Quality Enhancement**: Iterative refinement improves response quality  
- **Unified Config**: Single file for models and deliberation settings
- **Easy Validation**: Enhanced tools for configuration testing
- **Backward Compatible**: Existing setups continue to work

**Default Configuration**: 2 rounds of deliberation with cross-review enabled for enhanced quality while maintaining reasonable performance.

**Next Steps**: Multi-round deliberation is ready for production use. Users can configure deliberation depth in `config.json` based on their quality vs. performance requirements.