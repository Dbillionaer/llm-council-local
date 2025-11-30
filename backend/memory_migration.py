"""
Memory Migration Script

Scans existing conversations for important facts (names, preferences, identity)
and imports them into Graphiti memory groups.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

from backend.mcp.registry import get_mcp_registry


# Patterns to extract important facts
IDENTITY_PATTERNS = [
    # "You shall be known as Aether"
    r"(?:shall be known as|you are now|from now on.*?called|your new name is)\s+([A-Z][a-zA-Z]+)",
    # "Your name is X" or "You are X"
    r"(?:your name is|you are|you're|call you)\s+([A-Z][a-zA-Z]+)",
    # "I am X" or "My name is X"  
    r"(?:my name is|i am|i'm|call me)\s+([A-Z][a-zA-Z]+)",
    # Direct name assignment
    r"known as\s+([A-Z][a-zA-Z]+)",
]

PREFERENCE_PATTERNS = [
    r"(?:i prefer|i like|my favorite|i enjoy)\s+(.+?)(?:\.|$)",
]

FACT_PATTERNS = [
    r"(?:i live in|i'm from|i work at|my job is|i am a)\s+(.+?)(?:\.|$)",
]


class MemoryMigration:
    """Handles migration of conversation data to Graphiti memory."""
    
    GRAPHITI_SERVER_NAME = "graphiti"
    
    def __init__(self, conversations_dir: str = "data/conversations"):
        self.conversations_dir = Path(conversations_dir)
        self.registry = None
        self.stats = {
            "conversations_scanned": 0,
            "facts_found": 0,
            "facts_imported": 0,
            "errors": 0
        }
    
    async def initialize(self) -> bool:
        """Initialize the MCP registry and verify Graphiti is available."""
        self.registry = get_mcp_registry()
        await self.registry.initialize()
        
        # Check if Graphiti is available
        if self.GRAPHITI_SERVER_NAME not in self.registry.clients:
            print("[Migration] ERROR: Graphiti server not available")
            return False
        
        print("[Migration] Graphiti server connected")
        return True
    
    def scan_conversation(self, conv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scan a conversation for important facts.
        
        Returns:
            List of facts with type, content, and timestamp
        """
        facts = []
        
        # Common words to filter out
        filter_words = {"by", "the", "a", "an", "is", "are", "be", "to", "of", "in", "on", "at", "for", "as"}
        
        for message in conv_data.get("messages", []):
            content = message.get("content", "")
            role = message.get("role", "")
            timestamp = conv_data.get("created_at", datetime.utcnow().isoformat())
            
            # Check for identity statements
            for pattern in IDENTITY_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Filter out common words and short matches
                    if match and len(match) > 2 and match.lower() not in filter_words:
                        facts.append({
                            "type": "identity",
                            "content": f"My name is {match}. You shall be known as {match}.",
                            "source": f"{role}:{content[:100]}",
                            "timestamp": timestamp,
                            "original": content
                        })
            
            # Check for preferences
            for pattern in PREFERENCE_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match and len(match) > 5:
                        facts.append({
                            "type": "preference",
                            "content": f"Preference: {match}",
                            "source": f"{role}:{content[:100]}",
                            "timestamp": timestamp,
                            "original": content
                        })
            
            # Check for general facts
            for pattern in FACT_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match and len(match) > 3:
                        facts.append({
                            "type": "fact",
                            "content": f"Fact: {match}",
                            "source": f"{role}:{content[:100]}",
                            "timestamp": timestamp,
                            "original": content
                        })
        
        return facts
    
    async def import_fact(self, fact: Dict[str, Any], group_id: str = "llm_council") -> bool:
        """Import a single fact into Graphiti."""
        try:
            # Parse timestamp
            timestamp = fact.get("timestamp", datetime.utcnow().isoformat())
            if not timestamp.endswith("Z"):
                timestamp = timestamp + "Z"
            
            episode_data = {
                "name": f"migration_{fact['type']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "episode_body": fact["content"],
                "source": "llm_council_migration",
                "source_description": fact.get("source", "migration"),
                "reference_time": timestamp,
                "group_id": group_id
            }
            
            result = await self.registry.call_tool(
                f"{self.GRAPHITI_SERVER_NAME}.add_memory",
                episode_data
            )
            
            if result.get("success"):
                return True
            else:
                print(f"[Migration] Failed to import: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"[Migration] Error importing fact: {e}")
            return False
    
    async def run(self, dry_run: bool = False, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the migration.
        
        Args:
            dry_run: If True, only scan and report without importing
            limit: Maximum number of conversations to scan
            
        Returns:
            Migration statistics
        """
        if not await self.initialize():
            return {"error": "Failed to initialize"}
        
        all_facts: List[Dict[str, Any]] = []
        seen_contents: Set[str] = set()  # Deduplicate
        
        # Scan conversations
        conv_files = list(self.conversations_dir.glob("*.json"))
        if limit:
            conv_files = conv_files[:limit]
        
        print(f"[Migration] Scanning {len(conv_files)} conversations...")
        
        for conv_file in conv_files:
            try:
                with open(conv_file, 'r') as f:
                    conv_data = json.load(f)
                
                facts = self.scan_conversation(conv_data)
                self.stats["conversations_scanned"] += 1
                
                for fact in facts:
                    # Deduplicate by content
                    if fact["content"] not in seen_contents:
                        seen_contents.add(fact["content"])
                        all_facts.append(fact)
                        self.stats["facts_found"] += 1
                        
            except Exception as e:
                print(f"[Migration] Error reading {conv_file}: {e}")
                self.stats["errors"] += 1
        
        print(f"[Migration] Found {len(all_facts)} unique facts")
        
        # Show what we found
        for fact in all_facts[:10]:  # Show first 10
            print(f"  [{fact['type']}] {fact['content']}")
        
        if len(all_facts) > 10:
            print(f"  ... and {len(all_facts) - 10} more")
        
        # Import if not dry run
        if not dry_run and all_facts:
            print(f"\n[Migration] Importing {len(all_facts)} facts to Graphiti...")
            
            for fact in all_facts:
                if await self.import_fact(fact):
                    self.stats["facts_imported"] += 1
                else:
                    self.stats["errors"] += 1
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.1)
        
        print(f"\n[Migration] Complete!")
        print(f"  Conversations scanned: {self.stats['conversations_scanned']}")
        print(f"  Facts found: {self.stats['facts_found']}")
        print(f"  Facts imported: {self.stats['facts_imported']}")
        print(f"  Errors: {self.stats['errors']}")
        
        return self.stats


async def main():
    """Run memory migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate conversation data to Graphiti memory")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, don't import")
    parser.add_argument("--limit", type=int, help="Maximum conversations to scan")
    args = parser.parse_args()
    
    migration = MemoryMigration()
    await migration.run(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
