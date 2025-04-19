"""File patching utilities."""
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable


class ActionType(Enum):
    """Type of patch action."""
    ADD = "add"
    DELETE = "delete"
    UPDATE = "update"


@dataclass
class FileChange:
    """Change to a file."""
    type: ActionType
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    move_path: Optional[str] = None


@dataclass
class Commit:
    """A set of file changes."""
    changes: Dict[str, FileChange]


@dataclass
class Chunk:
    """A chunk of a patch."""
    orig_index: int
    del_lines: List[str]
    ins_lines: List[str]


@dataclass
class PatchAction:
    """Action to take on a file."""
    type: ActionType
    new_file: Optional[str] = None
    chunks: List[Chunk] = None
    move_path: Optional[str] = None

    def __post_init__(self):
        """Initialize chunks if None."""
        if self.chunks is None:
            self.chunks = []


@dataclass
class Patch:
    """A collection of patch actions."""
    actions: Dict[str, PatchAction]


class DiffError(Exception):
    """Error during patch application."""
    pass


class Parser:
    """Parser for patch text."""

    def __init__(self, current_files: Dict[str, str], lines: List[str]):
        """Initialize parser.
        
        Args:
            current_files: Map of file paths to their current contents
            lines: Lines of the patch
        """
        self.current_files = current_files
        self.lines = lines
        self.index = 0
        self.patch = Patch(actions={})
        self.fuzz = 0

    def is_done(self, prefixes: Optional[List[str]] = None) -> bool:
        """Check if parsing is done.
        
        Args:
            prefixes: Optional list of prefixes to check for
            
        Returns:
            True if done
        """
        if self.index >= len(self.lines):
            return True
        if prefixes and any(self.lines[self.index].startswith(p) for p in prefixes):
            return True
        return False

    def startswith(self, prefix: str) -> bool:
        """Check if current line starts with prefix.
        
        Args:
            prefix: Prefix to check for
            
        Returns:
            True if line starts with prefix
        """
        if self.index >= len(self.lines):
            return False
        return self.lines[self.index].startswith(prefix)

    def read_str(self, prefix: str = "", return_everything: bool = False) -> str:
        """Read a string from current line.
        
        Args:
            prefix: Prefix to strip
            return_everything: Return entire line
            
        Returns:
            Line content
            
        Raises:
            DiffError: If index out of bounds
        """
        if self.index >= len(self.lines):
            raise DiffError(f"Index: {self.index} >= {len(self.lines)}")
        if self.lines[self.index].startswith(prefix):
            text = (self.lines[self.index] if return_everything 
                   else self.lines[self.index][len(prefix):])
            self.index += 1
            return text
        return ""

    def parse(self) -> None:
        """Parse patch text."""
        # Skip begin patch line
        if self.startswith("*** Begin Patch"):
            self.index += 1
            
        while not self.is_done(["*** End Patch"]):
            path = self.read_str("*** Update File: ")
            if path:
                if path in self.patch.actions:
                    raise DiffError(f"Update File Error: Duplicate Path: {path}")
                move_to = self.read_str("*** Move to: ")
                if path not in self.current_files:
                    raise DiffError(f"Update File Error: Missing File: {path}")
                text = self.current_files[path]
                action = self.parse_update_file(text)
                if move_to:
                    action.move_path = move_to
                self.patch.actions[path] = action
                continue

            path = self.read_str("*** Add File: ")
            if path:
                if path in self.patch.actions:
                    raise DiffError(f"Add File Error: Duplicate Path: {path}")
                action = self.parse_add_file()
                self.patch.actions[path] = action
                continue

            path = self.read_str("*** Delete File: ")
            if path:
                if path in self.patch.actions:
                    raise DiffError(f"Delete File Error: Duplicate Path: {path}")
                if path not in self.current_files:
                    raise DiffError(f"Delete File Error: Missing File: {path}")
                self.patch.actions[path] = PatchAction(type=ActionType.DELETE)
                continue

            raise DiffError(f"Parse Error: {self.lines[self.index]}")

    def parse_update_file(self, text: str) -> PatchAction:
        """Parse update file action.
        
        Args:
            text: Current file content
            
        Returns:
            Patch action
            
        Raises:
            DiffError: On parse error
        """
        action = PatchAction(type=ActionType.UPDATE)
        lines = text.splitlines()

        while not self.is_done(["*** "]):
            if self.startswith("@@ "):
                # Skip chunk header
                self.index += 1

                chunk = Chunk(orig_index=0, del_lines=[], ins_lines=[])
                action.chunks.append(chunk)

                # Parse chunk content
                while not self.is_done(["@@ ", "*** "]):
                    line = self.read_str("", return_everything=True)
                    if not line:
                        break
                    if line.startswith("-"):
                        chunk.del_lines.append(line[1:])
                    elif line.startswith("+"):
                        chunk.ins_lines.append(line[1:])
                    elif not line.startswith("@@ "):
                        chunk.del_lines.append(line)
                        chunk.ins_lines.append(line)

        return action

    def parse_add_file(self) -> PatchAction:
        """Parse add file action.
        
        Returns:
            Patch action
        """
        action = PatchAction(type=ActionType.ADD, new_file="")
        lines = []
        while not self.is_done(["*** "]):
            line = self.read_str()
            if line:
                lines.append(line)
        action.new_file = "\n".join(lines)
        return action


