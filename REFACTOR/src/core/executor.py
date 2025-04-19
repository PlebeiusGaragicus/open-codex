"""
Command execution and tool handling for the LLM.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, AsyncIterator
from rich.console import Console
from .sandbox import Sandbox, ExecResult
from .llm import Message, ModelResponse, OllamaClient
from .tools import ToolCall, registry
from .approvals import ApprovalPolicy, ApplyPatchCommand, CommandReview

console = Console()

@dataclass
class ExecutionContext:
    """Context for command execution."""
    cwd: str
    env: Dict[str, str]
    writable_paths: List[str]
    approval_policy: Optional[ApprovalPolicy] = None

class CommandExecutor:
    """Handles command execution and tool calls from the LLM."""

    def __init__(
        self,
        context: Optional[ExecutionContext] = None,
        approval_policy: Optional[ApprovalPolicy] = None,
        model: str = "qwen2.5-coder",
        base_url: str = "http://localhost:11434/api"
    ):
        """Initialize executor.

        Args:
            context: Optional execution context
            approval_policy: Optional approval policy
            model: Name of the Ollama model to use
            base_url: Base URL for the Ollama API
        """
        self.model = model
        self.base_url = base_url
        self.context = context or ExecutionContext(
            cwd=str(Path().resolve()),
            env=os.environ.copy(),
            writable_paths=[str(Path().resolve())],
            approval_policy=approval_policy or ApprovalPolicy()
        )
        self.sandbox = Sandbox(writable_paths=self.context.writable_paths)
        self.client = OllamaClient()

    async def execute_command(self, command: str) -> ExecResult:
        """Execute a command in the sandbox.
        
        Args:
            command: Command to execute
            
        Returns:
            ExecResult containing command output
        """
        return await self.sandbox.exec(
            command,
            cwd=self.context.cwd,
            env=self.context.env
        )
        
    def _parse_tool_calls(self, response: ModelResponse) -> Optional[List[ToolCall]]:
        """Parse tool calls from response.
        
        Args:
            response: Response from LLM
            
        Returns:
            List of tool calls if present, None otherwise
        """
        # Convert ModelResponse to dict format expected by ToolCall
        response_dict = {
            'message': {
                'content': response.content,
                'tool_calls': response.tool_calls
            }
        }
        return ToolCall.from_response(response_dict)
        
    async def process_message(self, message: str) -> AsyncIterator[Union[str, ExecResult]]:
        """Process a message and execute any commands.
        
        Args:
            message: User message to process
            
        Yields:
            Either string responses or ExecResults from command execution
        """
        async with OllamaClient(base_url=self.base_url) as client:
            messages = [Message(role="user", content=message)]
            
            async for response in client.generate(self.model, messages):
                # Check for tool calls
                tool_calls = self._parse_tool_calls(response)
                
                if tool_calls:
                    for tool in tool_calls:
                        try:
                            # Execute tool
                            result = await registry.execute(tool)
                            
                            if isinstance(result, ExecResult):
                                yield result
                            
                            # Add result to conversation
                            messages.append(Message(
                                role="assistant",
                                content=f"Tool {tool.name} output: {result}"
                            ))
                        except Exception as e:
                            messages.append(Message(
                                role="assistant",
                                content=f"Error executing tool {tool.name}: {e}"
                            ))
                            
                # Always yield the response content
                if response.content:
                    yield response.content
                    
                if response.done:
                    break
                    
    def update_context(self, 
                      cwd: Optional[str] = None,
                      env: Optional[Dict[str, str]] = None,
                      writable_paths: Optional[List[str]] = None):
        """Update the execution context.
        
        Args:
            cwd: New working directory
            env: New environment variables
            writable_paths: New writable paths
        """
        if cwd:
            self.context.cwd = cwd
        if env:
            self.context.env.update(env)
        if writable_paths:
            self.context.writable_paths = writable_paths
            self.sandbox = Sandbox(writable_paths=writable_paths)
