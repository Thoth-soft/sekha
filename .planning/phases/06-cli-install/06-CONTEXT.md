# Phase 6: CLI & Install Experience - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Make the install path that MemPalace failed at. Ship `cyrus init`, `cyrus doctor`, `cyrus add-rule`, `cyrus list-rules`, plus idempotent settings.json merge and fresh-VM install tests on Win/macOS/Linux.

Exit criterion: a vanilla VM can run `pip install cyrus && cyrus init && claude mcp add cyrus -- cyrus serve` with zero manual fixups.

</domain>

<decisions>
## Implementation Decisions

### CLI Commands (add to existing `cyrus.cli`)

Already shipped (Phase 4/5): `cyrus hook run`, `cyrus hook bench`, `cyrus hook enable`, `cyrus hook disable`, `cyrus serve`

Add in Phase 6:
- `cyrus init` — one-shot setup
- `cyrus doctor` — diagnostic/health check
- `cyrus add-rule` — interactive rule wizard
- `cyrus list-rules` — show all rules with status

### `cyrus init`

Actions (in order):
1. Create `~/.cyrus/` tree with 5 category subdirs (reuse `cyrus.paths.cyrus_home()`)
2. Write default `~/.cyrus/config.json` if absent:
   ```json
   {"version": "0.0.0", "hook_enabled": true, "hook_budget_ms": {"p50": 50, "p95": 150}}
   ```
3. Back up `~/.claude/settings.json` → `~/.claude/settings.json.bak.<timestamp>` if exists
4. Merge hook registration into `~/.claude/settings.json`:
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "*",
           "hooks": [
             {"type": "command", "command": "cyrus hook run"}
           ]
         }
       ]
     }
   }
   ```
   If existing `hooks.PreToolUse` array exists, append (avoid duplicates by matching command string).
5. Print the `claude mcp add` command for user:
   ```
   Next step: register the MCP server:
     claude mcp add cyrus -- cyrus serve
   ```

**Idempotent:** running twice doesn't duplicate entries. Checks for existing hook matching `cyrus hook run` before appending.

**Windows:** uses `pathlib.Path.home()` → `C:\Users\<name>\.claude`. No special casing.

### `cyrus doctor`

Validates (each with clear pass/fail output):
1. `python --version` >= 3.11 ✓/✗
2. `cyrus` binary on PATH ✓/✗ (checks `shutil.which("cyrus")`)
3. `~/.cyrus/` exists and is writable ✓/✗
4. `~/.claude/settings.json` has `cyrus hook run` registered ✓/✗
5. Canary MCP handshake: spawn `cyrus serve`, send `initialize`, parse response, kill ✓/✗
6. Kill switch marker present? ✓/✗ (warn if yes, instruct `cyrus hook enable`)
7. Recent hook errors (last 24h) from `~/.cyrus/hook-errors.log`: count and show last 3 ✓/✗

Output format: colored pass/fail with ASCII-only chars (cp1252 safe):
```
[OK] Python 3.11.8
[OK] cyrus binary on PATH: /usr/local/bin/cyrus
[OK] ~/.cyrus writable
[OK] Hook registered in ~/.claude/settings.json
[OK] MCP server responds to initialize
[OK] Kill switch not active
[OK] No hook errors in last 24h

