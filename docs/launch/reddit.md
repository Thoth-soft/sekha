# Reddit launch post

Subreddit: r/ClaudeAI (primary), possibly r/LocalLLaMA if feeling brave.

## Title

Sekha - persistent memory for Claude Code (stays across sessions), plus
actually blocks destructive tool calls

## Body

I got tired of re-explaining my preferences to Claude Code every morning,
so I built Sekha: https://github.com/Thoth-soft/sekha

What it does:

1. **Remembers things across sessions.** Tell Claude "I prefer Postgres
   over MySQL for new projects" in one session. Close it. Open a new session
   tomorrow. Ask what database you prefer — it answers correctly, because
   it saved the preference as a markdown file and retrieved it on demand.
   Claude drives save/retrieve itself via 6 MCP tools (sekha_save,
   sekha_search, sekha_list, sekha_delete, sekha_status, sekha_add_rule).

2. **Actually blocks destructive tool calls.** This is the unique bit —
   every other memory system (Mem0, MemPalace, Letta, Zep, Basic Memory)
   stores rules but lets the AI ignore them. Sekha uses Claude Code's
   PreToolUse hook with `permissionDecision: "deny"` to hard-block tool
   calls matching user-defined regex patterns. Works even with
   `--dangerously-skip-permissions`. So you can write a rule for `rm -rf`
   and Claude literally cannot run that command.

Quick facts:

- Zero runtime dependencies (pure Python stdlib)
- Python 3.11+
- Cross-platform, 9-cell CI matrix (Win/mac/Linux x 3.11/3.12/3.13)
- 337 tests
- Hook latency: p50 under 50ms on Linux/macOS, ~300ms on Windows (Python
  cold-start floor)
- Plain markdown storage, no database, no embeddings, grep-based search
- MIT, pip install sekha

Scope honesty:

- **Hard enforcement only covers regex-matchable tool-input patterns.**
  `rm -rf`, `git push --force`, `DROP TABLE`, etc.
- **Behavioral rules** like "always confirm before acting" or "no guessing"
  stay prompt-level. The AI can ignore them. No PreReason hook exists at
  the Claude Code layer. README threat model explains why.

Install:

```
pip install sekha
sekha init
claude mcp add sekha -- sekha serve
```

Feedback I'd find valuable:

- Edge cases in memory retrieval (things it should find but doesn't, or
  things it finds but shouldn't)
- Rule patterns you want to ship for common foot-guns
- Other AI clients where this pattern could work (anything with a
  PreToolUse-equivalent hook)

Example rules in `examples/rules/` for copy-paste. Happy to answer questions
in comments.

## Tone notes (for when you edit)

- Reddit hates corporate-sounding launches. "I got tired of X" > "Introducing Y".
- Lead with the shared pain, not the feature list.
- Offer something useful in the first 60 seconds (the memory flow is the hook).
- Honest limitations go near the top, not buried at the bottom.
