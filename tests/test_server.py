"""Tests for cyrus.server: handle_request dispatcher + CLI `serve` subcommand.

Plan 05-02 Task 1 (in-process unit tests for handle_request + CLI wiring).
Task 2 will extend this file with TestServerSubprocess covering subprocess
integration tests that drive the real `cyrus serve` binary via stdio.

Every test here is synchronous and stream-free: handle_request is a pure
function over dicts, which keeps unit tests fast and deterministic. The
subprocess-spawning tests live in TestServerSubprocess (Task 2).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from cyrus.jsonrpc import (
    ACCEPTED_PROTOCOL_VERSIONS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
)
from cyrus.server import handle_request


class TestHandleRequest(unittest.TestCase):
    """Pure-function tests for cyrus.server.handle_request."""

    # ------------------------------------------------------------------
    # 1. initialize echoes protocolVersion
    # ------------------------------------------------------------------
    def test_initialize_echoes_protocol_version(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        }
        resp = handle_request(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(resp["result"]["serverInfo"]["name"], "cyrus")
        self.assertIn("version", resp["result"]["serverInfo"])
        self.assertEqual(resp["result"]["capabilities"], {"tools": {}})

    # ------------------------------------------------------------------
    # 2. initialize accepts all three protocol versions
    # ------------------------------------------------------------------
    def test_initialize_accepts_all_three_versions(self):
        for version in ACCEPTED_PROTOCOL_VERSIONS:
            with self.subTest(protocolVersion=version):
                req = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": version,
                        "capabilities": {},
                    },
                }
                resp = handle_request(req)
                self.assertEqual(resp["result"]["protocolVersion"], version)

    # ------------------------------------------------------------------
    # 3. initialize unknown version falls back without erroring
    # ------------------------------------------------------------------
    def test_initialize_unknown_version_falls_back(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "9999-01-01", "capabilities": {}},
        }
        resp = handle_request(req)
        self.assertIsNotNone(resp)
        # MUST have a result (not an error) and a protocolVersion field.
        self.assertIn("result", resp)
        self.assertNotIn("error", resp)
        self.assertIn("protocolVersion", resp["result"])
        # Must be a non-empty string.
        self.assertTrue(resp["result"]["protocolVersion"])

    # ------------------------------------------------------------------
    # 4. notifications/initialized returns None (no response)
    # ------------------------------------------------------------------
    def test_notifications_initialized_returns_none(self):
        req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = handle_request(req)
        self.assertIsNone(resp)

    # ------------------------------------------------------------------
    # 5. tools/list returns six cyrus_*-prefixed tools
    # ------------------------------------------------------------------
    def test_tools_list_returns_six_tools(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        resp = handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), 6)
        for t in tools:
            self.assertTrue(
                t["name"].startswith("cyrus_"),
                f"tool name {t['name']} does not start with cyrus_",
            )

    # ------------------------------------------------------------------
    # 6. tools/call cyrus_status success — round-trips a handler result
    # ------------------------------------------------------------------
    def test_tools_call_cyrus_status_success(self):
        import json as _json

        with tempfile.TemporaryDirectory(prefix="cyrus-srv-test-") as td:
            home = Path(td)
            # Stage the five categories that cyrus_status walks.
            for cat in ("sessions", "decisions", "preferences", "projects", "rules"):
                (home / cat).mkdir()
            saved_home = os.environ.get("CYRUS_HOME")
            os.environ["CYRUS_HOME"] = str(home)
            try:
                req = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "cyrus_status", "arguments": {}},
                }
                resp = handle_request(req)
            finally:
                if saved_home is None:
                    os.environ.pop("CYRUS_HOME", None)
                else:
                    os.environ["CYRUS_HOME"] = saved_home

            self.assertIsNotNone(resp)
            self.assertIn("result", resp)
            content = resp["result"]["content"]
            self.assertEqual(content[0]["type"], "text")
            status = _json.loads(content[0]["text"])
            for key in ("total", "by_category", "rules_count", "recent", "hook_errors"):
                self.assertIn(key, status)

    # ------------------------------------------------------------------
    # 7. tools/call unknown tool returns METHOD_NOT_FOUND (-32601)
    # ------------------------------------------------------------------
    def test_tools_call_unknown_tool_returns_method_not_found(self):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "cyrus_bogus", "arguments": {}},
        }
        resp = handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], METHOD_NOT_FOUND)

    # ------------------------------------------------------------------
    # 8. tools/call handler exception returns isError (NOT JSON-RPC error)
    # ------------------------------------------------------------------
    def test_tools_call_handler_exception_returns_is_error(self):
        from cyrus import tools as _tools

        saved = _tools.HANDLERS["cyrus_status"]
        def boom(**_kwargs):
            raise RuntimeError("boom")
        _tools.HANDLERS["cyrus_status"] = boom
        try:
            req = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "cyrus_status", "arguments": {}},
            }
            resp = handle_request(req)
        finally:
            _tools.HANDLERS["cyrus_status"] = saved

        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        self.assertTrue(resp["result"].get("isError"))
        self.assertIn("boom", resp["result"]["content"][0]["text"])

    # ------------------------------------------------------------------
    # 9. ping returns empty result
    # ------------------------------------------------------------------
    def test_ping_returns_empty_result(self):
        req = {"jsonrpc": "2.0", "id": 6, "method": "ping"}
        resp = handle_request(req)
        self.assertEqual(resp, {"jsonrpc": "2.0", "id": 6, "result": {}})

    # ------------------------------------------------------------------
    # 10. notifications/cancelled returns None and does not raise
    # ------------------------------------------------------------------
    def test_notifications_cancelled_returns_none(self):
        req = {
            "jsonrpc": "2.0",
            "method": "notifications/cancelled",
            "params": {"requestId": 3},
        }
        resp = handle_request(req)
        self.assertIsNone(resp)

    # ------------------------------------------------------------------
    # 11. unknown method returns METHOD_NOT_FOUND
    # ------------------------------------------------------------------
    def test_unknown_method_returns_method_not_found(self):
        req = {"jsonrpc": "2.0", "id": 7, "method": "prompts/list"}
        resp = handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], METHOD_NOT_FOUND)

    # ------------------------------------------------------------------
    # 12. missing method field returns INVALID_REQUEST (-32600)
    # ------------------------------------------------------------------
    def test_missing_method_field_returns_invalid_request(self):
        req = {"jsonrpc": "2.0", "id": 8}
        resp = handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], INVALID_REQUEST)

    # ------------------------------------------------------------------
    # 13. request id preserved for numeric, string, and null
    # ------------------------------------------------------------------
    def test_request_id_preserved_for_numeric_and_string(self):
        for rid in (1, "abc", None):
            with self.subTest(id=rid):
                req = {"jsonrpc": "2.0", "id": rid, "method": "ping"}
                resp = handle_request(req)
                self.assertEqual(resp["id"], rid)


class TestCli(unittest.TestCase):
    """Verify `cyrus serve` subcommand is wired into the argparse tree."""

    def test_cli_serve_subcommand_registered(self):
        from cyrus.cli import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["serve"])
        self.assertEqual(args.command, "serve")


if __name__ == "__main__":
    unittest.main()
