# Change: Fix Message Re-run Cleanup

## Why
When re-running a user message, the old assistant responses from previous runs are not removed, causing duplicate/stale messages to appear when selecting that conversation.

## What Changes
- Clear all messages below the user message being re-run before appending new response
- Ensure conversation state is clean before new deliberation starts

## Impact
- Affected specs: conversation-ui
- Affected code: `frontend/src/App.jsx`, conversation message handling
