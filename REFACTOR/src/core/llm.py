"""
Core LLM functionality using Ollama as the backend.
Handles model interaction, streaming, and response processing.
"""

import json
from typing import AsyncIterator, Dict, List, Optional, Union
import httpx
from dataclasses import dataclass

@dataclass
class Message:
    """Represents a message in the conversation."""
    role: str
    content: str
    images: Optional[List[str]] = None
    tool_calls: Optional[List[Dict]] = None

@dataclass
class ModelResponse:
    """Represents a response from the model."""
    content: str
    tool_calls: Optional[List[Dict]] = None
    done: bool = False

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434/api", timeout: int = 60):
        """Initialize the Ollama client.
        
        Args:
            base_url: Base URL for the Ollama API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()

    async def generate(self, 
                      model: str,
                      messages: List[Message],
                      stream: bool = True,
                      temperature: float = 0.7,
                      max_tokens: Optional[int] = None) -> AsyncIterator[ModelResponse]:
        """Generate responses from the model.
        
        Args:
            model: Name of the Ollama model to use
            messages: List of conversation messages
            stream: Whether to stream the response
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            
        Yields:
            ModelResponse objects containing generated content
        """
        # Convert messages to Ollama format
        formatted_messages = []
        for msg in messages:
            content = msg.content
            # Handle images if present
            if msg.images:
                content = f"{content}\n"
                for img in msg.images:
                    with open(img, 'rb') as f:
                        img_data = f.read()
                        content += f"\n<img>{img_data}</img>"
            
            formatted_messages.append({
                "role": msg.role,
                "content": content
            })
        
        # Prepare the request
        url = f"{self.base_url}/chat"
        data = {
            "model": model,
            "messages": formatted_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            data["options"]["num_predict"] = max_tokens
            
        # Make the request
        async with self._client.stream("POST", url, json=data) as response:
            response.raise_for_status()
            current_content = ""
            
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                    
                try:
                    chunk = json.loads(line)
                    if "error" in chunk:
                        raise ValueError(f"Ollama error: {chunk['error']}")
                        
                    # Extract content
                    if "message" in chunk:
                        content = chunk["message"].get("content", "")
                    else:
                        content = chunk.get("content", "")
                        
                    current_content += content
                    
                    # Check for tool calls in the response
                    tool_calls = None
                    if "tool_calls" in chunk:
                        tool_calls = chunk["tool_calls"]
                    
                    # Yield the response
                    yield ModelResponse(
                        content=current_content,
                        tool_calls=tool_calls,
                        done=chunk.get("done", False)
                    )
                    
                except json.JSONDecodeError:
                    continue
                    
    async def get_model_list(self) -> List[str]:
        """Get list of available models from Ollama."""
        url = f"{self.base_url}/tags"
        async with self._client as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
