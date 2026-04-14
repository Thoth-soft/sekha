"""Tests for sekha._cliutil: ASCII table, settings merge, atomic JSON write, say helpers.

Plan 06-01 Task 1 — RED stage. Module does not yet exist at test-write time.

Design invariants under test:
- format_table emits pure ASCII (cp1252 safe on Windows).
- merge_claude_settings is idempotent: second run with same inputs returns
  changed=False and an equivalent merged dict.
- backup_file copies bytes verbatim to a timestamped sibling path.
- write_json_atomic uses stable indent=2 + sort_keys=True and round-trips.
- say() writes to stderr by default, appends newline, leaves ASCII input alone.
"""
from __future__ import annotations

import copy
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class TestFormatTable(unittest.TestCase):
    def test_headers_and_rows_appear_in_output(self) -> None:
        from sekha._cliutil import format_table
        out = format_table(["A", "BB"], [["x", "yy"]])
        self.assertIn("A", out)
        self.assertIn("BB", out)
        self.assertIn("x", out)
        self.assertIn("yy", out)

    def test_output_is_ascii_only(self) -> None:
        from sekha._cliutil import format_table
        out = format_table(["NAME", "SEVERITY"], [["foo", "block"], ["bar", "warn"]])
        # Must not raise — cp1252-safe on Windows cmd.exe
        out.encode("ascii")

    def test_empty_rows_produces_header(self) -> None:
        from sekha._cliutil import format_table
        out = format_table(["A", "B"], [])
        # No crash; header names present.
        self.assertIn("A", out)
        self.assertIn("B", out)

    def test_no_unicode_box_drawing_chars(self) -> None:
        from sekha._cliutil import format_table
        out = format_table(["A", "B"], [["1", "2"]])
        # Every char must be printable ASCII 0x20-0x7E OR newline/CR.
        for ch in out:
            code = ord(ch)
            self.assertTrue(
                0x20 <= code <= 0x7E or ch in ("\n", "\r"),
                f"non-ASCII-printable char {ch!r} (0x{code:X}) in table output",
            )

    def test_column_alignment(self) -> None:
        from sekha._cliutil import format_table
        out = format_table(["A", "B"], [["short", "x"], ["longer-value", "yy"]])
        # Simple sanity: the output contains the literal strings.
        self.assertIn("short", out)
        self.assertIn("longer-value", out)


class TestMergeClaudeSettings(unittest.TestCase):
    def test_empty_input_adds_pretooluse(self) -> None:
        from sekha._cliutil import merge_claude_settings
        merged, changed = merge_claude_settings({})
        self.assertTrue(changed)
        entries = merged["hooks"]["PreToolUse"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["matcher"], "*")
        self.assertEqual(
            entries[0]["hooks"],
            [{"type": "command", "command": "sekha hook run"}],
        )

    def test_idempotent_second_run(self) -> None:
        from sekha._cliutil import merge_claude_settings
        first, _ = merge_claude_settings({})
        second, changed = merge_claude_settings(first)
        self.assertFalse(changed)
        self.assertEqual(first, second)

    def test_preserves_unrelated_user_entry(self) -> None:
        from sekha._cliutil import merge_claude_settings
        existing = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Edit",
                        "hooks": [{"type": "command", "command": "user-linter"}],
                    }
                ]
            }
        }
        original = copy.deepcopy(existing)
        merged, changed = merge_claude_settings(existing)
        self.assertTrue(changed)
        # Input must not be mutated.
        self.assertEqual(existing, original)
        # User linter preserved.
        commands: list[str] = []
        for entry in merged["hooks"]["PreToolUse"]:
            for h in entry.get("hooks", []):
                commands.append(h.get("command", ""))
        self.assertIn("user-linter", commands)
        self.assertIn("sekha hook run", commands)

    def test_hooks_without_pretooluse_gets_array(self) -> None:
        from sekha._cliutil import merge_claude_settings
        existing = {"hooks": {"PostToolUse": []}}
        merged, changed = merge_claude_settings(existing)
        self.assertTrue(changed)
        self.assertIn("PreToolUse", merged["hooks"])
        # PostToolUse preserved.
        self.assertIn("PostToolUse", merged["hooks"])

    def test_recognizes_nested_existing_sekha_entry(self) -> None:
        from sekha._cliutil import merge_claude_settings
        existing = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {"type": "command", "command": "sekha hook run"},
                        ],
                    }
                ]
            }
        }
        merged, changed = merge_claude_settings(existing)
        self.assertFalse(changed)
        self.assertEqual(merged, existing)


class TestBackupFile(unittest.TestCase):
    def test_existing_file_creates_bak(self) -> None:
        from sekha._cliutil import backup_file
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "settings.json"
            target.write_bytes(b'{"a": 1}')
            bak = backup_file(target)
            self.assertIsNotNone(bak)
            assert bak is not None  # for type checker
            self.assertTrue(bak.exists())
            self.assertEqual(bak.read_bytes(), b'{"a": 1}')
            # Name format: settings.json.bak.<timestamp>
            self.assertTrue(bak.name.startswith("settings.json.bak."))

    def test_missing_file_returns_none(self) -> None:
        from sekha._cliutil import backup_file
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "does-not-exist.json"
            result = backup_file(target)
            self.assertIsNone(result)
            # No bak created.
            baks = list(Path(td).glob("*.bak.*"))
            self.assertEqual(baks, [])

    def test_backup_name_is_ascii(self) -> None:
        from sekha._cliutil import backup_file
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "settings.json"
            target.write_bytes(b"{}")
            bak = backup_file(target)
            assert bak is not None
            bak.name.encode("ascii")  # must not raise


