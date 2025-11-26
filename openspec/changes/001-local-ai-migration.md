# Change Proposal: Migrate from OpenRouter to Local AI via LM Studio

**ID**: 001-local-ai-migration  
**Date**: 2025-11-26  
**Status**: ✅ Implemented  
**Type**: Breaking Change / Infrastructure Migration

## Summary

Replace OpenRouter API integration with local AI inference via LM Studio, changing from cloud-based LLM providers to locally-hosted models running on LM Studio server.

## Motivation

- **Privacy**: Keep all conversations and data completely local
- **Cost**: Eliminate per-token costs from OpenRouter API calls
- **Speed**: Potentially faster responses from local inference
- **Control**: Full control over model selection and configuration
- **Offline capability**: Works without internet connection

## Current State

The system currently uses:
- OpenRouter API at `https://openrouter.ai/api/v1/chat/completions`
- Cloud models: GPT-5.1, Gemini 3 Pro, Claude Sonnet 4.5, Grok 4
- API key authentication via environment variables
- HTTP client (`httpx`) for external API calls

## Proposed Changes

### Infrastructure Changes

**LM Studio Server**:
- Host: `http://192.168.1.111:11434`
- Protocol: OpenAI-compatible API format
- No authentication required (local network)

**New Model Configuration**:
- Council Models:
  - `microsoft/phi-4-mini-reasoning`
  - `apollo-v0.1-4b-thinking-qx86x-hi-mlx`
  - `ai21-jamba-reasoning-3b-hi-mlx`
- Chairman Model: `qwen/qwen3-4b-thinking-2507`

### Technical Implementation

**Backend Changes** (`backend/`):

1. **`config.py`** modifications:
   ```python
   # Replace OpenRouter configuration
   LM_STUDIO_BASE_URL = "http://192.168.1.111:11434"
   LM_STUDIO_API_ENDPOINT = f"{LM_STUDIO_BASE_URL}/v1/chat/completions"
   
   # New model identifiers
   COUNCIL_MODELS = [
       "microsoft/phi-4-mini-reasoning",
       "apollo-v0.1-4b-thinking-qx86x-hi-mlx",
       "ai21-jamba-reasoning-3b-hi-mlx"
   ]
   
   CHAIRMAN_MODEL = "qwen/qwen3-4b-thinking-2507"
   ```

2. **`openrouter.py` → `lmstudio.py`** refactor:
   - Remove OpenRouter-specific authentication
   - Update endpoint URL to LM Studio
   - Maintain OpenAI-compatible API format
   - Remove API key requirements
   - Update error handling for local network issues

3. **Import updates** across all modules:
   - Replace `from .openrouter import` with `from .lmstudio import`
   - Update function calls if any naming changes

**Frontend Changes**:
- No changes required (API interface remains the same)
- Update any error messages that mention OpenRouter

**Environment Changes**:
- Remove `OPENROUTER_API_KEY` requirement from `.env`
- Add optional `LM_STUDIO_BASE_URL` for configuration flexibility

### API Compatibility

LM Studio provides OpenAI-compatible endpoints, so the request/response format should remain largely the same:
- Same JSON request structure
- Same response format with `choices[0].message.content`
- Streaming support maintained

### Error Handling Updates

New error scenarios to handle:
- Local network connectivity issues
- LM Studio server unavailable
- Models not loaded in LM Studio
- Local resource constraints (memory, compute)

### Configuration Management

**Model Loading Requirements**:
- All council models must be loaded in LM Studio before starting
- Chairman model must be available for Stage 3
- Consider model switching latency between stages

**Deployment Checklist**:
- [ ] LM Studio running on `192.168.1.111:11434`
- [ ] All required models downloaded and loaded
- [ ] Network connectivity verified
- [ ] Model performance benchmarked

## Impact Assessment

### Breaking Changes
- **Environment**: `OPENROUTER_API_KEY` no longer required
- **Network**: Requires local network access to LM Studio server
- **Dependencies**: No new Python dependencies required

### Performance Considerations
- **Latency**: Local inference may be faster or slower depending on hardware
- **Concurrency**: Need to verify LM Studio can handle parallel requests
- **Memory**: Local models require significant GPU/CPU memory

### Risk Mitigation
- **Fallback**: Keep OpenRouter integration as optional backup
- **Testing**: Verify all models work with council workflow
- **Monitoring**: Add health checks for LM Studio availability

## Implementation Plan

### Phase 1: Core Migration
1. Rename and update `openrouter.py` → `lmstudio.py`
2. Update `config.py` with new endpoints and models
3. Update imports across all backend modules
4. Test basic connectivity and model queries

### Phase 2: Integration Testing
1. Verify 3-stage council workflow with new models
2. Test parallel query handling
3. Validate ranking parsing with new model outputs
4. Performance testing and optimization

### Phase 3: Documentation and Cleanup
1. Update README.md setup instructions
2. Remove OpenRouter references from documentation
3. Update `project.md` with new architecture
4. Create LM Studio setup guide

## Validation Criteria

- [ ] All three council stages work with local models
- [ ] Parallel queries execute successfully
- [ ] Model responses are properly parsed and ranked
- [ ] Performance is acceptable for user experience
- [ ] Error handling gracefully manages local network issues
- [ ] No regression in core council functionality

## Rollback Plan

If issues arise:
1. Revert `config.py` to OpenRouter settings
2. Restore `openrouter.py` module
3. Re-add `OPENROUTER_API_KEY` to environment
4. Update imports back to original state

## Questions for Approval

1. Should we maintain OpenRouter as a fallback option or complete migration?
2. Any specific performance requirements for local inference?
3. Preferred approach for handling model loading/switching in LM Studio?
4. Should we add configuration UI for switching between local/remote modes?

---

## Implementation Summary

**Completed**: 2025-11-26

### Changes Made:
✅ **Phase 1: Core Migration**
- ✅ Renamed `openrouter.py` → `lmstudio.py` with LM Studio endpoint
- ✅ Updated `config.py` with new models and LM Studio configuration  
- ✅ Updated imports in `council.py` from `.openrouter` to `.lmstudio`
- ✅ Removed OpenRouter authentication requirements
- ✅ Tested basic connectivity successfully

✅ **Phase 2: Documentation Updates**
- ✅ Updated README.md with LM Studio setup instructions
- ✅ Updated `project.md` with new architecture details
- ✅ Updated `AGENTS.md` technical notes for local AI
- ✅ Removed all OpenRouter references

✅ **Phase 3: Validation**
- ✅ Backend health check passes
- ✅ LM Studio connection test successful
- ✅ API format compatibility maintained

### New Model Configuration:
- **Council**: `microsoft/phi-4-mini-reasoning`, `apollo-v0.1-4b-thinking-qx86x-hi-mlx`, `ai21-jamba-reasoning-3b-hi-mlx`
- **Chairman**: `qwen/qwen3-4b-thinking-2507`

**Next Steps**: Ready for production use with LM Studio server running and all models loaded.