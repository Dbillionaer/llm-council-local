#!/usr/bin/env python3
"""
Graphiti MCP Server Integration Tests

Tests the knowledge graph memory capabilities:
1. Adding memories (episodes)
2. Searching/retrieving memories
3. Inference from related facts

NOTE: Graphiti requires:
- FalkorDB/Neo4j database running
- LLM API key (OpenAI, etc.) for entity extraction
- Episode processor must be running to process queued episodes
"""

import asyncio
import json
import sys
from typing import Dict, Any, List


async def run_graphiti_test():
    """Run the Graphiti memory test sequence."""
    from backend.mcp.registry import get_mcp_registry
    
    print("=" * 60)
    print("GRAPHITI KNOWLEDGE GRAPH TEST")
    print("=" * 60)
    
    # Initialize MCP registry
    print("\n[1/5] Initializing MCP servers...")
    registry = get_mcp_registry()
    status = await registry.initialize()
    
    if 'graphiti' not in status.get('servers', []):
        print("❌ FAILED: Graphiti server not available")
        print("   Make sure Graphiti is running at http://localhost:8000")
        await registry.shutdown()
        return False
    
    print("✅ Graphiti server connected")
    print(f"   Tools: {[t.split('.')[-1] for t in status.get('tools', []) if 'graphiti' in t]}")
    
    # Check server status
    print("\n[2/5] Checking Graphiti server status...")
    try:
        status_result = await registry.call_tool('graphiti.get_status', {})
        print(f"   Status: {_extract_message(status_result)}")
    except Exception as e:
        print(f"   ❌ Status check failed: {e}")
    
    # Test group ID
    test_group = "main"
    print(f"\n[3/5] Using group '{test_group}'...")
    
    # Add memories
    print("\n[4/5] Adding memories...")
    memories = [
        "Jane likes her New Balance shoes",
        "Jane likes her Nike shoes",
        "Jane has Nike clothes",
        "Jane likes Adidas shoes",
        "Jane thinks Adidas shoes are ok but she likes the brand of shoes better that she has clothes from"
    ]
    
    for i, memory in enumerate(memories, 1):
        try:
            result = await registry.call_tool('graphiti.add_memory', {
                'name': f'jane_preference_{i}',
                'episode_body': memory,
                'group_id': test_group,
                'source': 'text',
                'source_description': 'User preference observation'
            })
            msg = _extract_message(result)
            status_icon = "⏳" if "queued" in msg.lower() else "✅"
            print(f"   {status_icon} [{i}/5] \"{memory[:45]}...\"")
        except Exception as e:
            print(f"   ❌ [{i}/5] Failed: {e}")
    
    # Wait for processing
    print("\n   Waiting for graph processing (20s)...")
    print("   NOTE: If episodes remain 'queued', check Graphiti LLM configuration")
    await asyncio.sleep(20)
    
    # Check stored episodes
    print("\n[5/5] Querying knowledge graph...")
    
    print("\n   a) Checking stored episodes...")
    try:
        episodes_result = await registry.call_tool('graphiti.get_episodes', {
            'group_ids': [test_group],
            'max_episodes': 10
        })
        episodes = _extract_episodes(episodes_result)
        if episodes:
            print(f"   ✅ Found {len(episodes)} episodes:")
            for ep in episodes[:3]:
                print(f"      - {ep}")
        else:
            print("   ⚠️  No episodes found (still processing or LLM not configured)")
    except Exception as e:
        print(f"   ❌ Get episodes failed: {e}")
    
    # Search nodes
    print("\n   b) Searching nodes for 'Jane shoe preferences'...")
    try:
        nodes_result = await registry.call_tool('graphiti.search_nodes', {
            'query': 'Jane shoe preferences brands Nike Adidas',
            'group_ids': [test_group],
            'max_nodes': 10
        })
        nodes = _extract_nodes(nodes_result)
        if nodes:
            print(f"   ✅ Found {len(nodes)} nodes:")
            for node in nodes[:5]:
                print(f"      - {node.get('name', 'unknown')}: {node.get('summary', '')[:50]}...")
        else:
            print("   ⚠️  No nodes found")
    except Exception as e:
        print(f"   ❌ Node search failed: {e}")
    
    # Search facts
    print("\n   c) Searching facts: 'Which shoe brand does Jane like best?'...")
    try:
        facts_result = await registry.call_tool('graphiti.search_memory_facts', {
            'query': 'Which shoe brand does Jane like best?',
            'group_ids': [test_group],
            'max_facts': 10
        })
        facts = _extract_facts(facts_result)
        if facts:
            print(f"   ✅ Found {len(facts)} facts:")
            for fact in facts[:5]:
                print(f"      - {fact}")
        else:
            print("   ⚠️  No facts found")
    except Exception as e:
        print(f"   ❌ Fact search failed: {e}")
    
    # Analysis
    print("\n" + "=" * 60)
    print("EXPECTED INFERENCE")
    print("=" * 60)
    print("""
If Graphiti is properly configured, it should infer:

Input memories:
  1. Jane likes her New Balance shoes
  2. Jane likes her Nike shoes  
  3. Jane has Nike clothes
  4. Jane likes Adidas shoes
  5. Jane prefers shoes from the brand she has clothes from

Expected graph connections:
  - Jane → likes → [New Balance, Nike, Adidas] shoes
  - Jane → has → Nike clothes
  - Jane → prefers → brand with clothes (Nike)

Query: "Which shoe brand does Jane like best?"
Expected answer: Nike (she has Nike clothes AND prefers that brand)
""")
    
    await registry.shutdown()
    print("✅ Test complete")
    return True


