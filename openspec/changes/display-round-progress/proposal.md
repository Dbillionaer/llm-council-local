# Display Round Progress

## Status
- **State**: implemented
- **Priority**: 2 (Feature)
- **Created**: 2025-01-27
- **Implemented**: v0.4.0

## Summary
Display current round number and max rounds in the active UI frame during multi-round deliberation.

## Problem
Users cannot see which deliberation round is currently running or how many rounds are configured.

## Solution
Display "Round X / Y" indicator in the Stage 2 section during multi-round deliberation.

### Backend Changes

**`backend/council.py`**:
- Emit round info with stage2 events:
  - `round_start`: `{round: 1, max_rounds: 3}`
  - `round_complete`: `{round: 1, max_rounds: 3, triggered_next: true}`

### Frontend Changes

**`frontend/src/components/Stage2.jsx`**:
- Display round indicator when multi-round active
- Format: "Round 1 / 3" or "Round 2 / 3 (Refinement)"
- Style as subtle badge/pill in section header

**`frontend/src/components/Stage2.css`**:
```css
.round-indicator {
  background: #e3f2fd;
  color: #1565c0;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.85em;
  margin-left: 8px;
}
```

### UI Layout
```
┌─────────────────────────────────────────┐
│ Stage 2: Peer Rankings    Round 1 / 3   │
├─────────────────────────────────────────┤
│ [Model A] [Model B] [Model C]           │
│                                         │
│ Ranking content...                      │
└─────────────────────────────────────────┘
```

## Files to Modify
- `backend/council.py` - Emit round info
- `frontend/src/components/Stage2.jsx` - Display indicator
- `frontend/src/components/Stage2.css` - Styling

## Acceptance Criteria
- [ ] Round indicator shows during Stage 2
- [ ] Updates as rounds progress
- [ ] Hidden for single-round deliberation
- [ ] Shows "Refinement" label for refinement rounds
