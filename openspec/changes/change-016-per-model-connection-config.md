# Change Proposal 016: Per-Model Connection Configuration

## Summary
Allow specifying separate connection parameters (IP address, OpenAI API base URL, port, and API key) for each model in config.json, with fallback to main configuration values for efficient per-model inference granularity.

## Motivation
- Different models may be hosted on different servers or ports
- Some models may require different API endpoints or authentication
- Enables flexible deployment scenarios (some models on local LM Studio, others on remote Ollama instances)
- Maintains backwards compatibility while adding granular control

## Detailed Design

### Configuration Structure
Extend config.json to include per-model connection parameters:

```json
{
  "api_base_url": "http://192.168.1.111:11434",
  "ip_address": "192.168.1.111", 
  "port": "11434",
  "api_key": "",
  "models": {
    "chairman": {
      "model_id": "qwen/qwen3-4b-thinking-2507",
      "ip_address": "",
      "api_base_url": "",
      "port": "",
      "api_key": ""
    },
    "council_members": [
      {
        "model_id": "microsoft/phi-4-mini-reasoning",
        "ip_address": "",
        "api_base_url": "", 
        "port": "",
        "api_key": ""
      }
    ]
  }
}
```

### Parameter Resolution Logic
1. Check per-model parameter value
2. If empty, fallback to main configuration value
3. If main value empty, use system default

### Implementation Requirements
- Update config loading to parse per-model connection parameters
- Modify LLM client initialization to use resolved parameters
- Maintain backwards compatibility with existing config format
- Add validation for connection parameter combinations

## Testing Strategy
- Test with mixed configuration (some models with custom params, others using defaults)
- Verify backwards compatibility with existing configs
- Test connection validation with different parameter combinations
- Validate parameter resolution logic

## Migration Plan
- Existing configs continue to work unchanged
- New per-model parameters are optional (empty by default)
- Gradual migration path for users wanting granular control

## Impact Assessment
- **Frontend**: No changes required
- **Backend**: Update config loading and LLM client initialization
- **Configuration**: Extended schema with backwards compatibility
- **Performance**: Minimal impact, configuration loaded once at startup