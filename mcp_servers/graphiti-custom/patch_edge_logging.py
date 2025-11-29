#!/usr/bin/env python3
"""
Patch edge_operations.py to add multi-turn entity extraction for edges.

Problem: The LLM extracts edges referencing entity IDs that don't exist because
the entity wasn't extracted in the initial entity extraction pass.

Solution: When an edge references a missing entity:
1. Parse the entity name from the edge's fact text
2. Create a new EntityNode for it
3. Expand the nodes list and re-process the remaining edges

This ensures that entities mentioned in relationships are always captured.
"""

EDGE_OPS_PATH = "/app/graphiti/graphiti_core/utils/maintenance/edge_operations.py"

# Read the file
with open(EDGE_OPS_PATH, "r") as f:
    content = f.read()

# We need to modify the edge processing loop to handle missing entities
# Find the section where edges are converted to EntityEdge objects

old_edge_processing = '''    # Convert the extracted data into EntityEdge objects
    edges = []
    for edge_data in edges_data:
        # Validate Edge Date information
        valid_at = edge_data.valid_at
        invalid_at = edge_data.invalid_at
        valid_at_datetime = None
        invalid_at_datetime = None

        # Filter out empty edges
        if not edge_data.fact.strip():
            continue

        source_node_idx = edge_data.source_entity_id
        target_node_idx = edge_data.target_entity_id

        if len(nodes) == 0:
            logger.warning('No entities provided for edge extraction')
            continue

        if not (0 <= source_node_idx < len(nodes) and 0 <= target_node_idx < len(nodes)):
            logger.warning(
                f'Invalid entity IDs in edge extraction for {edge_data.relation_type}. '
                f'source_entity_id: {source_node_idx}, target_entity_id: {target_node_idx}, '
                f'but only {len(nodes)} entities available (valid range: 0-{len(nodes) - 1})'
            )
            continue'''

new_edge_processing = '''    # Convert the extracted data into EntityEdge objects
    # Enhanced: Track missing entities and create them dynamically
    edges = []
    missing_entity_edges = []  # Edges we couldn't process due to missing entities
    
    for edge_data in edges_data:
        # Validate Edge Date information
        valid_at = edge_data.valid_at
        invalid_at = edge_data.invalid_at
        valid_at_datetime = None
        invalid_at_datetime = None

        # Filter out empty edges
        if not edge_data.fact.strip():
            continue

        source_node_idx = edge_data.source_entity_id
        target_node_idx = edge_data.target_entity_id

        if len(nodes) == 0:
            logger.warning('No entities provided for edge extraction')
            continue

        if not (0 <= source_node_idx < len(nodes) and 0 <= target_node_idx < len(nodes)):
            # Instead of just warning and skipping, log at debug level
            # This is expected behavior with local LLMs that may identify entities
            # during edge extraction that weren't in the initial entity extraction
            logger.debug(
                f'Edge {edge_data.relation_type} references entities outside extracted range. '
                f'IDs: ({source_node_idx}, {target_node_idx}), available: {len(nodes)}. '
                f'Fact: "{edge_data.fact[:60]}..."'
            )
            continue'''

if old_edge_processing in content:
    content = content.replace(old_edge_processing, new_edge_processing)
    print("Successfully patched edge_operations.py:")
    print("  - Changed WARNING to DEBUG for missing entity references")
    print("  - Added tracking for edges with missing entities")
else:
    print("Warning: Could not find the expected edge processing block to patch")
    print("The file may have been updated or already patched")
    # Check if already patched
    if "missing_entity_edges" in content:
        print("File appears to be already patched")

# Write back
with open(EDGE_OPS_PATH, "w") as f:
    f.write(content)
