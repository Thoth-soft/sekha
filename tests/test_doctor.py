"""Tests for `cyrus doctor` (cyrus._doctor).

Plan 06-01 Task 3 -- RED stage. Module `cyrus._doctor` does not yet exist.

Covers CLI-03 (7 diagnostic checks) + CLI-07 (ASCII-only output).

The MCP canary check shells out to `cyrus serve` via subprocess. We patch
`_doctor._mcp_canary` to avoid spawning processes in unit tests -- Plan
06-02's install-test job exercises the real subprocess path.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


EXPECTED_CHECK_NAMES = {
    "python_version",
    "cyrus_on_path",
    "cyrus_home_writable",
    "settings_hook_registered",
    "mcp_canary",
    "kill_switch",
    "recent_hook_errors",
}


class DoctorTestBase(unittest.TestCase):
    """Isolate CYRUS_HOME and Path.home, patch mcp_canary to a happy stub."""

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.fake_home = self.tmp / "home"
        self.cyrus_dir = self.tmp / "cyrus"
        self.fake_home.mkdir(parents=True, exist_ok=True)
        self.cyrus_dir.mkdir(parents=True, exist_ok=True)

        self._env_patch = mock.patch.dict(
            os.environ, {"CYRUS_HOME": str(self.cyrus_dir)}
        )
        self._home_patch = mock.patch(
            "pathlib.Path.home", return_value=self.fake_home
        )
        # Patch the canary by default so tests don't spawn subprocesses.
        self._canary_patch = mock.patch(
            "cyrus._doctor._mcp_canary",
            return_value=(True, "protocolVersion=2025-03-26"),
        )
        self._env_patch.start()
        self._home_patch.start()
        self._canary_patch.start()

    def tearDown(self) -> None:
        self._canary_patch.stop()
        self._home_patch.stop()
        self._env_patch.stop()
        self._td.cleanup()

    def _write_settings_with_cyrus_hook(self) -> None:
        settings = self.fake_home / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps({
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {"type": "command", "command": "cyrus hook run"}
                            ],
                        }
                    ]
                }
            }),
            encoding="utf-8",
        )


class TestCollectChecks(DoctorTestBase):
    def test_returns_seven_check_results(self) -> None:
        from cyrus._doctor import collect_checks
        self._write_settings_with_cyrus_hook()
        results = collect_checks()
        self.assertEqual(len(results), 7)
        names = {r.name for r in results}
        self.assertEqual(names, EXPECTED_CHECK_NAMES)

    def test_result_has_name_ok_detail(self) -> None:
        from cyrus._doctor import collect_checks
        results = collect_checks()
        for r in results:
            self.assertIsInstance(r.name, str)
            self.assertIsInstance(r.ok, bool)
            self.assertIsInstance(r.detail, str)


class TestJsonMode(DoctorTestBase):
    def test_outputs_parseable_json_to_stdout(self) -> None:
        from cyrus._doctor import run
        self._write_settings_with_cyrus_hook()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            run(["--json"])
        data = json.loads(stdout.getvalue())
        self.assertIn("checks", data)
        self.assertIn("all_ok", data)
        self.assertIsInstance(data["checks"], list)
        self.assertIsInstance(data["all_ok"], bool)


class TestTextMode(DoctorTestBase):
    def test_output_ascii_only(self) -> None:
        from cyrus._doctor import run
        self._write_settings_with_cyrus_hook()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            run([])
        stdout.getvalue().encode("ascii")  # must not raise

    def test_contains_ok_or_fail_prefix(self) -> None:
        from cyrus._doctor import run
        self._write_settings_with_cyrus_hook()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            run([])
        out = stdout.getvalue()
        self.assertTrue("[OK]" in out or "[FAIL]" in out)


class TestExitCodes(DoctorTestBase):
    def test_exit_zero_when_all_pass(self) -> None:
        from cyrus import _doctor as doctor
        self._write_settings_with_cyrus_hook()
        fake_results = [
            doctor.CheckResult(name=n, ok=True, detail="good")
            for n in sorted(EXPECTED_CHECK_NAMES)
        ]
        with mock.patch("cyrus._doctor.collect_checks", return_value=fake_results):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = doctor.run([])
            self.assertEqual(rc, 0)

    def test_exit_one_when_any_fails(self) -> None:
        from cyrus import _doctor as doctor
        fake_results = [
            doctor.CheckResult(name=n, ok=True, detail="good")
            for n in sorted(EXPECTED_CHECK_NAMES)
        ]
        fake_results[0] = doctor.CheckResult(
            name=fake_results[0].name, ok=False, detail="broken"
        )
        with mock.patch("cyrus._doctor.collect_checks", return_value=fake_results):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = doctor.run([])
            self.assertEqual(rc, 1)


class TestKillSwitch(DoctorTestBase):
    def test_kill_switch_marker_trips_check(self) -> None:
        from cyrus._hookutil import create_marker
        from cyrus._doctor import collect_checks
        self._write_settings_with_cyrus_hook()
        create_marker()
        results = {r.name: r for r in collect_checks()}
        ks = results["kill_switch"]
        self.assertFalse(ks.ok)
        self.assertIn("cyrus hook enable", ks.detail)


class TestRecentHookErrors(DoctorTestBase):
    def test_tail_entries_reported(self) -> None:
        from cyrus._doctor import collect_checks
        log = self.cyrus_dir / "hook-errors.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "2026-04-12T10:00:00+00:00 ValueError: boom1",
            "2026-04-12T10:05:00+00:00 ValueError: boom2",
            "2026-04-12T10:10:00+00:00 ValueError: boom3",
            "2026-04-12T10:15:00+00:00 ValueError: boom4",
            "2026-04-12T10:20:00+00:00 ValueError: boom5",
        ]
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        results = {r.name: r for r in collect_checks()}
        rhe = results["recent_hook_errors"]
        # Detail must reference a count or at least one of the log entries.
        self.assertTrue(
            "boom" in rhe.detail or "5" in rhe.detail or "recent" in rhe.detail,
            f"unexpected detail: {rhe.detail!r}",
        )


class TestSettingsHookMissing(DoctorTestBase):
    def test_missing_settings_reports_fail(self) -> None:
        from cyrus._doctor import collect_checks
        # No settings.json written.
        results = {r.name: r for r in collect_checks()}
        shr = results["settings_hook_registered"]
        self.assertFalse(shr.ok)
        self.assertIn("cyrus init", shr.detail)


class TestMcpCanaryPatched(DoctorTestBase):
    def test_canary_success_detail_contains_version(self) -> None:
        from cyrus._doctor import collect_checks
        self._write_settings_with_cyrus_hook()
        results = {r.name: r for r in collect_checks()}
        canary = results["mcp_canary"]
        self.assertTrue(canary.ok)
        self.assertIn("2025-03-26", canary.detail)


class TestCliIntegration(DoctorTestBase):
    def test_cli_main_doctor_dispatches(self) -> None:
        from cyrus.cli import main
        self._write_settings_with_cyrus_hook()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = main(["doctor"])
        self.assertIn(rc, (0, 1))  # depends on binary on PATH etc.
        out = stdout.getvalue()
        self.assertTrue("[OK]" in out or "[FAIL]" in out)

    def test_cli_main_doctor_json_dispatches(self) -> None:
        from cyrus.cli import main
        self._write_settings_with_cyrus_hook()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            main(["doctor", "--json"])
        data = json.loads(stdout.getvalue())
        self.assertIn("checks", data)
        self.assertIn("all_ok", data)


if __name__ == "__main__":
    unittest.main()
