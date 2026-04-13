"""Tests for cyrus.tools: 6 MCP tool handlers delegating to storage/search/rules.

RED stage for Plan 05-01 Task 3. Every test stages its own CYRUS_HOME
tempdir so no two tests collide on disk. Handlers are asserted at the
dict-shape level — the underlying storage/search/rules behavior already
has its own dedicated test modules; we don't duplicate that coverage,
we just verify the thin delegation works.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from cyrus.storage import parse_frontmatter


class _TempHomeMixin:
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="cyrus-tools-test-")
        self._saved = os.environ.get("CYRUS_HOME")
        os.environ["CYRUS_HOME"] = self._tmp

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("CYRUS_HOME", None)
        else:
            os.environ["CYRUS_HOME"] = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# cyrus_save (MCP-04)
# --------------------------------------------------------------------------
class TestCyrusSave(_TempHomeMixin, unittest.TestCase):
    def test_save_returns_path_and_id(self):
        from cyrus.tools import cyrus_save
        result = cyrus_save(category="decisions", content="Use Python 3.11")
        self.assertIn("path", result)
        self.assertIn("id", result)
        self.assertTrue(result["path"].endswith(".md"))
        # id is 8-char hex (blake2b digest_size=4 -> 8 hex chars)
        self.assertEqual(len(result["id"]), 8)
        self.assertTrue(all(c in "0123456789abcdef" for c in result["id"]))
        # File exists under decisions/
        p = Path(result["path"])
        self.assertTrue(p.exists())
        self.assertEqual(p.parent.name, "decisions")

    def test_save_honours_tags_and_source(self):
        from cyrus.tools import cyrus_save
        result = cyrus_save(
            category="sessions",
            content="note body",
            tags=["alpha", "beta"],
            source="unit-test",
        )
        text = Path(result["path"]).read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(text)
        self.assertEqual(metadata.get("tags"), ["alpha", "beta"])
        self.assertEqual(metadata.get("source"), "unit-test")
        self.assertIn("note body", body)

    def test_save_rejects_invalid_category(self):
        from cyrus.tools import cyrus_save
        with self.assertRaises(ValueError):
            cyrus_save(category="bogus", content="x")


# --------------------------------------------------------------------------
# cyrus_search (MCP-05)
# --------------------------------------------------------------------------
class TestCyrusSearch(_TempHomeMixin, unittest.TestCase):
    def _save(self, category, content, **kw):
        from cyrus.tools import cyrus_save
        return cyrus_save(category=category, content=content, **kw)

    def test_search_returns_results_shape(self):
        from cyrus.tools import cyrus_search
        self._save("decisions", "alpha beta gamma")
        self._save("sessions", "alpha only")
        out = cyrus_search(query="alpha")
        self.assertIn("results", out)
        self.assertGreaterEqual(len(out["results"]), 2)
        for r in out["results"]:
            self.assertEqual(
                set(r.keys()), {"path", "score", "snippet", "metadata"}
            )

    def test_search_honours_category_filter(self):
        from cyrus.tools import cyrus_search
        self._save("decisions", "needle in decisions")
        self._save("sessions", "needle in sessions")
        out = cyrus_search(query="needle", category="decisions")
        self.assertEqual(len(out["results"]), 1)
        self.assertIn("decisions", out["results"][0]["path"])

    def test_search_limit_default_is_10(self):
        from cyrus.tools import cyrus_search
        for i in range(12):
            self._save("sessions", f"foo number {i}", tags=[f"t{i}"])
        out = cyrus_search(query="foo")
        self.assertLessEqual(len(out["results"]), 10)


# --------------------------------------------------------------------------
# cyrus_list (MCP-06)
# --------------------------------------------------------------------------
class TestCyrusList(_TempHomeMixin, unittest.TestCase):
    def _save(self, category, content):
        from cyrus.tools import cyrus_save
        return cyrus_save(category=category, content=content)

    def test_list_returns_metadata_no_body(self):
        from cyrus.tools import cyrus_list
        self._save("sessions", "one")
        self._save("decisions", "two")
        self._save("sessions", "three")
        out = cyrus_list()
        self.assertIn("memories", out)
        self.assertGreaterEqual(len(out["memories"]), 3)
        for m in out["memories"]:
            for k in ("path", "category", "created", "updated", "tags", "id"):
                self.assertIn(k, m)
            self.assertNotIn("content", m)
            self.assertNotIn("body", m)

    def test_list_category_filter(self):
        from cyrus.tools import cyrus_list
        self._save("sessions", "a")
        self._save("decisions", "b")
        out = cyrus_list(category="decisions")
        self.assertGreaterEqual(len(out["memories"]), 1)
        for m in out["memories"]:
            self.assertIn("decisions", m["path"])

    def test_list_limit(self):
        from cyrus.tools import cyrus_list
        for i in range(5):
            self._save("sessions", f"entry-{i}")
        out = cyrus_list(limit=2)
        self.assertLessEqual(len(out["memories"]), 2)


# --------------------------------------------------------------------------
# cyrus_delete (MCP-07)
# --------------------------------------------------------------------------
class TestCyrusDelete(_TempHomeMixin, unittest.TestCase):
    def test_delete_removes_file(self):
        from cyrus.tools import cyrus_delete, cyrus_save
        saved = cyrus_save(category="sessions", content="doomed")
        out = cyrus_delete(path=saved["path"])
        self.assertTrue(out["success"])
        self.assertFalse(Path(saved["path"]).exists())

    def test_delete_missing_returns_failure(self):
        from cyrus.tools import cyrus_delete
        fake = str(Path(self._tmp) / "sessions" / "nope.md")
        out = cyrus_delete(path=fake)
        self.assertFalse(out["success"])
        self.assertIn("error", out)

    def test_delete_rejects_path_outside_cyrus_home(self):
        from cyrus.tools import cyrus_delete
        # Create a real file outside CYRUS_HOME to prove we don't touch it.
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".md"
        ) as f:
            f.write(b"outside")
            outside = f.name
        try:
            out = cyrus_delete(path=outside)
            self.assertFalse(out["success"])
            self.assertIn("error", out)
            # The outside file must still exist.
            self.assertTrue(Path(outside).exists())
        finally:
            try:
                os.unlink(outside)
            except OSError:
                pass


# --------------------------------------------------------------------------
# cyrus_status (MCP-08)
# --------------------------------------------------------------------------
class TestCyrusStatus(_TempHomeMixin, unittest.TestCase):
    def test_status_shape(self):
        from cyrus.tools import cyrus_save, cyrus_status
        cyrus_save(category="decisions", content="one")
        cyrus_save(category="decisions", content="two")
        out = cyrus_status()
        for k in ("total", "by_category", "rules_count", "recent", "hook_errors"):
            self.assertIn(k, out)
        self.assertIsInstance(out["by_category"], dict)
        self.assertGreaterEqual(out["by_category"]["decisions"], 2)
        self.assertGreaterEqual(out["total"], 2)

    def test_status_reads_hook_errors_log(self):
        from cyrus.tools import cyrus_status
        log = Path(self._tmp) / "hook-errors.log"
        log.write_text("line-1\nline-2\nline-3\n", encoding="utf-8")
        out = cyrus_status()
        self.assertEqual(out["hook_errors"], 3)


# --------------------------------------------------------------------------
# cyrus_add_rule (MCP-09)
# --------------------------------------------------------------------------
class TestCyrusAddRule(_TempHomeMixin, unittest.TestCase):
    def test_add_rule_writes_file(self):
        from cyrus.tools import cyrus_add_rule
        out = cyrus_add_rule(
            name="no-foo",
            severity="block",
            matches=["Bash"],
            pattern="foo",
            message="no foo allowed",
        )
        rule_path = Path(out["path"])
        self.assertTrue(rule_path.exists())
        self.assertEqual(rule_path.parent.name, "rules")
        meta, _body = parse_frontmatter(
            rule_path.read_text(encoding="utf-8")
        )
        self.assertEqual(meta["name"], "no-foo")
        self.assertEqual(meta["severity"], "block")
        self.assertEqual(meta["matches"], ["Bash"])
        self.assertEqual(meta["pattern"], "foo")
        self.assertEqual(meta["message"], "no foo allowed")
        self.assertEqual(meta["priority"], 50)
        self.assertEqual(meta["triggers"], ["PreToolUse"])

    def test_add_rule_validates_regex_before_write(self):
        from cyrus.tools import cyrus_add_rule
        rules_dir = Path(self._tmp) / "rules"
        rule_path = rules_dir / "bad.md"
        with self.assertRaises(Exception) as ctx:
            cyrus_add_rule(
                name="bad",
                severity="block",
                matches=["*"],
                pattern="[",  # unclosed character class
                message="x",
            )
        # Any exception type is acceptable (re.error is a subclass of
        # Exception); the MCP-09 hard requirement is that the rule file
        # does NOT exist after the failure.
        del ctx  # ensure at least one assert above
        self.assertFalse(rule_path.exists())

    def test_add_rule_rejects_bad_severity(self):
        from cyrus.tools import cyrus_add_rule
        with self.assertRaises(ValueError):
            cyrus_add_rule(
                name="kab",
                severity="kablooey",
                matches=["*"],
                pattern="foo",
                message="x",
            )


# --------------------------------------------------------------------------
# HANDLERS registry
# --------------------------------------------------------------------------
class TestHandlers(unittest.TestCase):
    def test_handlers_dict_covers_all_six(self):
        from cyrus.tools import HANDLERS
        expected = {
            "cyrus_save", "cyrus_search", "cyrus_list",
            "cyrus_delete", "cyrus_status", "cyrus_add_rule",
        }
        self.assertEqual(set(HANDLERS.keys()), expected)
        for name, fn in HANDLERS.items():
            self.assertTrue(callable(fn), f"{name} is not callable")


if __name__ == "__main__":
    unittest.main()
