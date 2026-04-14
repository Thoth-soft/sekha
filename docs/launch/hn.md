# Show HN post

## Title (<= 80 chars)

Show HN: Sekha – persistent memory for Claude Code (plus it can block rm -rf)

## URL

https://github.com/Thoth-soft/sekha

## Body

Leave blank (HN rewards bare Show HN posts with no body).

## Planned first comment (to seed the thread, post immediately after submission)

```
Author here. Built this after six months of "I already told you my preferences
yesterday, why are you asking again?" with Claude Code.

Two things in one package:

1. Memory across sessions. Tell Claude "I prefer Postgres over MySQL for new
   projects." That becomes a markdown file in ~/.sekha/preferences/. Close
   Claude. Open it tomorrow. Ask what you prefer. It searches the files, finds
   the saved memory, answers correctly. Zero setup beyond `sekha init` +
   `claude mcp add sekha`. Claude drives save/search itself via 6 MCP tools.

2. Actually blocks dangerous tool calls. Claude Code ships a PreToolUse hook
   that can return `permissionDecision: "deny"`, which is enforced even with
   `--dangerously-skip-permissions`. No other memory system I looked at
   (MemPalace, Mem0, Letta, Zep, Basic Memory) uses it. Sekha does. Write a
   rule matching `rm -rf` as a regex, and Claude literally cannot run that
   command through the Bash tool. The hook subprocess vetoes before execution.

Implementation details:
- Python stdlib only, zero runtime deps, pure grep-based search
- Plain markdown files, no database, no ChromaDB, no embeddings
- 337 tests on a 9-cell CI (Win/mac/Linux x 3.11/3.12/3.13)
- Hook latency p50 <50ms on Linux/macOS (p95 <150ms), ~300ms on Windows
- ~4,000 lines of code total

Scope honesty (also in the README threat model):
- Hard enforcement only covers regex-matchable tool-input patterns. Behavioral
  rules like "always confirm before acting" stay prompt-level and the AI can
  ignore them. I proved this by having the AI violate such a rule mid-build.
  That class of rule needs something beyond PreToolUse — a PreReason hook
  doesn't exist.

Install:
    pip install sekha
    sekha init
    claude mcp add sekha -- sekha serve

MIT. Feedback very welcome, particularly from anyone who's hit walls trying
to solve persistent-memory-for-Claude a different way.
```

## Submission timing

- Tuesday or Wednesday
- 08:00 - 09:30 PT
- Stay online and responsive for 4-6 hours after post. Replies within 10 min
  dramatically improve thread quality.

## Response scripts for likely comments

- "But I already have CLAUDE.md for rules and system prompts for preferences."
  -> CLAUDE.md is loaded every session but it's static. Sekha stores
  conversational memories as the AI encounters them — what you told it
  yesterday, decisions from last week's debugging session, personal
  preferences — and recalls them when relevant. CLAUDE.md + Sekha is the
  combo, not either/or.

- "Why not just use --dangerously-skip-permissions and tell Claude to be
  careful?"
  -> That's what I did before. Claude listened ~70% of the time. 30% of
  `rm -rf` invocations hitting production data is bad odds. Hook-level deny
  is not 100% either (AI could use a different tool) but it closes the
  destructive-command class of foot-guns at the boundary.

- "What about Cursor/Cline/Continue?"
  -> The memory tools work everywhere MCP works. Hook enforcement is Claude
  Code-only in v0.1.0 because only Claude Code exposes the PreToolUse hook.
  The cross-client table in README makes this explicit.

- "Can it block X?"
  -> If X appears as a regex match in a Claude Code tool_input, yes. Example
  rules in `examples/rules/` cover rm -rf, force-push, DROP TABLE, and commit-
  without-tests. Rules are just markdown, easy to add.

- "Why Egyptian mythology?"
  -> Org is Thoth-soft (Thoth = scribe god of writing/knowledge). Sekha =
  Egyptian-etymology memory/remembrance word (caveat: not verified in English
  Wiktionary, proper Egyptological dictionary would confirm). The thematic
  fit: Thoth records, Sekha remembers.
```