def find_context(lines: List[str], context: List[str], start: int, eof: bool) -> Tuple[int, int]:
    """Find context lines in file.
    
    Args:
        lines: File lines
        context: Context lines to find
        start: Start line
        eof: Allow end of file
        
    Returns:
        Tuple of (start, end) line numbers
        
    Raises:
        DiffError: If context not found
    """
    if not context:
        return start, start

    for i in range(start, len(lines)):
        match = True
        for j, ctx_line in enumerate(context):
            if i + j >= len(lines):
                if eof and j == len(context) - 1:
                    return i, i + j
                match = False
                break
            if lines[i + j] != ctx_line:
                match = False
                break
        if match:
            return i, i + len(context)

    raise DiffError("Context not found")


def text_to_patch(text: str, orig: Dict[str, str]) -> Tuple[Patch, int]:
    """Convert patch text to Patch object.
    
    Args:
        text: Patch text
        orig: Map of file paths to contents
        
    Returns:
        Tuple of (patch, fuzz)
        
    Raises:
        DiffError: On parse error
    """
    if not text.startswith("*** Begin Patch"):
        raise DiffError("Patch must start with *** Begin Patch")

    lines = text.splitlines()
    parser = Parser(orig, lines)
    parser.parse()
    return parser.patch, parser.fuzz


def identify_files_needed(text: str) -> List[str]:
    """Get list of files needed by patch.
    
    Args:
        text: Patch text
        
    Returns:
        List of file paths
    """
    files = []
    for line in text.splitlines():
        if line.startswith("*** Update File: "):
            files.append(line[len("*** Update File: "):])
        elif line.startswith("*** Delete File: "):
            files.append(line[len("*** Delete File: "):])
    return files


def identify_files_added(text: str) -> List[str]:
    """Get list of files to be added by patch.
    
    Args:
        text: Patch text
        
    Returns:
        List of file paths
    """
    files = []
    for line in text.splitlines():
        if line.startswith("*** Add File: "):
            files.append(line[len("*** Add File: "):])
    return files


def _get_updated_file(text: str, action: PatchAction, path: str) -> str:
    """Apply patch chunks to file content.
    
    Args:
        text: Original file content
        action: Patch action
        path: File path
        
    Returns:
        Updated file content with proper line endings
        
    Raises:
        DiffError: If patch cannot be applied
    """
    """Apply patch chunks to file content.
    
    Args:
        text: Original file content
        action: Patch action
        path: File path
        
    Returns:
        Updated file content
        
    Raises:
        DiffError: If patch cannot be applied
    """
    if action.type != ActionType.UPDATE:
        raise DiffError(f"Invalid action type for {path}: {action.type}")

    lines = text.splitlines()
    new_lines = lines.copy()

    for chunk in action.chunks:
        # Find chunk location
        try:
            start, end = find_context(lines, chunk.del_lines, 0, False)
        except DiffError:
            raise DiffError(f"Failed to apply chunk in {path}")

        # Apply chunk
        new_lines[start:end] = chunk.ins_lines

    # Preserve original line endings
    if text.endswith("\n"):
        return "\n".join(new_lines) + "\n"
    return "\n".join(new_lines)


def patch_to_commit(patch: Patch, orig: Dict[str, str]) -> Commit:
    """Convert Patch to Commit.
    
    Args:
        patch: Patch object
        orig: Map of file paths to contents
        
    Returns:
        Commit object
    """
    commit = Commit(changes={})
    for path, action in patch.actions.items():
        if action.type == ActionType.DELETE:
            commit.changes[path] = FileChange(
                type=ActionType.DELETE,
                old_content=orig[path]
            )
        elif action.type == ActionType.ADD:
            commit.changes[path] = FileChange(
                type=ActionType.ADD,
                new_content=action.new_file
            )
        elif action.type == ActionType.UPDATE:
            new_content = _get_updated_file(orig[path], action, path)
            commit.changes[path] = FileChange(
                type=ActionType.UPDATE,
                old_content=orig[path],
                new_content=new_content,
                move_path=action.move_path
            )
    return commit


def process_patch(text: str,
                 open_fn: Callable[[str], str],
                 write_fn: Callable[[str, str], None],
                 remove_fn: Callable[[str], None]) -> str:
    """Process a patch.
    
    Args:
        text: Patch text
        open_fn: Function to open files
        write_fn: Function to write files
        remove_fn: Function to remove files
        
    Returns:
        Status message
        
    Raises:
        DiffError: If patch cannot be applied
    """
    if not text.startswith("*** Begin Patch"):
        raise DiffError("Patch must start with *** Begin Patch")

    paths = identify_files_needed(text)
    orig = {p: open_fn(p) for p in paths}
    patch, _ = text_to_patch(text, orig)
    commit = patch_to_commit(patch, orig)

    for path, change in commit.changes.items():
        if change.type == ActionType.DELETE:
            remove_fn(path)
        elif change.type == ActionType.ADD:
            write_fn(path, change.new_content or "")
        elif change.type == ActionType.UPDATE:
            if change.move_path:
                write_fn(change.move_path, change.new_content or "")
                remove_fn(path)
            else:
                write_fn(path, change.new_content or "")

    return "Done!"
