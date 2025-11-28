# Change 025: Fix MCP Tool Detection for Current Events Queries

## Status
- [x] Proposed
- [x] Approved  
- [x] Implemented
- [ ] Verified

## Problem Statement

When users ask about current events like "what are today's top 5 news", the system fails to use the `websearch` MCP tool. Instead, the model's thinking shows "Hmm, this is tricky because I don't have live news access" and responds with "I cannot provide news for November 27, 2025 (a future date), as my knowledge is current only up to October 2024".

The MCP tool detection (Phase 1) is not correctly identifying that the websearch tool should be used for current events queries.

## Root Cause Analysis

1. The `_phase1_analyze_query` function provides date/time context and tool info, but the analysis prompt doesn't strongly enough emphasize using websearch for current events
2. The tool calling model may not be following the explicit instruction to use websearch for "today's news" queries
3. The classification model might be responding before considering available tools

## Proposed Solution

### 1. Strengthen the Phase 1 analysis prompt

Update `_phase1_analyze_query` in `backend/council.py` to:
- Add explicit examples of when websearch MUST be used
- Include stronger language about current events requiring websearch
- Add a reminder that the model DOES have tools available

### 2. Add explicit keyword detection

Add a pre-check before LLM analysis that detects keywords requiring websearch:
- "news", "current events", "today's", "latest", "recent", "happening now"
- If detected, bias the prompt or short-circuit to use websearch directly

### 3. Improve tool info formatting

Make the websearch tool description more prominent in the detailed tool info.

## Files to Modify

- `backend/council.py`: Update `_phase1_analyze_query` function

## Implementation Details

```python
# Add keyword-based pre-detection
WEBSEARCH_KEYWORDS = ['news', 'current events', 'latest', 'recent', 'happening', 
                      'today\'s', 'this week', 'trending', 'breaking']

def _requires_websearch(query: str) -> bool:
    """Check if query contains keywords that strongly suggest websearch is needed."""
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in WEBSEARCH_KEYWORDS)
```

Update the analysis prompt to be more explicit:

```python
time_context = f"""CRITICAL CONTEXT:
- Today's date is: {current_time.strftime('%Y-%m-%d')} ({current_time.strftime('%A, %B %d, %Y')})
- You HAVE ACCESS to external tools including websearch
- For ANY question about current events, news, or real-time information, you MUST use websearch

IMPORTANT: Do NOT respond that you "lack real-time access" - you have the websearch tool!"""
```

## Testing

1. Test query: "what are today's top 5 news" - should trigger websearch
2. Test query: "what's happening in the world today" - should trigger websearch
3. Test query: "latest news about AI" - should trigger websearch
4. Test query: "what is 2+2" - should NOT trigger websearch (use calculator)
5. Test query: "what is the capital of France" - should NOT trigger websearch (factual)

## Rollback Plan

Revert changes to `backend/council.py` if issues arise.
