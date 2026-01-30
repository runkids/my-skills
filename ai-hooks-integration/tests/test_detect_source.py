#!/usr/bin/env python3
"""Tests for parent process source detection."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from runtime.detect_source import (
    TOOL_SIGNATURES,
    detect_parent_source,
    get_parent_pid,
    get_process_cmdline,
)


class TestToolSignatures(unittest.TestCase):
    """Test that tool signatures are properly defined."""

    def test_all_tools_have_signatures(self):
        """Each tool should have at least one signature."""
        expected_tools = {"cursor", "opencode", "gemini", "windsurf", "zed"}
        self.assertEqual(set(TOOL_SIGNATURES.keys()), expected_tools)

    def test_signatures_are_lowercase(self):
        """All signatures should be lowercase for case-insensitive matching."""
        for tool, sigs in TOOL_SIGNATURES.items():
            for sig in sigs:
                self.assertEqual(
                    sig, sig.lower(), f"Signature '{sig}' for {tool} should be lowercase"
                )


class TestGetProcessCmdline(unittest.TestCase):
    """Test process command line retrieval."""

    def test_current_process_has_cmdline(self):
        """Current process should have a retrievable command line."""
        cmdline = get_process_cmdline(os.getpid())
        self.assertIsInstance(cmdline, str)
        # Should contain python or the test runner
        self.assertTrue(len(cmdline) > 0)

    def test_invalid_pid_returns_empty(self):
        """Invalid PID should return empty string, not raise."""
        cmdline = get_process_cmdline(999999999)
        self.assertEqual(cmdline, "")

    def test_pid_zero_returns_empty(self):
        """PID 0 should return empty string."""
        cmdline = get_process_cmdline(0)
        self.assertEqual(cmdline, "")


class TestGetParentPid(unittest.TestCase):
    """Test parent PID retrieval."""

    def test_current_process_has_parent(self):
        """Current process should have a parent PID."""
        ppid = get_parent_pid(os.getpid())
        # Should be a valid PID or None
        if ppid is not None:
            self.assertIsInstance(ppid, int)
            self.assertGreater(ppid, 0)

    def test_invalid_pid_returns_none(self):
        """Invalid PID should return None, not raise."""
        ppid = get_parent_pid(999999999)
        self.assertIsNone(ppid)


class TestDetectParentSource(unittest.TestCase):
    """Test source detection from process tree."""

    @patch("runtime.detect_source.get_process_cmdline")
    @patch("runtime.detect_source.get_parent_pid")
    @patch("os.getppid")
    def test_detects_cursor(self, mock_getppid, mock_get_parent_pid, mock_get_cmdline):
        """Should detect cursor from command line."""
        mock_getppid.return_value = 100
        mock_get_parent_pid.side_effect = [200, 300, None]
        mock_get_cmdline.side_effect = [
            "/usr/bin/node",  # pid 100
            "/Applications/Cursor.app/Contents/MacOS/Cursor",  # pid 200
            "launchd",  # pid 300
        ]

        result = detect_parent_source()
        self.assertEqual(result, "cursor")

    @patch("runtime.detect_source.get_process_cmdline")
    @patch("runtime.detect_source.get_parent_pid")
    @patch("os.getppid")
    def test_detects_opencode(self, mock_getppid, mock_get_parent_pid, mock_get_cmdline):
        """Should detect opencode from command line."""
        mock_getppid.return_value = 100
        mock_get_parent_pid.side_effect = [None]
        mock_get_cmdline.side_effect = ["/usr/local/bin/opencode"]

        result = detect_parent_source()
        self.assertEqual(result, "opencode")

    @patch("runtime.detect_source.get_process_cmdline")
    @patch("runtime.detect_source.get_parent_pid")
    @patch("os.getppid")
    def test_detects_gemini(self, mock_getppid, mock_get_parent_pid, mock_get_cmdline):
        """Should detect gemini from command line."""
        mock_getppid.return_value = 100
        mock_get_parent_pid.side_effect = [None]
        mock_get_cmdline.side_effect = ["node /usr/local/bin/gemini chat"]

        result = detect_parent_source()
        self.assertEqual(result, "gemini")

    @patch("runtime.detect_source.get_process_cmdline")
    @patch("runtime.detect_source.get_parent_pid")
    @patch("os.getppid")
    def test_returns_none_for_unknown(
        self, mock_getppid, mock_get_parent_pid, mock_get_cmdline
    ):
        """Should return None when no known tool is found."""
        mock_getppid.return_value = 100
        mock_get_parent_pid.side_effect = [200, None]
        mock_get_cmdline.side_effect = ["/bin/bash", "/sbin/launchd"]

        result = detect_parent_source()
        self.assertIsNone(result)

    @patch("runtime.detect_source.get_process_cmdline")
    @patch("runtime.detect_source.get_parent_pid")
    @patch("os.getppid")
    def test_respects_max_depth(
        self, mock_getppid, mock_get_parent_pid, mock_get_cmdline
    ):
        """Should stop at max_depth."""
        mock_getppid.return_value = 100
        # Always return next pid and unknown command
        mock_get_parent_pid.side_effect = list(range(101, 200))
        mock_get_cmdline.side_effect = ["/bin/bash"] * 100

        result = detect_parent_source(max_depth=3)
        self.assertIsNone(result)
        # Should have called get_cmdline exactly 3 times
        self.assertEqual(mock_get_cmdline.call_count, 3)

    @patch("runtime.detect_source.get_process_cmdline")
    @patch("runtime.detect_source.get_parent_pid")
    @patch("os.getppid")
    def test_case_insensitive(self, mock_getppid, mock_get_parent_pid, mock_get_cmdline):
        """Should match tool names case-insensitively."""
        mock_getppid.return_value = 100
        mock_get_parent_pid.side_effect = [None]
        mock_get_cmdline.side_effect = ["/Applications/CURSOR.APP/Contents/MacOS/Cursor"]

        result = detect_parent_source()
        self.assertEqual(result, "cursor")


class TestIntegration(unittest.TestCase):
    """Integration tests that run against the real system."""

    def test_detect_returns_valid_type(self):
        """detect_parent_source should return str or None."""
        result = detect_parent_source()
        self.assertTrue(
            result is None or isinstance(result, str),
            f"Expected str or None, got {type(result)}",
        )

    def test_detect_returns_known_tool_or_none(self):
        """If not None, should be a known tool name."""
        result = detect_parent_source()
        if result is not None:
            self.assertIn(
                result,
                TOOL_SIGNATURES.keys(),
                f"Unknown tool detected: {result}",
            )


if __name__ == "__main__":
    unittest.main()
