"""Tests for command execution and tool handling."""
import json
import pytest
import httpx
from src.core.executor import CommandExecutor, ExecutionContext, ToolCall
from src.core.llm import Message, ModelResponse

@pytest.mark.asyncio
async def test_execute_command():
    """Test executing a command."""
    executor = CommandExecutor()
    result = await executor.execute_command("echo test")
    assert result.stdout.strip() == "test"
    assert not result.stderr
    assert result.code == 0

@pytest.mark.asyncio
async def test_execute_command_with_context():
    """Test executing a command with context."""
    context = ExecutionContext(
        cwd="/tmp",
        env={"TEST": "value"},
        writable_paths=["/tmp"],
    )
    executor = CommandExecutor(context=context)
    result = await executor.execute_command("pwd")
    assert "/tmp" in result.stdout
    
    # Test env
    result = await executor.execute_command("echo $TEST")
    assert "value" in result.stdout

@pytest.mark.asyncio
async def test_process_message_shell_command(respx_mock):
    """Test processing a message with shell command."""
    # Mock Ollama API response
    api_url = "http://localhost:11434/api/chat"
    mock_response = {
        "message": {
            "content": "Let me help you with that.",
            "tool_calls": [{
                "type": "function",
                "function": {
                    "name": "shell",
                    "arguments": json.dumps({
                        "command": "echo 'Hello from shell'"
                    })
                }
            }]
        },
        "done": True
    }
    
    respx_mock.post(api_url).mock(return_value=httpx.Response(
        200,
        content=json.dumps(mock_response)
    ))
    
    executor = CommandExecutor()
    responses = []
    async for response in executor.process_message("Run a test command"):
        responses.append(response)
        
    # Should have one response - the LLM's response
    # The command execution is handled internally
    assert len(responses) == 1
    assert responses[0] == "Let me help you with that."

@pytest.mark.asyncio
async def test_update_context():
    """Test updating execution context."""
    executor = CommandExecutor()
    
    # Update context
    executor.update_context(
        cwd="/tmp",
        env={"TEST": "value"},
        writable_paths=["/tmp"],
    )
    
    # Verify changes
    assert executor.context.cwd == "/tmp"
    assert executor.context.env["TEST"] == "value"
    assert "/tmp" in executor.context.writable_paths
    
    # Test command with new context
    result = await executor.execute_command("pwd")
    assert "/tmp" in result.stdout
