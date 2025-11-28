"""
Prompt Library for LLM Council.

This module provides intelligent prompt engineering by:
1. Storing and retrieving proven prompts from a library
2. Dynamically generating new prompts when needed
3. Learning which prompts work best for specific scenarios
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .config_loader import get_prompt_engineer_model, load_config
from .lmstudio import query_model


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_library_paths() -> tuple[Path, Path]:
    """Get paths to prompt library files."""
    root = get_project_root()
    return (
        root / "data" / "prompt_library.md",
        root / "data" / "prompt_library.json"
    )


def _load_library_json() -> Dict[str, Any]:
    """Load the prompt library JSON file."""
    _, json_path = get_library_paths()
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"prompts": {}, "scenarios": {}, "metadata": {"version": "1.0"}}


def _save_library_json(data: Dict[str, Any]):
    """Save the prompt library JSON file."""
    _, json_path = get_library_paths()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def _save_library_md(data: Dict[str, Any]):
    """Save the prompt library markdown file for human readability."""
    md_path, _ = get_library_paths()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = ["# Prompt Library\n"]
    lines.append(f"*Last updated: {datetime.now().isoformat()}*\n\n")
    
    for prompt_id, prompt_data in data.get("prompts", {}).items():
        lines.append(f"## {prompt_data.get('name', prompt_id)}\n")
        lines.append(f"**ID:** `{prompt_id}`\n")
        lines.append(f"**Category:** {prompt_data.get('category', 'general')}\n")
        lines.append(f"**Success Rate:** {prompt_data.get('success_rate', 'N/A')}\n")
        lines.append(f"**Created:** {prompt_data.get('created', 'N/A')}\n\n")
        lines.append("### Prompt\n```\n")
        lines.append(prompt_data.get('prompt', ''))
        lines.append("\n```\n\n")
        if prompt_data.get('scenarios'):
            lines.append("### Best For\n")
            for scenario in prompt_data['scenarios']:
                lines.append(f"- {scenario}\n")
            lines.append("\n")
        lines.append("---\n\n")
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def _generate_prompt_id(category: str, user_query: str) -> str:
    """Generate a unique prompt ID based on category and query pattern."""
    # Create a hash of the normalized query pattern
    normalized = category.lower() + ":" + user_query.lower()[:100]
    hash_suffix = hashlib.md5(normalized.encode()).hexdigest()[:8]
    return f"{category}_{hash_suffix}"


def _categorize_query(user_query: str, tool_name: Optional[str] = None) -> str:
    """Categorize a query to find matching prompts."""
    query_lower = user_query.lower()
    
    # Tool-based categorization
    if tool_name:
        if 'search' in tool_name.lower():
            if any(w in query_lower for w in ['news', 'headline', 'current events']):
                return 'news_extraction'
            if any(w in query_lower for w in ['weather', 'temperature', 'forecast']):
                return 'weather_extraction'
            return 'web_search'
        if 'geo' in tool_name.lower() or 'location' in tool_name.lower():
            return 'location_extraction'
        if 'date' in tool_name.lower() or 'time' in tool_name.lower():
            return 'datetime_extraction'
        if 'calculator' in tool_name.lower():
            return 'calculation'
    
    # Query-based categorization (fallback)
    if any(w in query_lower for w in ['news', 'headline', 'happening']):
        return 'news_extraction'
    if any(w in query_lower for w in ['weather', 'temperature', 'forecast']):
        return 'weather_extraction'
    if any(w in query_lower for w in ['where am i', 'location', 'ip address']):
        return 'location_extraction'
    if any(w in query_lower for w in ['time', 'date', 'today']):
        return 'datetime_extraction'
    
    return 'general'


def find_matching_prompt(
    user_query: str,
    tool_name: Optional[str] = None,
    tool_output: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Find a matching prompt from the library.
    
    Args:
        user_query: The user's original question
        tool_name: Name of the tool being used (if any)
        tool_output: Output from the tool (if any)
    
    Returns:
        Matching prompt string or None if no match found
    """
    library = _load_library_json()
    category = _categorize_query(user_query, tool_name)
    
    # Find prompts matching this category
    best_prompt = None
    best_score = 0
    
    for prompt_id, prompt_data in library.get("prompts", {}).items():
        if prompt_data.get('category') == category:
            # Calculate match score based on success rate and usage
            score = prompt_data.get('success_rate', 0.5) * prompt_data.get('usage_count', 1)
            if score > best_score:
                best_score = score
                best_prompt = prompt_data.get('prompt')
    
    return best_prompt


