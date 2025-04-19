"""Tests for configuration management."""
import os
from pathlib import Path
import pytest
from src.core.config import load_config, Config, get_api_key_for_provider

def test_get_api_key_for_provider():
    # Test Ollama (no key required)
    assert get_api_key_for_provider('ollama') == 'ollama'
    
    # Test other providers (should be rejected)
    assert get_api_key_for_provider('openai') is None
    assert get_api_key_for_provider('invalid') is None

def test_load_config_defaults(monkeypatch, tmp_path):
    # Setup test environment
    monkeypatch.setattr('src.core.config.CONFIG_DIR', tmp_path)
    
    # Test default configuration
    config = load_config()
    assert isinstance(config, Config)
    assert config.provider == 'ollama'
    assert config.api_key == 'ollama'
    assert config.model == 'qwen2.5-coder'  # Default model
    assert 'localhost:11434' in config.base_url

def test_load_config_model_override(monkeypatch, tmp_path):
    # Setup test environment
    monkeypatch.setattr('src.core.config.CONFIG_DIR', tmp_path)
    
    # Test model override
    config = load_config(model='llama3.1:8b')
    assert config.provider == 'ollama'
    assert config.model == 'llama3.1:8b'
    assert 'localhost:11434' in config.base_url

def test_load_config_with_project_doc(tmp_path):
    # Create a test project doc
    project_doc = tmp_path / 'codex.md'
    project_doc.write_text('# Test Project\nThis is a test project.')
    
    # Test loading with project doc
    config = load_config(project_doc_path=str(project_doc))
    assert 'Test Project' in config.instructions
