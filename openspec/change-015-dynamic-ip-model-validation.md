# Change Proposal 015: Dynamic IP Address Configuration and Model Validation

## Summary
Add dynamic IP address configuration and comprehensive model validation to ensure proper connectivity to local LLM servers and validate configured models against available models.

## Problem Statement
Currently, the application uses a hardcoded IP address for the local LLM server. This creates deployment challenges when the server IP changes or when deploying on different networks. Additionally, there's no validation to ensure the configured models are actually available on the LLM server.

## Proposed Solution
1. **Dynamic IP Configuration**
   - Add `server_ip` parameter to config.json (empty string by default)
   - Auto-detect local IPv4 address when server_ip is not specified
   - Construct OpenAI base URL using the configured or detected IP

2. **Model Validation**
   - Connect to LLM server on startup
   - Retrieve available models via API
   - Compare with configured models in config.json
   - Exit with detailed error if validation fails

3. **Error Handling**
   - Fallback to 127.0.0.1 if connection fails
   - Detailed error messages for troubleshooting
   - Graceful exit with clear instructions

## Technical Details

### Configuration Changes
```json
{
  "server_ip": "",
  "server_port": "11434",
  "openai_base_url": "http://{ip}:{port}/v1"
}
```

### Implementation Flow
1. Load config.json
2. If server_ip is empty, auto-detect local IP
3. Construct base URL using IP and port
4. Test connection to LLM server
5. Retrieve and validate available models
6. Exit with error if < 3 models or configured models not found
7. Continue startup if validation passes

### API Endpoints
- `GET /v1/models` - Retrieve available models
- Model list format validation

## Files to Modify
- `config.json` - Add server configuration parameters
- `backend/config.py` - Load and validate server config
- `backend/main.py` - Add startup validation
- `backend/council.py` - Use dynamic base URL
- New: `backend/model_validator.py` - Model validation logic
- `README.md` - Document new configuration options

## Testing Plan
1. Test with empty server_ip (auto-detection)
2. Test with specified server_ip
3. Test connection failure scenarios
4. Test model validation with correct/incorrect models
5. Test error message clarity

## Rollback Plan
If issues occur, revert to hardcoded IP configuration by restoring previous config.json and removing validation logic.

## Timeline
- Implementation: 2-3 hours
- Testing: 1 hour
- Documentation: 30 minutes

## Dependencies
- Local LLM server must support OpenAI-compatible `/v1/models` endpoint
- Python `socket` library for IP detection
- Enhanced error handling and logging