#!/usr/bin/env python3
"""
Script to remove all Hermes-related nodes and edges from the Graphiti knowledge graph.
This cleans up incorrect AI name associations.
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp.registry import get_mcp_registry, initialize_mcp


async def remove_hermes_nodes():
    """Remove all nodes and edges related to 'hermes' from the graph."""
    
    print("Initializing MCP servers...")
    await initialize_mcp()
    
    registry = get_mcp_registry()
    
    if "graphiti" not in registry.clients:
        print("ERROR: Graphiti server not available")
        return False
    
    # Search all groups for Hermes-related content
    search_groups = [
        "llm_council",
        "llm_council_autobiographical",
        "llm_council_semantic",
        "llm_council_episodic"
    ]
    
    hermes_uuids = set()
    
    # Search for nodes containing Hermes
    print("\nSearching for Hermes-related nodes...")
    for group_id in search_groups:
        try:
            result = await registry.call_tool("graphiti.search_nodes", {
                "query": "hermes",
                "group_ids": [group_id],
                "max_nodes": 100
            })
            
            if result.get("success"):
                output = result.get("output", {})
                content = output.get("content", [])
                if content and isinstance(content, list) and len(content) > 0:
                    try:
                        parsed = json.loads(content[0].get("text", "{}"))
                        nodes = parsed.get("nodes", []) if isinstance(parsed, dict) else parsed
                        
                        for node in nodes:
                            if isinstance(node, dict):
                                name = str(node.get("name", "")).lower()
                                summary = str(node.get("summary", "")).lower()
                                uuid = node.get("uuid", "")
                                
                                # STRICT CHECK: Only delete if "hermes" is specifically in name or summary
                                if uuid and ("hermes" in name or "hermes" in summary):
                                    hermes_uuids.add(uuid)
                                    print(f"  Found node: {node.get('name', 'unnamed')} (uuid: {uuid[:8]}...)")
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"  Error searching {group_id}: {e}")
    
    # Search for facts containing Hermes
    print("\nSearching for Hermes-related facts...")
    for group_id in search_groups:
        try:
            result = await registry.call_tool("graphiti.search_memory_facts", {
                "query": "hermes",
                "group_ids": [group_id],
                "max_facts": 100
            })
            
            if result.get("success"):
                output = result.get("output", {})
                content = output.get("content", [])
                if content and isinstance(content, list) and len(content) > 0:
                    try:
                        parsed = json.loads(content[0].get("text", "{}"))
                        facts = parsed.get("facts", []) if isinstance(parsed, dict) else parsed
                        
                        for fact in facts:
                            if isinstance(fact, dict):
                                fact_text = str(fact.get("fact", "")).lower()
                                uuid = fact.get("uuid", "")
                                
                                # STRICT CHECK: Only delete if "hermes" is in fact text
                                if uuid and "hermes" in fact_text:
                                    hermes_uuids.add(uuid)
                                    print(f"  Found fact: {fact.get('fact', 'no text')[:50]}... (uuid: {uuid[:8]}...)")
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"  Error searching facts in {group_id}: {e}")
    
    if not hermes_uuids:
        print("\nNo Hermes-related nodes or edges found.")
        return True
    
    print(f"\nFound {len(hermes_uuids)} Hermes-related entries to delete.")
    
    # Delete each found entity
    deleted_count = 0
    failed_count = 0
    
    for uuid in hermes_uuids:
        try:
            result = await registry.call_tool("graphiti.delete_entity_edge", {
                "uuid": uuid
            })
            
            if result.get("success"):
                deleted_count += 1
                print(f"  Deleted: {uuid[:8]}...")
            else:
                failed_count += 1
                print(f"  Failed to delete {uuid[:8]}: {result.get('error', 'unknown error')}")
        except Exception as e:
            failed_count += 1
            print(f"  Error deleting {uuid[:8]}: {e}")
    
    print(f"\nSummary: Deleted {deleted_count}, Failed {failed_count}")
    return deleted_count > 0 or failed_count == 0


if __name__ == "__main__":
    success = asyncio.run(remove_hermes_nodes())
    sys.exit(0 if success else 1)
