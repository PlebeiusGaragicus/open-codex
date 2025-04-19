"""Tests for tool handling."""
import pytest
from src.core.tools import ToolCall, ToolRegistry, registry
from src.core.sandbox import ExecResult


def test_tool_call_from_response():
    """Test extracting tool calls from response."""
    response = {
        'message': {
            'tool_calls': [{
                'type': 'function',
                'function': {
                    'name': 'shell',
                    'arguments': '{"command": "echo test"}'
                }
            }]
        }
    }
    
    tools = ToolCall.from_response(response)
    assert tools is not None
    assert len(tools) == 1
    assert tools[0].name == 'shell'
    assert tools[0].arguments == {'command': 'echo test'}


def test_tool_call_from_response_no_tools():
    """Test handling response with no tools."""
    response = {
        'message': {
            'content': 'test'
        }
    }
    
    assert ToolCall.from_response(response) is None


def test_tool_call_from_response_invalid_json():
    """Test handling invalid JSON arguments."""
    response = {
        'message': {
            'tool_calls': [{
                'type': 'function',
                'function': {
                    'name': 'shell',
                    'arguments': 'invalid json'
                }
            }]
        }
    }
    
    tools = ToolCall.from_response(response)
    assert tools is not None
    assert len(tools) == 1
    assert tools[0].name == 'shell'
    assert tools[0].arguments == {}


@pytest.mark.asyncio
async def test_tool_registry():
    """Test tool registry."""
    registry = ToolRegistry()
    
    @registry.register('test')
    async def test_tool(arg: str):
        return f"test: {arg}"
        
    tool = ToolCall(name='test', arguments={'arg': 'value'})
    result = await registry.execute(tool)
    assert result == 'test: value'
    
    with pytest.raises(ValueError):
        await registry.execute(ToolCall(name='unknown', arguments={}))


@pytest.mark.asyncio
async def test_shell_command():
    """Test shell command tool."""
    tool = ToolCall(name='shell', arguments={'command': 'echo test'})
    result = await registry.execute(tool)
    assert isinstance(result, ExecResult)
    assert result.stdout.strip() == 'test'
    assert not result.stderr
    assert result.code == 0
    assert not result.error


@pytest.mark.asyncio
async def test_apply_patch():
    """Test apply patch tool."""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        test_py = os.path.join(tmpdir, "test.py")
        with open(test_py, "w") as f:
            f.write("a\nb\nc\n")
            
        # Create patch
        patch_text = """*** Begin Patch
*** Update File: test.py
@@ -1,3 +1,3 @@
a
-b
+c
*** End Patch"""
        
        # Apply patch
        tool = ToolCall(name="apply_patch", arguments={"patch_text": patch_text})
        
        # Change to temp dir
        cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = await registry.execute(tool)
            assert result == "Done!"
            
            # Verify result
            with open(test_py) as f:
                assert f.read() == "a\nc\nc\n"
        finally:
            os.chdir(cwd)
