"""PreToolUse hook entrypoint. Short-lived process invoked by Claude Code.

Reads a PreToolUse JSON event from stdin, evaluates rules via cyrus.rules,
and emits a permissionDecision JSON to stdout. Fail-open on any internal
error; kill-switch marker disables the hook after repeated failures.

stdout is sacred — only the decision JSON goes there. sys.stdout is
swapped to sys.stderr inside _run() before any non-stdlib import so stray
log lines from dependencies (or a rogue `print()` anywhere in the import
chain) cannot corrupt the protocol stream. The real stdout is passed to
the emit_* helpers explicitly.

Module-top imports are strictly `sys` and `json` (plus `__future__`). Every
other import — cyrus.rules, cyrus.paths, cyrus._hookutil, pathlib, even
`traceback` — lives inside _run() so `python -X importtime cyrus.hook`
stays under the 30ms budget. The ast-introspection test in tests/test_hook.py
enforces this structurally.
"""
# Requirement coverage:
#   HOOK-01: `cyrus hook run` entry (dispatched by cyrus.cli → main())
#   HOOK-02: Reads PreToolUse JSON from stdin
#   HOOK-03: Emits deny JSON on block match
#   HOOK-04: Emits additionalContext JSON on warn match
#   HOOK-05: Belt-and-suspenders (stdout JSON + stderr + exit 2)
#   HOOK-06: Fail-open with ~/.cyrus/hook-errors.log + stderr warning
#   HOOK-07: Kill switch after 3 errors in 10 min via marker file
#   HOOK-09: Lazy imports — only sys, json at module top
from __future__ import annotations

import sys
import json  # noqa: F401 — re-exported name for CLI & bench; imported here per CONTEXT budget


def _run(stdin, stdout, stderr) -> int:
    """Core PreToolUse decision loop. Test-callable with in-memory streams.

    Contract:
    - Swap sys.stdout → stderr early, before any heavyweight import.
    - Check kill switch first — if tripped, return allow-by-default.
    - Parse stdin → load rules for (hook_event, tool_name) → evaluate.
    - Emit block / warn / allow via cyrus._hookutil helpers.
    - Top-level `except Exception` guarantees fail-open: log + stderr warn
      + exit 0. After 3 errors within 10 minutes, create the kill-switch
      marker so subsequent invocations short-circuit.

    Returns the exit code (2 on block, 0 otherwise). Callers in test code
    pass StringIO streams; main() delegates to sys.stdin/stdout/stderr.
    """
    real_stdout = stdout
    saved_stdout = sys.stdout
    # Redirect any stray print() from downstream imports to stderr so it
    # cannot corrupt the protocol channel.
    sys.stdout = stderr
    try:
        # Everything non-stdlib lives here — see module docstring.
        from cyrus._hookutil import (
            check_kill_switch,
            create_marker,
            emit_allow,
            emit_block,
            emit_warn,
            fail_open,
            read_event,
            record_error,
        )

        # Kill switch — never evaluate rules when disabled. Short-circuit
        # BEFORE reading stdin so a malformed event while disabled still
        # produces a clean allow (Claude Code keeps working).
        if check_kill_switch():
            return emit_allow(real_stdout)

        try:
            event = read_event(stdin)
            from cyrus.paths import category_dir
            from cyrus.rules import evaluate, load_rules

            hook_event = event.get("hook_event_name", "PreToolUse")
            tool_name = event.get("tool_name", "")
            tool_input = event.get("tool_input") or {}

            rules = load_rules(category_dir("rules"), hook_event, tool_name)
            winner = evaluate(rules, tool_input)
            if winner is None:
                return emit_allow(real_stdout)
            if winner.severity == "block":
                return emit_block(winner.message, real_stdout, stderr)
            return emit_warn(winner.message, real_stdout)
        except Exception as exc:  # noqa: BLE001 — fail-open is intentional
            fail_open(exc, stderr)
            if record_error(exc):
                create_marker()
            return 0
    finally:
        sys.stdout = saved_stdout  # restore for process cleanliness


def main() -> int:
    """Real-process entrypoint. Reads sys.stdin, writes sys.stdout/stderr."""
    return _run(sys.stdin, sys.stdout, sys.stderr)


def enable() -> int:
    """Remove the kill-switch marker so the hook runs again."""
    from cyrus._hookutil import clear_marker
    clear_marker()
    sys.stderr.write("cyrus hook: enabled\n")
    return 0


def disable() -> int:
    """Create the kill-switch marker so the hook short-circuits to allow."""
    from cyrus._hookutil import create_marker
    create_marker()
    sys.stderr.write("cyrus hook: disabled\n")
    return 0


# bench() is implemented in plan 04-02. The CLI catches ImportError on the
# bench subcommand and prints a friendly message in the meantime.


if __name__ == "__main__":
    raise SystemExit(main())