async def generate_extraction_prompt(
    user_query: str,
    tool_name: str,
    tool_output: Dict[str, Any]
) -> str:
    """
    Generate a prompt for extracting and presenting information from tool output.
    
    Args:
        user_query: The user's original question
        tool_name: Name of the tool that was called
        tool_output: Raw output from the tool
    
    Returns:
        Generated prompt for the response LLM
    """
    # First, check if we have a matching prompt in the library
    existing_prompt = find_matching_prompt(user_query, tool_name, tool_output)
    if existing_prompt:
        print(f"[PromptLibrary] Using cached prompt for {_categorize_query(user_query, tool_name)}")
        return existing_prompt
    
    # Generate a new prompt using the prompt engineer model
    print(f"[PromptLibrary] Generating new prompt for: {user_query[:50]}...")
    
    prompt_engineer_model = get_prompt_engineer_model()
    
    meta_prompt = f"""You are an expert prompt engineer. Your task is to craft the perfect prompt for an LLM to extract and present information from tool output to answer a user's question.

USER'S QUESTION: {user_query}

TOOL USED: {tool_name}

TOOL OUTPUT STRUCTURE:
{json.dumps(tool_output, indent=2)[:2000]}

TASK: Create a prompt that will:
1. Instruct the LLM to extract the SPECIFIC information the user asked for
2. Guide the LLM to present it in a clear, useful format
3. Ensure the LLM uses the ACTUAL DATA from the tool output, not generic descriptions

For example:
- If user asks for "news headlines", the prompt should instruct to extract actual headlines/events from snippets
- If user asks for "weather", the prompt should instruct to extract temperature, conditions, etc.
- If user asks for "location", the prompt should instruct to extract city, region, country

OUTPUT ONLY the prompt text that will be sent to the response LLM. No explanations or meta-commentary.
The prompt should be direct and actionable."""

    messages = [{"role": "user", "content": meta_prompt}]
    
    try:
        response = await query_model(prompt_engineer_model, messages, timeout=30.0)
        if response and response.get('content'):
            generated_prompt = response['content'].strip()
            
            # Store the generated prompt in the library
            category = _categorize_query(user_query, tool_name)
            _store_prompt(category, user_query, generated_prompt)
            
            return generated_prompt
    except Exception as e:
        print(f"[PromptLibrary] Error generating prompt: {e}")
    
    # Fallback to a default prompt
    return _get_default_extraction_prompt(user_query, tool_name)


def _store_prompt(category: str, user_query: str, prompt: str):
    """Store a generated prompt in the library."""
    library = _load_library_json()
    
    prompt_id = _generate_prompt_id(category, user_query)
    
    if prompt_id not in library["prompts"]:
        library["prompts"][prompt_id] = {
            "name": f"{category.replace('_', ' ').title()} Prompt",
            "category": category,
            "prompt": prompt,
            "created": datetime.now().isoformat(),
            "success_rate": 0.5,  # Initial neutral score
            "usage_count": 1,
            "scenarios": [user_query[:100]]
        }
    else:
        # Update existing prompt
        library["prompts"][prompt_id]["usage_count"] += 1
        if user_query[:100] not in library["prompts"][prompt_id]["scenarios"]:
            library["prompts"][prompt_id]["scenarios"].append(user_query[:100])
    
    _save_library_json(library)
    _save_library_md(library)
    print(f"[PromptLibrary] Stored prompt: {prompt_id}")


def update_prompt_success(prompt_id: str, success: bool):
    """Update the success rate of a prompt based on user feedback or validation."""
    library = _load_library_json()
    
    if prompt_id in library["prompts"]:
        current = library["prompts"][prompt_id]
        usage = current.get("usage_count", 1)
        old_rate = current.get("success_rate", 0.5)
        
        # Exponential moving average for success rate
        alpha = min(0.3, 1.0 / usage)  # More weight to recent results initially
        new_rate = old_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
        
        library["prompts"][prompt_id]["success_rate"] = new_rate
        _save_library_json(library)


def _get_default_extraction_prompt(user_query: str, tool_name: str) -> str:
    """Get a default extraction prompt when generation fails."""
    category = _categorize_query(user_query, tool_name)
    
    defaults = {
        'news_extraction': """Extract and present the actual news headlines and events from the tool output.
Focus on the "snippet" fields which contain real news content - NOT just website names.
List specific events, names, dates, and developments mentioned.
Present as a numbered list of actual news items.""",
        
        'weather_extraction': """Extract the current weather information from the tool output.
Look for temperature, conditions, humidity, wind, and forecast details.
Present the weather clearly with specific values and conditions.""",
        
        'location_extraction': """Extract the geographic location information from the tool output.
Present the city, region/state, country, and any other relevant location details.
Be specific about the detected location.""",
        
        'datetime_extraction': """Extract and present the current date and time from the tool output.
Include the full date, day of week, and time with timezone if available.""",
        
        'web_search': """Extract the most relevant information from the search results to answer the user's question.
Focus on the actual content in snippets, not just titles.
Synthesize the information into a clear, helpful response.""",
        
        'general': """Present the information from the tool output in a clear, organized manner.
Focus on the specific data that answers the user's question.
Use the actual values and content from the tool output."""
    }
    
    return defaults.get(category, defaults['general'])


def get_prompt_library_stats() -> Dict[str, Any]:
    """Get statistics about the prompt library."""
    library = _load_library_json()
    
    prompts = library.get("prompts", {})
    categories = {}
    total_usage = 0
    avg_success = 0
    
    for prompt_data in prompts.values():
        cat = prompt_data.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1
        total_usage += prompt_data.get("usage_count", 0)
        avg_success += prompt_data.get("success_rate", 0)
    
    return {
        "total_prompts": len(prompts),
        "categories": categories,
        "total_usage": total_usage,
        "average_success_rate": avg_success / len(prompts) if prompts else 0
    }
