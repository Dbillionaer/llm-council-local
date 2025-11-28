#!/usr/bin/env python3
"""Patch factories.py to add LMStudio provider support."""

import re

FACTORIES_PATH = "/app/graphiti/mcp_server/src/services/factories.py"

# Read the file
with open(FACTORIES_PATH, "r") as f:
    content = f.read()

# Add import after existing imports
import_addition = '''
# Import custom LMStudio client
try:
    from src.lmstudio_client import LMStudioClient
    HAS_LMSTUDIO = True
except ImportError:
    HAS_LMSTUDIO = False
'''

# Find a good place to add the import (after other try/except imports)
if "HAS_LMSTUDIO" not in content:
    # Add after the last HAS_* import block
    pattern = r"(try:\s+from graphiti_core\.llm_client\.groq_client.*?HAS_GROQ = False)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.end()] + import_addition + content[match.end():]
    else:
        # Fallback: add after imports section
        pattern = r"(from utils\.utils import create_azure_credential_token_provider)"
        content = re.sub(pattern, r"\1" + import_addition, content)

# Add the lmstudio case to the LLM match statement
lmstudio_case = '''
            case 'lmstudio':
                # For LM Studio with strict JSON schema support
                if not HAS_LMSTUDIO:
                    raise ValueError('LMStudioClient not available')
                import os
                api_key = os.environ.get('OPENAI_API_KEY', 'lms')
                base_url = os.environ.get('OPENAI_BASE_URL', 'http://localhost:1234/v1')
                logger.info(f'Creating LM Studio client with base_url: {base_url}')
                from graphiti_core.llm_client.config import LLMConfig as CoreLLMConfig
                llm_config = CoreLLMConfig(
                    api_key=api_key,
                    base_url=base_url,
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens or 16384,
                )
                return LMStudioClient(config=llm_config, max_tokens=config.max_tokens or 16384)
'''

# Insert before "case _:" (default case) in LLMFactory
if "'lmstudio'" not in content:
    content = re.sub(
        r"(\n            case _:)",
        lmstudio_case + r"\1",
        content,
        count=1  # Only the first match (LLMFactory)
    )

# Add openai_generic case to EmbedderFactory for LM Studio embeddings
openai_generic_embedder_case = '''            case 'openai_generic':
                # OpenAI-compatible embedder with custom base URL (e.g., LM Studio)
                import os
                api_key = os.environ.get('EMBEDDER_API_KEY', 'lms')
                base_url = os.environ.get('EMBEDDER_BASE_URL', 'http://localhost:1234/v1')
                
                from graphiti_core.embedder.openai import OpenAIEmbedderConfig
                
                # Get embedding dimension from environment or use default
                embedding_dim = int(os.environ.get('EMBEDDER_DIM', '768'))
                
                logger.info(f'Creating OpenAI-generic embedder with base_url: {base_url}, model: {config.model}, dim: {embedding_dim}')
                embedder_config = OpenAIEmbedderConfig(
                    api_key=api_key,
                    base_url=base_url,
                    embedding_model=config.model,
                    embedding_dim=embedding_dim,
                )
                return OpenAIEmbedder(config=embedder_config)

'''

# Find the case 'voyage' in EmbedderFactory and add our case after it
if "'openai_generic'" not in content:
    # Find the voyage case and its return statement, then add after
    pattern = r"(return VoyageAIEmbedder\(config=voyage_config\))\n\n(            case _:)"
    replacement = r"\1\n\n" + openai_generic_embedder_case + r"\2"
    content = re.sub(pattern, replacement, content)

# Write back
with open(FACTORIES_PATH, "w") as f:
    f.write(content)

print("Successfully patched factories.py with LMStudio LLM and openai_generic embedder support")
