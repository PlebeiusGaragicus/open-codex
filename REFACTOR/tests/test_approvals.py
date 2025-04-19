"""Tests for approval system."""
import pytest
from src.core.approvals import ApprovalMode, ApprovalPolicy, ApplyPatchCommand, CommandReview


def test_approval_mode_suggest():
    """Test suggest approval mode."""
    policy = ApprovalPolicy(mode=ApprovalMode.SUGGEST)
    assert not policy.should_auto_approve_edit()
    assert not policy.should_auto_approve_command()


def test_approval_mode_auto_edit():
    """Test auto-edit approval mode."""
    policy = ApprovalPolicy(mode=ApprovalMode.AUTO_EDIT)
    assert policy.should_auto_approve_edit()
    assert not policy.should_auto_approve_command()


def test_approval_mode_full_auto():
    """Test full-auto approval mode."""
    policy = ApprovalPolicy(mode=ApprovalMode.FULL_AUTO)
    assert policy.should_auto_approve_edit()
    assert policy.should_auto_approve_command()


def test_command_approval_suggest():
    """Test command approval in suggest mode."""
    policy = ApprovalPolicy(mode=ApprovalMode.SUGGEST)
    
    # Test command approval
    review = policy.get_command_approval(command=["echo", "test"])
    assert not review.approved
    assert not review.custom_message
    
    # Test patch approval
    patch = ApplyPatchCommand(filename="test.py", patch="test patch")
    review = policy.get_command_approval(command=["apply_patch"], patch=patch)
    assert not review.approved
    assert not review.custom_message


def test_command_approval_auto_edit():
    """Test command approval in auto-edit mode."""
    policy = ApprovalPolicy(mode=ApprovalMode.AUTO_EDIT)
    
    # Commands still need approval
    review = policy.get_command_approval(command=["echo", "test"])
    assert not review.approved
    
    # Patches are auto-approved
    patch = ApplyPatchCommand(filename="test.py", patch="test patch")
    review = policy.get_command_approval(command=["apply_patch"], patch=patch)
    assert review.approved


def test_command_approval_full_auto():
    """Test command approval in full-auto mode."""
    policy = ApprovalPolicy(mode=ApprovalMode.FULL_AUTO)
    
    # Both commands and patches are auto-approved
    review = policy.get_command_approval(command=["echo", "test"])
    assert review.approved
    
    patch = ApplyPatchCommand(filename="test.py", patch="test patch")
    review = policy.get_command_approval(command=["apply_patch"], patch=patch)
    assert review.approved
