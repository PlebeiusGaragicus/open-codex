"""Tests for LLM functionality."""
import json
import pytest
import httpx
from src.core.llm import OllamaClient, Message, ModelResponse

@pytest.mark.asyncio
async def test_ollama_generate(respx_mock):
    """Test the generate method of OllamaClient."""
    # Mock the Ollama API response
    api_url = "http://localhost:11434/api/chat"
    mock_responses = [
        {"message": {"content": "Hello"}},
        {"message": {"content": " World"}, "done": True}
    ]
    
    # Setup mock response
    respx_mock.post(api_url).mock(
        return_value=httpx.Response(
            200,
            content="\n".join(json.dumps(r) for r in mock_responses)
        )
    )
    
    async with OllamaClient() as client:
        messages = [Message(role="user", content="Say hello")]
        responses = []
        
        async for response in client.generate("qwen2.5-coder", messages):
            responses.append(response)
            
        # Check responses
        assert len(responses) == 2
        assert responses[0].content == "Hello"
        assert not responses[0].done
        assert responses[1].content == "Hello World"
        assert responses[1].done

@pytest.mark.asyncio
async def test_ollama_generate_with_tool_calls(respx_mock):
    """Test generation with tool calls."""
    api_url = "http://localhost:11434/api/chat"
    mock_responses = [
        {
            "message": {"content": "Let me help with that."},
            "tool_calls": [{
                "type": "function",
                "function": {
                    "name": "write_file",
                    "arguments": {"path": "test.txt", "content": "Hello"}
                }
            }],
            "done": True
        }
    ]
    
    # Setup mock response
    respx_mock.post(api_url).mock(
        return_value=httpx.Response(
            200,
            content="\n".join(json.dumps(r) for r in mock_responses)
        )
    )
    
    async with OllamaClient() as client:
        messages = [Message(role="user", content="Create a file")]
        async for response in client.generate("qwen2.5-coder", messages):
            assert response.tool_calls is not None
            assert response.tool_calls[0]["type"] == "function"
            assert response.tool_calls[0]["function"]["name"] == "write_file"

@pytest.mark.asyncio
async def test_ollama_get_model_list(respx_mock):
    """Test getting available models."""
    api_url = "http://localhost:11434/api/tags"
    mock_response = {
        "models": [
            {"name": "qwen2.5-coder"},
            {"name": "llama3.1:8b"}
        ]
    }
    
    # Setup mock response
    respx_mock.get(api_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )
    
    async with OllamaClient() as client:
        models = await client.get_model_list()
        assert "qwen2.5-coder" in models
        assert "llama3.1:8b" in models

@pytest.mark.asyncio
async def test_ollama_error_handling(respx_mock):
    """Test error handling."""
    api_url = "http://localhost:11434/api/chat"
    mock_response = {"error": "Model not found"}
    
    # Setup mock response
    respx_mock.post(api_url).mock(
        return_value=httpx.Response(
            200,
            content=json.dumps(mock_response)
        )
    )
    
    async with OllamaClient() as client:
        messages = [Message(role="user", content="Hello")]
        with pytest.raises(ValueError, match="Ollama error: Model not found"):
            async for _ in client.generate("nonexistent-model", messages):
                pass