All checks passed. Cyrus is ready to use.
```

No emoji. No Unicode box-drawing. Just ASCII.

### `cyrus add-rule`

Interactive wizard (input() calls), or argparse flags for scripted use:
```
cyrus add-rule --name block-docker-prune --severity block --matches Bash --pattern "docker system prune.*-f" --message "Dangerous: forces docker prune without confirmation"
```

Validates:
- Name: alphanumeric + hyphens, doesn't collide with existing file
- Severity: block or warn
- Matches: non-empty list
- Pattern: compiles as regex (test via `re.compile`)
- Message: non-empty
- Priority: int 1-100 (default 50)
- Triggers: default ["PreToolUse"]

Writes to `~/.cyrus/rules/<name>.md` via `cyrus.storage.save_memory` (or direct write with proper frontmatter).

### `cyrus list-rules`

Shows all rules in `~/.cyrus/rules/` as a table:
```
NAME                  SEVERITY  MATCHES  PATTERN              STATUS
block-rm-rf           block     Bash     rm\s+-rf\s+/         OK
block-force-push      block     Bash     git.*push.*--force   OK
warn-no-tests         warn      Bash     git commit           OK
broken-rule           ?         ?        ?                    BROKEN (no severity)
```

Flags broken rules (ones that failed to parse in `cyrus.rules.load_rules`).

### Fresh-VM Install Test (HARD RELEASE GATE)

Requirement CLI-08: on vanilla Win/macOS/Linux VMs:
```bash
pip install cyrus==0.0.0
cyrus init
claude mcp add cyrus -- cyrus serve
```
...must succeed end-to-end with no manual fixups.

**Implementation in Phase 6:** since v0.0.0 isn't on PyPI yet (deferred from Plan 00-02), we test with editable install locally:
```bash
# On fresh VM:
pip install -e /path/to/cyrus
cyrus init
# Verify ~/.cyrus/ created, settings.json updated, no errors
```

CI job: add `install-test` matrix cell that does `pip install -e .` + `cyrus init` + `cyrus doctor` on each OS × Python version, asserts exit 0 on all.

### ASCII-Only Output (Cp1252 Safe)

Windows cmd.exe uses cp1252 encoding by default. Our CLI output must not include:
- Emoji (☒ ✓ ✗ 🚀)
- Unicode box-drawing (╭ ├ ╯)
- Arrows (→ ← ↑ ↓)

Use ASCII equivalents:
- `[OK]` / `[FAIL]` / `[WARN]` instead of ✓/✗/⚠
- `-->` instead of →
- `|` `+` `-` for tables (or just indent)

Ship a `force_utf8()` helper in `cyrus._cliutil` that attempts `sys.stdout.reconfigure("utf-8")` but falls back gracefully if not possible.

### Module Layout

Expand existing `cyrus.cli`:
```
src/cyrus/
    cli.py          # existing — add init, doctor, add-rule, list-rules commands
    _cliutil.py     # NEW — ASCII table formatting, settings.json merge, etc
    _init.py        # NEW — init command implementation (kept separate for testability)
    _doctor.py      # NEW — doctor command implementation
```

### Claude's Discretion

- Whether `cyrus init` opens an interactive prompt or just runs with defaults (suggest: default run, `--interactive` flag for wizard mode)
- Whether to suggest running `cyrus doctor` after init (suggest: yes, print "Verify with: cyrus doctor")
- Whether `cyrus add-rule` prompts interactively when no flags given, or errors out (suggest: interactive wizard if TTY, error if not)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cyrus.storage.save_memory`, `cyrus.storage.CATEGORIES` — for rule file writes
- `cyrus.rules.load_rules` — for list-rules parsing
- `cyrus.paths.cyrus_home()` — home dir
- `cyrus.cli` — existing argparse router, ADD subcommands
- `cyrus.server` — for doctor canary test (spawn + handshake)
- `cyrus.hook` — for doctor kill-switch check

### Established Patterns
- Stdlib only
- pathlib.Path
- unittest
- ASCII-only output for Windows compat

### Integration Points
- `~/.claude/settings.json` — hooks registration merge
- `~/.cyrus/` — config file + rule file writes
- Cross-platform: Windows cmd.exe, macOS Terminal, Linux bash all must work

</code_context>

<specifics>
## Specific Ideas

- Test fresh-VM install via CI matrix (add a new job cell `install-test` that runs on all 3 OSes)
- Backup `settings.json` before merge — always — with timestamp in filename
- `cyrus init` must handle case: no `~/.claude/settings.json` exists yet (create fresh with hooks block)
- `cyrus doctor --json` flag for machine-readable output (nice-to-have for CI)

</specifics>

<deferred>
## Deferred Ideas

- Web-based config UI — v2 (anti-feature)
- Auto-update cyrus — v2
- Interactive "rule builder" that suggests rules based on recent Bash history — v2
- Telemetry opt-in — v2 (privacy concerns)

</deferred>

---

*Phase: 06-cli-install*
*Context gathered: 2026-04-13 via infrastructure auto-detection*