class TestWriteJsonAtomic(unittest.TestCase):
    def test_writes_and_roundtrips(self) -> None:
        from sekha._cliutil import write_json_atomic
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "out.json"
            data = {"b": 2, "a": 1}
            write_json_atomic(target, data)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), data)

    def test_creates_parent_dir(self) -> None:
        from sekha._cliutil import write_json_atomic
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "nested" / "deep" / "out.json"
            write_json_atomic(target, {"x": 1})
            self.assertTrue(target.exists())

    def test_uses_indent_and_sort_keys(self) -> None:
        from sekha._cliutil import write_json_atomic
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "out.json"
            write_json_atomic(target, {"b": 2, "a": 1})
            text = target.read_text(encoding="utf-8")
            # indent=2 means lines after first start with spaces.
            self.assertIn("\n  ", text)
            # sort_keys=True means 'a' appears before 'b'.
            self.assertLess(text.index('"a"'), text.index('"b"'))


class TestSay(unittest.TestCase):
    def test_writes_to_stderr_by_default(self) -> None:
        from sekha._cliutil import say
        buf = io.StringIO()
        with mock.patch("sys.stderr", buf):
            say("hello")
        self.assertIn("hello", buf.getvalue())

    def test_appends_newline(self) -> None:
        from sekha._cliutil import say
        buf = io.StringIO()
        say("abc", stream=buf)
        self.assertTrue(buf.getvalue().endswith("\n"))

    def test_ascii_passthrough(self) -> None:
        from sekha._cliutil import say
        buf = io.StringIO()
        say("[OK] ready", stream=buf)
        self.assertEqual(buf.getvalue(), "[OK] ready\n")


class TestRegisterClaudeMcp(unittest.TestCase):
    """Each possible outcome of `claude mcp add` maps to the right status."""

    def test_no_claude_on_path_returns_no_claude(self) -> None:
        from sekha._cliutil import register_claude_mcp
        with mock.patch("shutil.which", return_value=None):
            status, detail = register_claude_mcp()
        self.assertEqual(status, "no_claude")
        self.assertIn("PATH", detail)

    def test_successful_add_returns_registered(self) -> None:
        from sekha._cliutil import register_claude_mcp
        fake_result = mock.Mock(returncode=0, stdout="Added server sekha", stderr="")
        with mock.patch("shutil.which", return_value="/usr/bin/claude"), \
             mock.patch("subprocess.run", return_value=fake_result):
            status, _ = register_claude_mcp()
        self.assertEqual(status, "registered")

    def test_already_exists_error_returns_already(self) -> None:
        from sekha._cliutil import register_claude_mcp
        fake_result = mock.Mock(
            returncode=1,
            stdout="",
            stderr="Error: MCP server 'sekha' already exists in user config",
        )
        with mock.patch("shutil.which", return_value="/usr/bin/claude"), \
             mock.patch("subprocess.run", return_value=fake_result):
            status, detail = register_claude_mcp()
        self.assertEqual(status, "already")
        self.assertIn("already exists", detail)

    def test_generic_failure_returns_error(self) -> None:
        from sekha._cliutil import register_claude_mcp
        fake_result = mock.Mock(
            returncode=1, stdout="", stderr="network unreachable"
        )
        with mock.patch("shutil.which", return_value="/usr/bin/claude"), \
             mock.patch("subprocess.run", return_value=fake_result):
            status, detail = register_claude_mcp()
        self.assertEqual(status, "error")
        self.assertIn("network unreachable", detail)

    def test_subprocess_os_error_returns_error(self) -> None:
        from sekha._cliutil import register_claude_mcp
        with mock.patch("shutil.which", return_value="/usr/bin/claude"), \
             mock.patch("subprocess.run", side_effect=OSError("permission denied")):
            status, detail = register_claude_mcp()
        self.assertEqual(status, "error")
        self.assertIn("permission denied", detail)

    def test_invokes_correct_command_shape(self) -> None:
        from sekha._cliutil import register_claude_mcp
        fake_result = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("shutil.which", return_value="/path/to/claude"), \
             mock.patch("subprocess.run", return_value=fake_result) as m:
            register_claude_mcp()
        args = m.call_args[0][0]
        self.assertEqual(args[0], "/path/to/claude")
        self.assertEqual(args[1:5], ["mcp", "add", "sekha", "--scope"])
        self.assertEqual(args[5], "user")
        self.assertEqual(args[6], "--")
        self.assertEqual(args[7:], ["python", "-m", "sekha.cli", "serve"])


if __name__ == "__main__":
    unittest.main()
