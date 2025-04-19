"""Tool call handling and definitions."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
import json
from .sandbox import ExecResult
from .patch import process_patch


@dataclass
class ToolCall:
    """A tool call from the LLM."""
    name: str
    arguments: Dict[str, Any]
    
    @staticmethod
    def from_response(response: Dict[str, Any]) -> Optional[List['ToolCall']]:
        """Extract tool calls from an LLM response.
        
        Args:
            response: Response from LLM
            
        Returns:
            List of tool calls if present, None otherwise
        """
        if not response.get('message', {}).get('tool_calls'):
            return None
            
        tool_calls = []
        for call in response['message']['tool_calls']:
            if call.get('type') != 'function':
                continue
                
            function = call.get('function', {})
            if not function.get('name'):
                continue
                
            try:
                arguments = json.loads(function.get('arguments', '{}'))
            except json.JSONDecodeError:
                arguments = {}
                
            tool_calls.append(ToolCall(
                name=function['name'],
                arguments=arguments
            ))
            
        return tool_calls if tool_calls else None


class ToolRegistry:
    """Registry of available tools."""
    
    def __init__(self):
        """Initialize registry."""
        self._tools = {}
        
    def register(self, name: str):
        """Register a tool.
        
        Args:
            name: Name of the tool
        """
        def decorator(func):
            self._tools[name] = func
            return func
        return decorator
        
    async def execute(self, tool: ToolCall) -> Any:
        """Execute a tool call.
        
        Args:
            tool: Tool call to execute
            
        Returns:
            Result of tool execution
            
        Raises:
            ValueError: If tool not found
        """
        if tool.name not in self._tools:
            raise ValueError(f"Unknown tool: {tool.name}")
            
        return await self._tools[tool.name](**tool.arguments)


# Global registry
registry = ToolRegistry()


@registry.register('shell')
async def shell_command(command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> ExecResult:
    # If the command is a cd command, handle it specially
    if command.strip().startswith('cd '):
        target_dir = command.strip()[3:].strip()
        if not os.path.exists(target_dir):
            return ExecResult(
                stdout='',
                stderr=f'cd: no such file or directory: {target_dir}\n',
                code=1
            )
        # Update the cwd for this and future commands
        cwd = target_dir
    """Execute a shell command in the sandbox.
    
    Args:
        command: Command to execute
        cwd: Optional working directory
        env: Optional environment variables
        
    Returns:
        Execution result
    """
    from .sandbox import Sandbox
    sandbox = Sandbox()
    return await sandbox.exec(command, cwd=cwd, env=env)


@registry.register('search')
async def search_files(query: str, path: Optional[str] = None) -> List[str]:
    """Search for files.
    
    Args:
        query: Search query
        path: Optional path to search in
        
    Returns:
        List of matching files
    """
    return []


@registry.register('read')
async def read_file(path: str) -> str:
    """Read a file.
    
    Args:
        path: Path to file
        
    Returns:
        File contents
    """
    with open(path) as f:
        return f.read()


@registry.register('apply_patch')
async def apply_patch(patch_text: str) -> str:
    """Apply a patch to files.
    
    Args:
        patch_text: Patch text
        
    Returns:
        Status message
    """
    def open_fn(path: str) -> str:
        with open(path) as f:
            return f.read()
            
    def write_fn(path: str, content: str) -> None:
        with open(path, 'w') as f:
            f.write(content)
            
    def remove_fn(path: str) -> None:
        import os
        os.remove(path)
        
    return process_patch(patch_text, open_fn, write_fn, remove_fn)
