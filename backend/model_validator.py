"""
Model Validator - Validates available models on LLM server with per-model connection support
"""
import socket
import requests
import json
import sys
from typing import List, Dict, Any, Tuple, Set
import logging
from .config_loader import get_model_connection_info, load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelValidator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tested_endpoints: Set[str] = set()
        self.validated_models: Dict[str, Dict[str, str]] = {}
        
    def get_local_ip(self) -> str:
        """Get the local IPv4 address"""
        try:
            # Connect to a remote host to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.warning(f"Failed to auto-detect IP: {e}")
            return "127.0.0.1"
    
    def get_all_unique_endpoints(self) -> List[Dict[str, str]]:
        """Get all unique endpoints needed for validation."""
        endpoints = []
        seen_base_urls = set()
        
        # Get all models from config
        models = self.config.get("models", {})
        all_models = []
        
        # Collect council models
        council_models = models.get("council", [])
        for model in council_models:
            all_models.append(model["id"])
        
        # Add chairman model
        chairman = models.get("chairman", {})
        if chairman.get("id"):
            all_models.append(chairman["id"])
        
        # Get connection info for each model
        for model_id in all_models:
            connection_info = get_model_connection_info(model_id)
            base_url = connection_info["base_url"]
            
            if base_url not in seen_base_urls:
                seen_base_urls.add(base_url)
                endpoints.append({
                    "base_url": base_url,
                    "ip": connection_info["ip"],
                    "port": connection_info["port"],
                    "api_key": connection_info["api_key"]
                })
        
        return endpoints
    
    def test_endpoint(self, endpoint_info: Dict[str, str]) -> Tuple[bool, str, List[str]]:
        """Test connection to a specific endpoint and get available models."""
        base_url = endpoint_info["base_url"]
        api_key = endpoint_info["api_key"]
        
        try:
            models_url = f"{base_url}/models"
            logger.info(f"Testing connection to: {models_url}")
            
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            response = requests.get(models_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            available_models = self._extract_model_ids(models_data)
            
            logger.info(f"✓ Successfully connected to {base_url}")
            logger.info(f"  Found {len(available_models)} models")
            
            self.tested_endpoints.add(base_url)
            return True, "Connection successful", available_models
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Failed to connect to {base_url}"
            logger.error(error_msg)
            
            # Try fallback to localhost if not already localhost
            ip = endpoint_info["ip"]
            if ip != "127.0.0.1":
                logger.info(f"Trying fallback to 127.0.0.1 for {base_url}")
                fallback_base_url = base_url.replace(ip, "127.0.0.1")
                
                try:
                    models_url = f"{fallback_base_url}/models"
                    headers = {}
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                        
                    response = requests.get(models_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    models_data = response.json()
                    available_models = self._extract_model_ids(models_data)
                    
                    logger.info(f"✓ Successfully connected using localhost fallback: {fallback_base_url}")
                    
                    # Update endpoint info with successful fallback
                    endpoint_info["base_url"] = fallback_base_url
                    endpoint_info["ip"] = "127.0.0.1"
                    self.tested_endpoints.add(fallback_base_url)
                    
                    return True, "Connection successful with localhost fallback", available_models
                    
                except Exception as fallback_error:
                    return False, f"Connection failed even with localhost fallback: {fallback_error}", []
            
            return False, error_msg, []
            
        except requests.exceptions.Timeout:
            return False, f"Connection timeout to {base_url}", []
        except requests.exceptions.RequestException as e:
            return False, f"Request failed to {base_url}: {e}", []
        except Exception as e:
            return False, f"Unexpected error connecting to {base_url}: {e}", []
    
    def _extract_model_ids(self, models_data: Dict) -> List[str]:
        """Extract model IDs from API response."""
        available_models = []
        
        # Handle different response formats
        if "data" in models_data:
            for model in models_data["data"]:
                model_id = model.get("id", "")
                if model_id:
                    available_models.append(model_id)
        elif "models" in models_data:
            for model in models_data["models"]:
                model_id = model.get("name", model.get("id", ""))
                if model_id:
                    available_models.append(model_id)
        else:
            # Try to parse as simple list
            if isinstance(models_data, list):
                for model in models_data:
                    if isinstance(model, str):
                        available_models.append(model)
                    elif isinstance(model, dict):
                        model_id = model.get("id", model.get("name", ""))
                        if model_id:
                            available_models.append(model_id)
        
        return available_models
    
    def validate_model_availability(self, model_id: str, available_models_by_endpoint: Dict[str, List[str]]) -> Tuple[bool, str]:
        """Validate that a specific model is available on its configured endpoint."""
        connection_info = get_model_connection_info(model_id)
        base_url = connection_info["base_url"]
        
        # Find the available models for this endpoint
        available_models = available_models_by_endpoint.get(base_url, [])
        
        if model_id in available_models:
            self.validated_models[model_id] = connection_info
            logger.info(f"✓ Model {model_id} validated at {base_url}")
            return True, f"Model {model_id} available"
        else:
            logger.error(f"✗ Model {model_id} not found at {base_url}")
            logger.error(f"  Available models at this endpoint: {available_models[:10]}{'...' if len(available_models) > 10 else ''}")
            return False, f"Model {model_id} not available at {base_url}"
    
    def validate_all(self) -> Tuple[bool, str]:
        """Run complete validation process for all models and their endpoints."""
        logger.info("Starting per-model validation...")
        
        # Get all unique endpoints that need testing
        endpoints = self.get_all_unique_endpoints()
        logger.info(f"Found {len(endpoints)} unique endpoints to test")
        
        # Test each unique endpoint and collect available models
        available_models_by_endpoint = {}
        failed_endpoints = []
        
        for endpoint_info in endpoints:
            base_url = endpoint_info["base_url"]
            success, message, available_models = self.test_endpoint(endpoint_info)
            
            if success:
                available_models_by_endpoint[base_url] = available_models
                # Update the base_url in case it was changed by fallback
                available_models_by_endpoint[endpoint_info["base_url"]] = available_models
            else:
                failed_endpoints.append((base_url, message))
        
        if failed_endpoints:
            error_details = "; ".join([f"{url}: {msg}" for url, msg in failed_endpoints])
            return False, f"Failed to connect to endpoints: {error_details}"
        
        # Validate each configured model
        models = self.config.get("models", {})
        failed_models = []
        
        # Validate council models
        council_models = models.get("council", [])
        for model in council_models:
            model_id = model["id"]
            success, message = self.validate_model_availability(model_id, available_models_by_endpoint)
            if not success:
                failed_models.append((model_id, message))
        
        # Validate chairman model
        chairman = models.get("chairman", {})
        if chairman.get("id"):
            model_id = chairman["id"]
            success, message = self.validate_model_availability(model_id, available_models_by_endpoint)
            if not success:
                failed_models.append((model_id, message))
        
        # Check if we have enough models
        if len(self.validated_models) < 3:
            return False, f"Insufficient models validated. Need at least 3, got {len(self.validated_models)}"
        
        if failed_models:
            error_details = "; ".join([f"{model}: {msg}" for model, msg in failed_models])
            return False, f"Model validation failed: {error_details}"
        
        logger.info(f"✓ All {len(self.validated_models)} models validated successfully")
        return True, f"Validation successful. Validated {len(self.validated_models)} models across {len(available_models_by_endpoint)} endpoints"
    
    def get_validated_models(self) -> Dict[str, Dict[str, str]]:
        """Get dictionary of validated models and their connection info."""
        return self.validated_models.copy()

def validate_models(config: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Dict[str, str]]]:
    """
    Validate all models with their per-model configuration.
    
    Returns:
        Tuple of (success, message, validated_models_dict)
    """
    validator = ModelValidator(config)
    success, message = validator.validate_all()
    validated_models = validator.get_validated_models() if success else {}
    return success, message, validated_models