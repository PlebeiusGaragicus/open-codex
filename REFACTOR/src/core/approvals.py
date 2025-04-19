"""Approval modes and policies for command execution."""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Union


class ApprovalMode(Enum):
    """Approval modes for commands and edits."""
    SUGGEST = auto()  # Ask for approval for everything
    AUTO_EDIT = auto()  # Auto-approve edits, ask for commands
    FULL_AUTO = auto()  # Auto-approve everything (in sandbox)


@dataclass
class ApplyPatchCommand:
    """Command to apply a patch to files."""
    filename: str
    patch: str


@dataclass
class CommandReview:
    """Review decision for a command."""
    approved: bool
    custom_message: Optional[str] = None


class ApprovalPolicy:
    """Policy for approving commands and edits."""

    def __init__(self, mode: ApprovalMode = ApprovalMode.SUGGEST):
        """Initialize approval policy.

        Args:
            mode: Approval mode to use
        """
        self.mode = mode

    def should_auto_approve_edit(self) -> bool:
        """Check if edits should be auto-approved.

        Returns:
            True if edits should be auto-approved
        """
        return self.mode in (ApprovalMode.AUTO_EDIT, ApprovalMode.FULL_AUTO)

    def should_auto_approve_command(self) -> bool:
        """Check if commands should be auto-approved.

        Returns:
            True if commands should be auto-approved
        """
        return self.mode == ApprovalMode.FULL_AUTO

    def get_command_approval(
        self,
        command: List[str],
        patch: Optional[ApplyPatchCommand] = None
    ) -> CommandReview:
        """Get approval for a command.

        Args:
            command: Command to execute
            patch: Optional patch to apply

        Returns:
            Review decision
        """
        # Auto-approve if policy allows
        if patch and self.should_auto_approve_edit():
            return CommandReview(approved=True)
        if not patch and self.should_auto_approve_command():
            return CommandReview(approved=True)

        # Otherwise require explicit approval
        return CommandReview(approved=False)
