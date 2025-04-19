"""Tests for patch module."""
import os
import tempfile
from typing import Dict

import pytest

from src.core.patch import (
    ActionType,
    Chunk,
    Commit,
    DiffError,
    FileChange,
    Patch,
    PatchAction,
    Parser,
    find_context,
    identify_files_added,
    identify_files_needed,
    patch_to_commit,
    process_patch,
    text_to_patch,
)


def test_find_context():
    """Test finding context lines."""
    lines = ["a", "b", "c", "d", "e"]
    context = ["b", "c"]
    start, end = find_context(lines, context, 0, False)
    assert start == 1
    assert end == 3

    # Test EOF
    context = ["d", "e"]
    start, end = find_context(lines, context, 0, True)
    assert start == 3
    assert end == 5

    # Test not found
    context = ["x", "y"]
    with pytest.raises(DiffError):
        find_context(lines, context, 0, False)


def test_identify_files():
    """Test identifying files in patch."""
    text = """*** Begin Patch
*** Update File: test1.py
@@ -1,3 +1,3 @@
a
-b
+c
*** Delete File: test2.py
*** Add File: test3.py
new content
*** End Patch"""

    needed = identify_files_needed(text)
    assert set(needed) == {"test1.py", "test2.py"}

    added = identify_files_added(text)
    assert added == ["test3.py"]


def test_text_to_patch():
    """Test converting text to patch."""
    text = """*** Begin Patch
*** Update File: test.py
@@ -1,3 +1,3 @@
a
-b
+c
*** End Patch"""

    orig = {"test.py": "a\nb\nc\n"}
    patch, fuzz = text_to_patch(text, orig)
    assert isinstance(patch, Patch)
    assert fuzz == 0

    action = patch.actions["test.py"]
    assert action.type == ActionType.UPDATE
    assert len(action.chunks) == 1
    assert action.chunks[0].del_lines == ["a", "b"]
    assert action.chunks[0].ins_lines == ["a", "c"]


def test_patch_to_commit():
    """Test converting patch to commit."""
    patch = Patch(actions={
        "test.py": PatchAction(
            type=ActionType.UPDATE,
            chunks=[
                Chunk(
                    orig_index=0,
                    del_lines=["a", "b"],
                    ins_lines=["a", "c"]
                )
            ]
        )
    })
    orig = {"test.py": "a\nb\nc\n"}
    commit = patch_to_commit(patch, orig)

    assert isinstance(commit, Commit)
    change = commit.changes["test.py"]
    assert change.type == ActionType.UPDATE
    assert change.old_content == "a\nb\nc\n"
    assert change.new_content == "a\nc\nc\n"


def test_process_patch():
    """Test processing a patch."""
    files: Dict[str, str] = {}

    def open_fn(path: str) -> str:
        if path not in files:
            raise FileNotFoundError(path)
        return files[path]

    def write_fn(path: str, content: str) -> None:
        files[path] = content

    def remove_fn(path: str) -> None:
        del files[path]

    # Initial content
    files["test.py"] = "a\nb\nc\n"

    # Apply patch
    text = """*** Begin Patch
*** Update File: test.py
@@ -1,3 +1,3 @@
a
-b
+c
*** End Patch"""

    result = process_patch(text, open_fn, write_fn, remove_fn)
    assert result == "Done!"
    assert files["test.py"] == "a\nc\nc\n"


def test_process_patch_with_real_files():
    """Test processing a patch with real files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_py = os.path.join(tmpdir, "test.py")
        with open(test_py, "w") as f:
            f.write("a\nb\nc\n")

        # Apply patch
        text = """*** Begin Patch
*** Update File: test.py
@@ -1,3 +1,3 @@
a
-b
+c
*** End Patch"""

        def open_fn(path: str) -> str:
            with open(os.path.join(tmpdir, path)) as f:
                return f.read()

        def write_fn(path: str, content: str) -> None:
            with open(os.path.join(tmpdir, path), "w") as f:
                f.write(content)

        def remove_fn(path: str) -> None:
            os.remove(os.path.join(tmpdir, path))

        result = process_patch(text, open_fn, write_fn, remove_fn)
        assert result == "Done!"

        # Verify result
        with open(test_py) as f:
            assert f.read() == "a\nc\nc\n"
