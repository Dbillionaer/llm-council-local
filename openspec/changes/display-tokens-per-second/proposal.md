# Display Tokens Per Second

## Status
- **State**: implemented
- **Priority**: 2 (Feature)
- **Created**: 2025-01-27
- **Implemented**: v0.4.0

## Summary
Calculate and display real-time average tokens/second next to each council member's, chairman's, and formatter's name during streaming.

## Problem
Users have no visibility into model performance during streaming. There's no way to see how fast each model is generating tokens.

## Solution
Track token generation timing per model and display running average tokens/s next to each model name in the UI.

### Backend Changes

**`backend/council.py`**:
- Track start time when first token received for each model
- Track total tokens generated per model
- Calculate and emit tokens/s with each streaming event
- Add `tokens_per_second` field to completion events

### Frontend Changes

**`frontend/src/components/Stage1.jsx`**:
- Display tokens/s next to model name in tab header
- Update in real-time as tokens stream
- Format: "Model Name (123.4 tok/s)"

**`frontend/src/components/Stage2.jsx`**:
- Same display for ranking phase

**`frontend/src/components/Stage3.jsx`**:
- Display tokens/s for chairman/formatter

## Implementation Details

### Token Counting
```python
# In streaming loop
if chunk["type"] == "token":
    if model not in start_times:
        start_times[model] = time.time()
    token_counts[model] = token_counts.get(model, 0) + len(chunk["delta"].split())
    
    elapsed = time.time() - start_times[model]
    tps = token_counts[model] / elapsed if elapsed > 0 else 0
    
    on_event("stage1_token", {
        "model": model,
        "delta": chunk["delta"],
        "content": content,
        "tokens_per_second": round(tps, 1)
    })
```

### UI Display
```jsx
<div className="model-tab">
  {modelName}
  {tokensPerSecond && (
    <span className="tps-indicator">({tokensPerSecond} tok/s)</span>
  )}
</div>
```

## Files to Modify
- `backend/council.py` - Add timing and calculation
- `frontend/src/components/Stage1.jsx` - Display in tabs
- `frontend/src/components/Stage2.jsx` - Display in tabs
- `frontend/src/components/Stage3.jsx` - Display for chairman

## Acceptance Criteria
- [ ] Tokens/s calculated accurately per model
- [ ] Display updates in real-time during streaming
- [ ] Final tokens/s shown after completion
- [ ] Works for all three stages
