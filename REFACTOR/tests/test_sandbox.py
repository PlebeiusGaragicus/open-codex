"""Tests for sandbox functionality."""
import os
import platform
import pytest
from src.core.sandbox import Sandbox, SandboxType, ExecResult

@pytest.mark.asyncio
async def test_sandbox_echo():
    """Test basic command execution."""
    sandbox = Sandbox()
    result = await sandbox.exec("echo 'hello world'")
    assert result.code == 0
    assert "hello world" in result.stdout
    assert not result.stderr

@pytest.mark.asyncio
async def test_sandbox_write_tmp():
    """Test writing to /tmp is allowed."""
    sandbox = Sandbox()
    result = await sandbox.exec("echo 'test' > /tmp/test.txt")
    assert result.code == 0
    assert not result.stderr
    
    # Clean up
    if os.path.exists("/tmp/test.txt"):
        os.unlink("/tmp/test.txt")

@pytest.mark.asyncio
async def test_sandbox_write_protected():
    """Test writing to protected paths is blocked."""
    if platform.system() != "Darwin":
        pytest.skip("Sandbox restrictions only work on macOS")
        
    sandbox = Sandbox()
    result = await sandbox.exec("touch /etc/test.txt")
    assert result.code != 0
    assert "Operation not permitted" in result.stderr

@pytest.mark.asyncio
async def test_sandbox_writable_paths():
    """Test writing to explicitly allowed paths."""
    sandbox = Sandbox(writable_paths=["/tmp/test_dir"])
    
    # Create test directory
    os.makedirs("/tmp/test_dir", exist_ok=True)
    
    result = await sandbox.exec("echo 'test' > /tmp/test_dir/test.txt")
    assert result.code == 0
    assert not result.stderr
    
    # Clean up
    if os.path.exists("/tmp/test_dir/test.txt"):
        os.unlink("/tmp/test_dir/test.txt")
    os.rmdir("/tmp/test_dir")

@pytest.mark.asyncio
async def test_sandbox_invalid_command():
    """Test handling of invalid commands."""
    sandbox = Sandbox()
    result = await sandbox.exec("nonexistentcommand")
    assert result.code != 0
    assert "not found" in result.stderr.lower()

@pytest.mark.asyncio
async def test_sandbox_with_env():
    """Test command execution with environment variables."""
    sandbox = Sandbox()
    env = {"TEST_VAR": "test_value"}
    result = await sandbox.exec("echo $TEST_VAR", env=env)
    assert result.code == 0
    assert "test_value" in result.stdout

@pytest.mark.asyncio
async def test_sandbox_with_cwd():
    """Test command execution with working directory."""
    sandbox = Sandbox()
    result = await sandbox.exec("pwd", cwd="/tmp")
    assert result.code == 0
    assert "/tmp" in result.stdout
