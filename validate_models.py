#!/usr/bin/env python3
"""Configuration validation tool for LLM Council."""

import json
import sys
from pathlib import Path

def main():
    """Validate config.json configuration."""
    config_path = Path("config.json")
    models_path = Path("models.json")  # Legacy format
    
    print("LLM Council - Configuration Validator")
    print("=" * 50)
    
    # Check which file exists
    if config_path.exists():
        config_file = config_path
        format_type = "config.json (current format)"
    elif models_path.exists():
        config_file = models_path
        format_type = "models.json (legacy format)"
    else:
        print(f"❌ Configuration file not found")
        print("💡 Create config.json with models and deliberation settings")
        return 1
    
    print(f"📁 Found: {config_file} ({format_type})")
    
    # Load and parse JSON
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ JSON syntax valid in {config_file}")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON syntax: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return 1
    
    # Determine format and validate
    if config_file.name == "config.json":
        return validate_config_format(config)
    else:
        return validate_models_format(config)

def validate_config_format(config: dict) -> int:
    """Validate new config.json format."""
    errors = []
    
    # Check required top-level fields
    if not isinstance(config, dict):
        errors.append("Configuration must be a JSON object")
    
    if "models" not in config:
        errors.append("Missing 'models' field")
    
    if errors:
        for error in errors:
            print(f"❌ {error}")
        return 1
    
    # Validate models section
    models = config["models"]
    if not isinstance(models, dict):
        print("❌ 'models' must be an object")
        return 1
    
    if not validate_models_section(models):
        return 1
    
    print("✅ Models configuration valid")
    
    # Validate deliberation section (optional)
    if "deliberation" in config:
        if not validate_deliberation_section(config["deliberation"]):
            return 1
        print("✅ Deliberation configuration valid")
    else:
        print("ℹ️  No deliberation configuration (will use defaults)")
    
    # Print summary
    return print_config_summary(config)

def validate_models_format(config: dict) -> int:
    """Validate legacy models.json format."""
    if not validate_models_section(config):
        return 1
    
    print("✅ Legacy models configuration valid")
    print("💡 Consider migrating to config.json format for deliberation features")
    
    # Create synthetic config for summary
    synthetic_config = {
        "models": config,
        "deliberation": {"rounds": 1}  # Default for legacy
    }
    return print_config_summary(synthetic_config)

def validate_models_section(models: dict) -> bool:
    """Validate the models section (works for both formats)."""
    if "council" not in models:
        print("❌ Missing 'council' field")
        return False
    
    if "chairman" not in models:
        print("❌ Missing 'chairman' field")
        return False
    
    # Validate council models
    council = models["council"]
    if not isinstance(council, list):
        print("❌ 'council' must be an array")
        return False
    
    if len(council) == 0:
        print("❌ Council must have at least one model")
        return False
    
    for i, model in enumerate(council):
        if not isinstance(model, dict):
            print(f"❌ Council model {i+1} must be an object")
            return False
        
        if "id" not in model:
            print(f"❌ Council model {i+1} missing 'id' field")
            return False
        
        if "name" not in model:
            print(f"❌ Council model {i+1} missing 'name' field")
            return False
        
        if not isinstance(model["id"], str) or not model["id"].strip():
            print(f"❌ Council model {i+1} 'id' must be a non-empty string")
            return False
        
        if not isinstance(model["name"], str) or not model["name"].strip():
            print(f"❌ Council model {i+1} 'name' must be a non-empty string")
            return False
    
    # Validate chairman model
    chairman = models["chairman"]
    if not isinstance(chairman, dict):
        print("❌ 'chairman' must be an object")
        return False
    
    if "id" not in chairman:
        print("❌ Chairman model missing 'id' field")
        return False
    
    if "name" not in chairman:
        print("❌ Chairman model missing 'name' field")
        return False
    
    if not isinstance(chairman["id"], str) or not chairman["id"].strip():
        print("❌ Chairman 'id' must be a non-empty string")
        return False
    
    if not isinstance(chairman["name"], str) or not chairman["name"].strip():
        print("❌ Chairman 'name' must be a non-empty string")
        return False
    
    return True

def validate_deliberation_section(deliberation: dict) -> bool:
    """Validate deliberation configuration."""
    if not isinstance(deliberation, dict):
        print("❌ 'deliberation' must be an object")
        return False
    
    # Validate rounds
    if "rounds" in deliberation:
        rounds = deliberation["rounds"]
        if not isinstance(rounds, int) or rounds < 1 or rounds > 5:
            print("❌ 'rounds' must be an integer between 1 and 5")
            return False
    
    # Validate max_rounds
    if "max_rounds" in deliberation:
        max_rounds = deliberation["max_rounds"]
        if not isinstance(max_rounds, int) or max_rounds < 1:
            print("❌ 'max_rounds' must be a positive integer")
            return False
    
    # Validate enable_cross_review
    if "enable_cross_review" in deliberation:
        if not isinstance(deliberation["enable_cross_review"], bool):
            print("❌ 'enable_cross_review' must be a boolean")
            return False
    
    return True

def print_config_summary(config: dict) -> int:
    """Print configuration summary."""
    print("\n📋 Configuration Summary:")
    
    models = config["models"]
    council = models["council"]
    chairman = models["chairman"]
    
    print(f"   Council Models: {len(council)}")
    for i, model in enumerate(council, 1):
        print(f"     {i}. {model['name']} ({model['id']})")
    
    print(f"   Chairman: {chairman['name']} ({chairman['id']})")
    
    # Deliberation info
    if "deliberation" in config:
        deliberation = config["deliberation"]
        rounds = deliberation.get("rounds", 1)
        max_rounds = deliberation.get("max_rounds", 5)
        cross_review = deliberation.get("enable_cross_review", True)
        
        print(f"   Deliberation Rounds: {rounds}")
        print(f"   Max Rounds: {max_rounds}")
        print(f"   Cross Review: {cross_review}")
        
        if rounds > 1:
            print(f"   🔄 Multi-round deliberation enabled")
        else:
            print(f"   ➡️  Single-round deliberation")
    
    # Metadata
    if "metadata" in config:
        metadata = config["metadata"]
        if "version" in metadata:
            print(f"   Version: {metadata['version']}")
        if "updated" in metadata:
            print(f"   Updated: {metadata['updated']}")
    
    print("\n🎉 Configuration is valid and ready to use!")
    return 0

if __name__ == "__main__":
    sys.exit(main())