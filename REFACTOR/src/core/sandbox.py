"""
Command execution sandbox using macOS seatbelt for security.
"""

import asyncio
import enum
import os
import platform
import shlex
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
from rich.console import Console

console = Console()

class SandboxType(enum.Enum):
    """Type of sandbox to use."""
    NONE = "none"
    MACOS_SEATBELT = "macos_seatbelt"

@dataclass
class ExecResult:
    """Result of executing a command."""
    stdout: str
    stderr: str
    code: int
    error: Optional[str] = None

class Sandbox:
    """Command execution sandbox."""
    
    def __init__(self, writable_paths: List[str] = None):
        """Initialize the sandbox.
        
        Args:
            writable_paths: List of paths that should be writable within the sandbox
        """
        self.writable_paths = writable_paths or []
        self.sandbox_type = self._get_sandbox_type()
        
    def _get_sandbox_type(self) -> SandboxType:
        """Determine which sandbox implementation to use."""
        if platform.system() == "Darwin":
            return SandboxType.MACOS_SEATBELT
        console.print("[yellow]Warning: No sandbox available for this platform. Running without sandbox.[/yellow]")
        return SandboxType.NONE
        
    def _create_seatbelt_profile(self, writable_paths: List[str]) -> str:
        """Create a seatbelt sandbox profile.
        
        Args:
            writable_paths: List of paths that should be writable
            
        Returns:
            Path to the created profile file
        """
        profile = """
(version 1)
(allow default)
(deny file-write*)
(allow file-write*
    (subpath "/private/tmp")
    (subpath "/private/var/tmp")
    (literal "/dev/null")
    (literal "/dev/zero")
"""
        
        # Add writable paths
        for path in writable_paths:
            abs_path = str(Path(path).resolve())
            profile += f'    (subpath "{abs_path}")\n'
            
        profile += ")\n"
        
        # Write profile to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sb', delete=False) as f:
            f.write(profile)
            return f.name
            
    async def exec(self, 
                   command: str,
                   cwd: Optional[str] = None,
                   env: Optional[Dict[str, str]] = None) -> ExecResult:
        """Execute a command in the sandbox.
        
        Args:
            command: Command to execute
            cwd: Working directory for the command
            env: Environment variables for the command
            
        Returns:
            ExecResult containing stdout, stderr, and exit code
        """
        try:
            if self.sandbox_type == SandboxType.MACOS_SEATBELT:
                # Create sandbox profile
                profile_path = self._create_seatbelt_profile(self.writable_paths)
                
                # Wrap command in sandbox-exec
                sandbox_cmd = [
                    "sandbox-exec",
                    "-f", profile_path,
                    "/bin/sh", "-c", command
                ]
                
                # Run command
                proc = await asyncio.create_subprocess_exec(
                    *sandbox_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env
                )
                
                # Get output
                stdout, stderr = await proc.communicate()
                
                # Clean up profile
                os.unlink(profile_path)
                
                return ExecResult(
                    stdout=stdout.decode(),
                    stderr=stderr.decode(),
                    code=proc.returncode
                )
                
            else:
                # No sandbox, run directly
                proc = await asyncio.create_subprocess_exec(
                    "/bin/sh", "-c", command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env
                )
                
                stdout, stderr = await proc.communicate()
                return ExecResult(
                    stdout=stdout.decode(),
                    stderr=stderr.decode(),
                    code=proc.returncode
                )
                
        except Exception as e:
            return ExecResult(
                stdout="",
                stderr=str(e),
                code=1,
                error=str(e)
            )
