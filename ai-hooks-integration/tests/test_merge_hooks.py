#!/usr/bin/env python3
"""Tests for hook merging logic."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from merge_hooks import TOOL_CONFIG, has_hook, load_json, save_json


class TestToolConfig(unittest.TestCase):
    """Test tool configuration."""

    def test_all_tools_configured(self):
        """All supported tools should be configured."""
        expected = {"claude", "gemini", "cursor", "opencode"}
        self.assertEqual(set(TOOL_CONFIG.keys()), expected)

    def test_claude_config(self):
        """Claude config should have correct structure."""
        cfg = TOOL_CONFIG["claude"]
        self.assertEqual(cfg["hook_key"], "PreToolUse")
        self.assertEqual(cfg["default_matcher"], "Bash")
        self.assertTrue(cfg["nested"])

    def test_gemini_config(self):
        """Gemini config should have correct structure."""
        cfg = TOOL_CONFIG["gemini"]
        self.assertEqual(cfg["hook_key"], "BeforeTool")
        self.assertEqual(cfg["default_matcher"], "run_shell_command")
        self.assertTrue(cfg["nested"])

    def test_cursor_config(self):
        """Cursor config should have flat structure."""
        cfg = TOOL_CONFIG["cursor"]
        self.assertEqual(cfg["hook_key"], "beforeShellExecution")
        self.assertIsNone(cfg["default_matcher"])
        self.assertFalse(cfg["nested"])


class TestLoadJson(unittest.TestCase):
    """Test JSON loading."""

    def test_load_existing_file(self):
        """Should load existing JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            f.flush()

            data = load_json(Path(f.name))
            self.assertEqual(data, {"key": "value"})

            os.unlink(f.name)

    def test_load_nonexistent_file(self):
        """Should return empty dict for nonexistent file."""
        data = load_json(Path("/nonexistent/path/file.json"))
        self.assertEqual(data, {})


class TestSaveJson(unittest.TestCase):
    """Test JSON saving."""

    def test_save_creates_parents(self):
        """Should create parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "file.json"

            save_json(path, {"key": "value"}, dry_run=False)

            self.assertTrue(path.exists())
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data, {"key": "value"})

    def test_save_dry_run(self):
        """Dry run should not write file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "file.json"

            save_json(path, {"key": "value"}, dry_run=True)

            self.assertFalse(path.exists())

    def test_save_pretty_prints(self):
        """Should save with indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "file.json"

            save_json(path, {"key": "value"}, dry_run=False)

            content = path.read_text()
            # Should have newlines (pretty printed)
            self.assertIn("\n", content)


class TestHasHook(unittest.TestCase):
    """Test hook existence checking."""

    def test_empty_list(self):
        """Empty list should have no hooks."""
        self.assertFalse(has_hook([], nested=True, command="/path/to/hook"))
        self.assertFalse(has_hook([], nested=False, command="/path/to/hook"))

    def test_nested_hook_exists(self):
        """Should find nested hook."""
        hooks = [
            {"matcher": "Bash", "hooks": [{"command": "/path/to/hook --claude"}]}
        ]
        self.assertTrue(has_hook(hooks, nested=True, command="/path/to/hook"))

    def test_nested_hook_not_exists(self):
        """Should not find missing nested hook."""
        hooks = [
            {"matcher": "Bash", "hooks": [{"command": "/other/hook"}]}
        ]
        self.assertFalse(has_hook(hooks, nested=True, command="/path/to/hook"))

    def test_flat_hook_exists(self):
        """Should find flat hook."""
        hooks = [{"command": "/path/to/hook --cursor"}]
        self.assertTrue(has_hook(hooks, nested=False, command="/path/to/hook"))

    def test_flat_hook_not_exists(self):
        """Should not find missing flat hook."""
        hooks = [{"command": "/other/hook"}]
        self.assertFalse(has_hook(hooks, nested=False, command="/path/to/hook"))

    def test_partial_match(self):
        """Should match partial command string."""
        hooks = [{"command": "/path/to/hook --flag --other"}]
        self.assertTrue(has_hook(hooks, nested=False, command="/path/to/hook"))

    def test_non_list_returns_false(self):
        """Non-list should return False."""
        self.assertFalse(has_hook(None, nested=True, command="cmd"))
        self.assertFalse(has_hook("string", nested=True, command="cmd"))
        self.assertFalse(has_hook({}, nested=True, command="cmd"))


class TestIdempotency(unittest.TestCase):
    """Test that hook merging is idempotent."""

    def test_repeated_merge_no_duplicates(self):
        """Running merge multiple times should not create duplicates."""
        # This is more of an integration test, but important for the spec
        hooks = []
        command = "/path/to/hook"

        # Simulate first merge
        if not has_hook(hooks, nested=False, command=command):
            hooks.append({"command": command})

        # Simulate second merge (should not add)
        if not has_hook(hooks, nested=False, command=command):
            hooks.append({"command": command})

        self.assertEqual(len(hooks), 1)


if __name__ == "__main__":
    unittest.main()
