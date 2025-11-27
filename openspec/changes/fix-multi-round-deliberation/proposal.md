# Fix Multi-Round Deliberation

## Status
- **State**: implemented
- **Priority**: 1 (Fix)
- **Created**: 2025-01-27
- **Implemented**: v0.4.0

## Summary
Multi-round deliberation is configured but not working with streaming. The streaming endpoint uses single-round functions while multi-round logic exists only in non-streaming code.

## Problem
Config shows `deliberation.rounds: 2` but streaming endpoint always runs single round because:
1. `stage2_collect_rankings_streaming()` is single-round only
2. Multi-round logic in `stage2_multi_round_deliberation()` uses non-streaming functions
3. Streaming endpoint in `main.py` calls single-round function

## Root Cause
Multi-round deliberation was implemented for non-streaming but never ported to streaming functions.

## Solution
Implement quality-based multi-round deliberation in streaming mode:

### New Algorithm
1. **Stage 2 Round 1**: Each model ranks AND rates (1-5) each other response
2. **Quality Check**: If any response rated below 30% (1.5/5), trigger another round
3. **Refinement Round**: Models receive their response + peer feedback + instruction to improve
4. **Stage 2 Round N**: Re-rank refined responses
5. **Repeat**: Until all ratings ≥30% or max_rounds reached

### Backend Changes

**`backend/council.py`**:
- Modify `stage2_collect_rankings_streaming()` to support multi-round
- Add quality rating extraction from rankings
- Add refinement round streaming
- Emit round progress events: `round_start`, `round_complete`

**New ranking prompt format**:
```
For each response, provide:
1. Quality rating (1-5)
2. Brief feedback (1 sentence)

Then provide FINAL RANKING with quality scores:
1. Response A (4/5) - Clear and comprehensive
2. Response B (2/5) - Too brief, missing key details
...
```

### Frontend Changes

**`frontend/src/App.jsx`**:
- Handle `round_start`, `round_complete` events
- Track current round state

## Files to Modify
- `backend/council.py` - Multi-round streaming implementation
- `backend/main.py` - Handle round events
- `frontend/src/App.jsx` - Track round state

## Acceptance Criteria
- [ ] Multi-round triggers when any response rated <30%
- [ ] Models receive feedback in refinement rounds
- [ ] Streaming works for all rounds
- [ ] Respects `max_rounds` config limit
- [ ] Round progress visible in UI
