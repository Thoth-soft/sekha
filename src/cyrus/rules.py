"""Cyrus rules engine — Rule dataclass stub for Task 2.

Expanded to the full public API (load_rules, evaluate, test_rule, clear_cache)
in Task 4. For now this module exists solely to host the `Rule` dataclass that
`cyrus._rulesutil._parse_rule_file` instantiates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    """Compiled rule loaded from a ~/.cyrus/rules/<name>.md markdown file.

    Frozen + hashable: `triggers` and `matches` are tuples (not lists) so the
    dataclass can live in sets / be used as a dict key if downstream callers
    need it. The compiled `pattern` is an `re.Pattern` — not equality-comparable
    in a stable way across processes, so equality on Rule instances is useful
    chiefly for (name, severity, priority) inspection rather than identity.
    """

    name: str
    severity: str                    # "block" | "warn"
    triggers: tuple[str, ...]
    matches: tuple[str, ...]
    pattern: re.Pattern[str]
    priority: int
    message: str
    raw_pattern: str
    anchored: bool
