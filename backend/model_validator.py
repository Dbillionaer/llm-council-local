"""
Model Validator - Validates available models on LLM server
"""
import socket
import requests
import json
import sys
from typing import List, Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelValidator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.server_ip = None
        self.base_url = None
        
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
    
    def setup_connection(self) -> Tuple[bool, str]:
        """Setup connection parameters and test connectivity"""
        server_config = self.config.get("server", {})
        server_ip = server_config.get("ip", "")
        server_port = server_config.get("port", "11434")
        
        # Use configured IP or auto-detect
        if not server_ip:
            self.server_ip = self.get_local_ip()
            logger.info(f"Auto-detected IP address: {self.server_ip}")
        else:
            self.server_ip = server_ip
            logger.info(f"Using configured IP address: {self.server_ip}")
        
        # Build base URL
        base_url_template = server_config.get("base_url_template", "http://{ip}:{port}/v1")
        self.base_url = base_url_template.format(ip=self.server_ip, port=server_port)
        
        return self.test_connection()
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test connection to LLM server"""
        try:
            models_url = f"{self.base_url}/models"
            logger.info(f"Testing connection to: {models_url}")
            
            response = requests.get(models_url, timeout=10)
            response.raise_for_status()
            
            logger.info("✓ Successfully connected to LLM server")
            return True, "Connection successful"
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Failed to connect to LLM server at {self.base_url}"
            logger.error(error_msg)
            
            # Try fallback to localhost
            if self.server_ip != "127.0.0.1":
                logger.info("Trying fallback to 127.0.0.1...")
                self.server_ip = "127.0.0.1"
                server_config = self.config.get("server", {})
                server_port = server_config.get("port", "11434")
                base_url_template = server_config.get("base_url_template", "http://{ip}:{port}/v1")
                self.base_url = base_url_template.format(ip=self.server_ip, port=server_port)
                
                try:
                    models_url = f"{self.base_url}/models"
                    response = requests.get(models_url, timeout=10)
                    response.raise_for_status()
                    logger.info("✓ Successfully connected using localhost fallback")
                    return True, "Connection successful with localhost fallback"
                except Exception as fallback_error:
                    return False, f"Connection failed even with localhost fallback: {fallback_error}"
            
            return False, error_msg
            
        except requests.exceptions.Timeout:
            return False, f"Connection timeout to LLM server at {self.base_url}"
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    def get_available_models(self) -> Tuple[bool, List[str], str]:
        """Get list of available models from LLM server"""
        try:
            models_url = f"{self.base_url}/models"
            response = requests.get(models_url, timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            
            # Extract model IDs (handle different response formats)
            available_models = []
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
            
            logger.info(f"Found {len(available_models)} available models")
            for model in available_models:
                logger.info(f"  - {model}")
            
            return True, available_models, "Successfully retrieved models"
            
        except Exception as e:
            error_msg = f"Failed to retrieve models: {e}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def validate_configured_models(self, available_models: List[str]) -> Tuple[bool, List[str], str]:
        """Validate that configured models are available"""
        if len(available_models) < 3:
            return False, [], f"Insufficient models available. Found {len(available_models)}, need at least 3."
        
        configured_models = []
        missing_models = []
        
        # Check council models
        council_models = self.config.get("models", {}).get("council", [])
        for model in council_models:
            model_id = model.get("id", "")
            if model_id:
                configured_models.append(model_id)
                if model_id not in available_models:
                    missing_models.append(model_id)
        
        # Check chairman model
        chairman = self.config.get("models", {}).get("chairman", {})
        chairman_id = chairman.get("id", "")
        if chairman_id:
            configured_models.append(chairman_id)
            if chairman_id not in available_models:
                missing_models.append(chairman_id)
        
        if missing_models:
            error_msg = f"Configured models not found on server: {missing_models}"
            logger.error(error_msg)
            logger.error("Available models:")
            for model in available_models:
                logger.error(f"  - {model}")
            return False, missing_models, error_msg
        
        logger.info("✓ All configured models are available")
        return True, [], "All configured models validated"
    
    def validate_all(self) -> Tuple[bool, str]:
        """Run complete validation process"""
        logger.info("Starting model validation...")
        
        # Setup connection
        connected, conn_msg = self.setup_connection()
        if not connected:
            return False, f"Connection failed: {conn_msg}"
        
        # Get available models
        success, available_models, models_msg = self.get_available_models()
        if not success:
            return False, f"Model retrieval failed: {models_msg}"
        
        # Validate configured models
        valid, missing, validation_msg = self.validate_configured_models(available_models)
        if not valid:
            return False, f"Model validation failed: {validation_msg}"
        
        logger.info("✓ Model validation completed successfully")
        return True, f"Validation successful. Using server at {self.base_url}"
    
    def get_base_url(self) -> str:
        """Get the validated base URL"""
        return self.base_url

def validate_models(config: Dict[str, Any]) -> Tuple[bool, str, str]:
    """
    Validate models and return success status, error message, and base URL
    """
    validator = ModelValidator(config)
    success, message = validator.validate_all()
    base_url = validator.get_base_url() if success else ""
    return success, message, base_url