def _extract_message(result: Dict[str, Any]) -> str:
    """Extract message from tool result."""
    if not result.get('success'):
        return f"Error: {result.get('error', 'unknown')}"
    
    output = result.get('output', {})
    content = output.get('content', [])
    
    if content and isinstance(content, list):
        for item in content:
            if item.get('type') == 'text':
                try:
                    data = json.loads(item.get('text', '{}'))
                    if 'message' in data:
                        return data['message']
                    if 'result' in data and isinstance(data['result'], dict):
                        return data['result'].get('message', str(data['result']))
                    if 'status' in data:
                        return f"{data.get('status')}: {data.get('message', '')}"
                    return str(data)[:100]
                except:
                    return item.get('text', '')[:100]
    
    return str(output)[:100]


def _extract_episodes(result: Dict[str, Any]) -> List[str]:
    """Extract episodes from result."""
    if not result.get('success'):
        return []
    
    output = result.get('output', {})
    content = output.get('content', [])
    
    if content and isinstance(content, list):
        for item in content:
            if item.get('type') == 'text':
                try:
                    data = json.loads(item.get('text', '{}'))
                    episodes = data.get('result', data).get('episodes', [])
                    return [f"{e.get('name', 'unknown')}: {e.get('content', '')[:50]}..." for e in episodes]
                except:
                    pass
    return []


def _extract_nodes(result: Dict[str, Any]) -> List[Dict]:
    """Extract nodes from search result."""
    if not result.get('success'):
        return []
    
    output = result.get('output', {})
    content = output.get('content', [])
    
    if content and isinstance(content, list):
        for item in content:
            if item.get('type') == 'text':
                try:
                    data = json.loads(item.get('text', '{}'))
                    if 'result' in data:
                        return data['result'].get('nodes', [])
                    return data.get('nodes', [])
                except:
                    pass
    return []


def _extract_facts(result: Dict[str, Any]) -> List[str]:
    """Extract facts from search result."""
    if not result.get('success'):
        return []
    
    output = result.get('output', {})
    content = output.get('content', [])
    
    if content and isinstance(content, list):
        for item in content:
            if item.get('type') == 'text':
                try:
                    data = json.loads(item.get('text', '{}'))
                    facts_data = data.get('result', data).get('facts', [])
                    formatted = []
                    for f in facts_data:
                        if isinstance(f, dict):
                            fact_str = f.get('fact', f.get('name', str(f)))
                            formatted.append(fact_str[:100])
                        else:
                            formatted.append(str(f)[:100])
                    return formatted
                except:
                    pass
    return []


if __name__ == "__main__":
    success = asyncio.run(run_graphiti_test())
    sys.exit(0 if success else 1)
