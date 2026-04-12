"""Private helpers for cyrus.search: ReDoS watchdog + scoring primitives.

This module is private — the public API lives in `cyrus.search`. It owns:
- the regex-metachar detection heuristic (is_literal_query) that lets us
  avoid the ReDoS watchdog entirely for plain-substring queries,
- the 30-day-half-life recency decay and the filename_bonus multiplier that
  together with term frequency form the final score,
- the per-line snippet extractor with 120-char truncation, and
- the threaded scan_file_with_timeout that kills pathological regex matches
  (e.g. `(a+)+b` against long 'a' runs) at 100ms wall-clock rather than
  letting a single hostile file freeze the whole search.

Stdlib only. All logs go to stderr via cyrus.logutil.get_logger — never
stdout, because the MCP server protocol stream owns stdout.
"""
from __future__ import annotations

import math
import re
import threading
from pathlib import Path

from cyrus.logutil import get_logger

_log = get_logger(__name__)

# Every character that would change the meaning of a regex pattern. If NONE
# of these appear in the query we can safely bypass re.compile + findall and
# use str.count — which is O(n) and ReDoS-immune by construction.
_REGEX_METACHARS = frozenset(".^$*+?()[]{}|\\")

# Nested-quantifier detector. CPython's `re` is a C extension that holds the
# GIL for the entire findall() call, which means a daemon-thread watchdog
# cannot preempt a catastrophic backtrack — `t.join(timeout)` waits for the
# GIL the worker never releases. The only robust defense is to reject the
# dangerous shape BEFORE compile+findall runs.
#
# We match the three canonical catastrophic shapes from the CONTEXT spec:
#   (a+)+     — nested plus
#   (a*)*     — nested star
#   (a+)*     — mixed
#   (a*)+     — mixed
#   (a|a)*    — alternation of overlap under star/plus
# Plus any `{n,}` or `{n,m}` variant of the inner or outer quantifier.
_CATASTROPHIC_RE = re.compile(
    r"""
    \(              # opening group
    [^)]*?          # group body (non-greedy, no nested groups in v1)
    (?:             # inner quantifier:
        [*+]        #   * or +
        | \{\d*,\d*\}  #   {n,} or {n,m}
    )
    [^)]*?          # rest of body
    \)              # closing
    (?:             # outer quantifier applied to group:
        [*+]
        | \{\d*,\d*\}
    )
    """,
    re.VERBOSE,
)
_ALT_OVERLAP_RE = re.compile(r"\([^)]*?\|[^)]*?\)\s*[*+]")


def _is_catastrophic_pattern(pattern: str) -> bool:
    """Return True if the regex `pattern` has the shape of a classic ReDoS.

    Catches (X+)+, (X*)*, (X+)*, (X*)+, {n,}/{n,m} variants, and (X|Y)* with
    overlapping alternatives. Strict superset-of-false-positives is fine —
    false positives degrade gracefully (the user sees a warning and no
    results for that file); false negatives would hang the entire search.
    """
    if _CATASTROPHIC_RE.search(pattern):
        return True
    if _ALT_OVERLAP_RE.search(pattern):
        return True
    return False


def is_literal_query(query: str) -> bool:
    """True if the query contains no regex metacharacters.

    Literal queries are searched with str.lower() + str.count() and cannot
    trigger catastrophic backtracking. Empty string is trivially literal.
    """
    return not any(c in _REGEX_METACHARS for c in query)


def recency_decay(age_days: float) -> float:
    """exp(-age_days / 30) with a floor at age_days == 0.

    A fresh file returns 1.0; a file touched 30 days ago returns ~0.368;
    90 days returns ~0.050. Negative age_days (future-dated file, usually
    from mtime skew) is clamped to 1.0 so a misconfigured clock cannot
    push a document above the fresh-score ceiling.
    """
    if age_days <= 0.0:
        return 1.0
    return math.exp(-age_days / 30.0)


def filename_bonus(query: str, path: Path) -> float:
    """2.0 when query (case-insensitive) is a substring of path.name, else 1.0.

    Empty query returns 1.0 — the caller is expected to short-circuit empty
    searches before reaching here, but we defend anyway.
    """
    if not query:
        return 1.0
    return 2.0 if query.lower() in path.name.lower() else 1.0


def extract_snippet(body: str, query: str, *, max_line_len: int = 120) -> str:
    """Matched line plus up to one line above and one below, '\\n'-joined.

    Match is case-insensitive substring on lines split by '\\n'. Each line
    in the returned window is truncated to max_line_len characters, with
    the last three characters replaced by '...' when truncation occurs.
    Returns '' when body/query is empty or no line matches.

    v1 uses substring (not regex) for snippet line selection even when the
    caller's search query is a regex — this keeps snippet extraction
    ReDoS-immune. Downstream callers that want regex-accurate highlight
    markers can layer that on top of this helper.
    """
    if not query or not body:
        return ""
    q = query.lower()
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if q in line.lower():
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            window = lines[start:end]
            truncated = []
            for ln in window:
                if len(ln) > max_line_len:
                    truncated.append(ln[: max_line_len - 3] + "...")
                else:
                    truncated.append(ln)
            return "\n".join(truncated)
    return ""


def scan_file_with_timeout(
    path: Path,
    query: str,
    *,
    timeout: float = 0.1,
    is_literal: bool,
) -> tuple[int, bool]:
    """Count occurrences of `query` in file at `path`.

    Returns (match_count, timed_out).

    Literal path: read text, lowercase both, str.count — no ReDoS possible.

    Regex path: spawn a daemon thread running `re.compile(query, IGNORECASE)
    .findall(text)`. Parent waits `timeout` seconds via thread.join. If the
    thread has not finished we log a warning to stderr and return (0, True).
    The runaway thread is daemon=True, so it will not block interpreter
    shutdown; Python has no portable way to kill it cleanly (no
    pthread_cancel equivalent), but the process is not held hostage.

    On read errors (missing file, permission denied) logs a warning and
    returns (0, False) — a failed read is not a ReDoS event.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        _log.warning("search: cannot read %s: %s", path, e)
        return (0, False)

    if is_literal:
        if not query:
            return (0, False)
        return (text.lower().count(query.lower()), False)

    # Regex path — reject catastrophic shapes UP FRONT. CPython's `re` is a C
    # extension that holds the GIL throughout findall, so a thread watchdog
    # cannot preempt a runaway backtrack. The pre-check keeps us out of that
    # trap entirely for the known-dangerous shapes.
    if _is_catastrophic_pattern(query):
        _log.warning(
            "search: regex %r on %s rejected as catastrophic (ReDoS guard)",
            query,
            path,
        )
        return (0, True)

    # Non-catastrophic regex — still run under the thread watchdog as a
    # secondary defense for surprises the static check misses. If the
    # watchdog fires the worker will keep running (daemon) but the search
    # moves on.
    result: dict = {"count": 0, "done": False}

    def _worker() -> None:
        try:
            pattern = re.compile(query, re.IGNORECASE)
            result["count"] = len(pattern.findall(text))
        except re.error as e:
            _log.warning("search: invalid regex %r: %s", query, e)
        finally:
            result["done"] = True

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout)
    if not result["done"]:
        _log.warning(
            "search: regex %r timed out on %s after %.3fs (possible ReDoS)",
            query,
            path,
            timeout,
        )
        return (0, True)
    return (result["count"], False)
