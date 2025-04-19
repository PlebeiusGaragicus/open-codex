"""
Configuration management for Open Codex CLI.
Handles loading and saving of configuration, API keys, and provider settings.
"""

import os
import json
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Default settings
DEFAULT_PROVIDER = "ollama"
CONFIG_DIR = Path.home() / ".codex"
CONFIG_JSON_PATH = CONFIG_DIR / "config.json"
CONFIG_YAML_PATH = CONFIG_DIR / "config.yaml"
CONFIG_YML_PATH = CONFIG_DIR / "config.yml"
INSTRUCTIONS_PATH = CONFIG_DIR / "instructions.md"

# Provider-specific settings
PROVIDER_CONFIGS = {
    "ollama": {
        "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/api"),
        "models": {
            "agentic": "qwen2.5-coder",  # Default model for interactive coding
            "full_context": "llama3.1:8b"  # Default model for full context analysis
        }
    }
}

@dataclass
class Config:
    """Configuration class for Open Codex CLI."""
    provider: str
    model: str
    api_key: str
    base_url: str
    instructions: str
    instructions_path: Path
    memory_enabled: bool = False
    full_auto_error_mode: Optional[str] = None

def get_api_key_for_provider(provider: str) -> Optional[str]:
    """Get the API key for the specified provider."""
    if provider != "ollama":
        print(f"Error: Only Ollama provider is supported")
        return None
    return "ollama"  # Ollama doesn't require an API key

def load_project_doc(cwd: Path, explicit_path: Optional[str] = None,
                    max_size: int = 32 * 1024) -> Optional[str]:
    """Load the project documentation markdown if present."""
    doc_path = None
    
    if explicit_path:
        doc_path = Path(explicit_path)
    else:
        # Look for standard doc filenames
        doc_names = ["codex.md", ".codex.md", "CODEX.md"]
        current = Path(cwd)
        
        while current != current.parent:
            for name in doc_names:
                if (current / name).is_file():
                    doc_path = current / name
                    break
            else:
                if (current / ".git").exists():
                    break
                current = current.parent
                
    if not doc_path:
        return None
            
    try:
        content = doc_path.read_text()
        if len(content.encode()) > max_size:
            print(f"Warning: {doc_path} exceeds {max_size} bytes, truncating")
            content = content[:max_size]
        return content
    except Exception as e:
        print(f"Warning: Failed to read {doc_path}: {e}")
        return None

def load_config(provider: Optional[str] = None,
               model: Optional[str] = None,
               base_url: Optional[str] = None,
               disable_project_doc: bool = False,
               project_doc_path: Optional[str] = None) -> Config:
    """
    Load configuration from disk, environment variables, and arguments.
    
    Args:
        provider: Override the provider from config/env
        model: Override the model from config
        disable_project_doc: Skip loading project documentation
        project_doc_path: Explicit path to project documentation
    """
    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load stored config (try JSON first, then YAML)
    stored_config: Dict[str, Any] = {}
    config_paths = [CONFIG_JSON_PATH, CONFIG_YAML_PATH, CONFIG_YML_PATH]
    
    for path in config_paths:
        if path.exists():
            try:
                content = path.read_text()
                if path.suffix in ['.yaml', '.yml']:
                    stored_config = yaml.safe_load(content) or {}
                else:
                    stored_config = json.loads(content)
                break
            except Exception as e:
                print(f"Warning: Failed to load {path}: {e}")
    
    # Determine provider (priority: argument > env > stored > default)
    effective_provider = (
        provider or
        (DEFAULT_PROVIDER if not os.environ.get("OPENAI_API_KEY") and
         (os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY") or
          os.environ.get("OPENROUTER_API_KEY")) else None) or
        stored_config.get('provider') or
        DEFAULT_PROVIDER
    )
    
    # Get provider-specific settings
    provider_config = PROVIDER_CONFIGS.get(effective_provider, {})
    
    # Determine model (priority: argument > stored > provider default)
    effective_model = (
        model or
        stored_config.get('model') or
        provider_config.get('models', {}).get('agentic', '')
    )
    
    # Get API key
    api_key = get_api_key_for_provider(effective_provider)
    if not api_key:
        raise ValueError(f"No API key available for provider {effective_provider}")
    
    # Load instructions
    instructions = ""
    if INSTRUCTIONS_PATH.exists():
        try:
            instructions = INSTRUCTIONS_PATH.read_text()
        except Exception as e:
            print(f"Warning: Failed to load instructions: {e}")
    
    # Load project documentation if enabled
    if not disable_project_doc:
        project_doc = load_project_doc(
            Path.cwd(),
            explicit_path=project_doc_path
        )
        if project_doc:
            instructions = f"{instructions}\n\n{project_doc}"
    
    return Config(
        provider=effective_provider,
        model=effective_model,
        api_key=api_key,
        base_url=base_url or provider_config.get('base_url', ''),
        instructions=instructions,
        instructions_path=INSTRUCTIONS_PATH,
        memory_enabled=stored_config.get('memory', {}).get('enabled', False),
        full_auto_error_mode=stored_config.get('fullAutoErrorMode')
    )
