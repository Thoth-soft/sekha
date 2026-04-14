# Anthropic Discord post

Channel: `#project-showcase` or `#community-projects` (whatever the current name
is). Keep it short - Discord moves fast.

## Message (single post, no thread)

```
Shipped Sekha v0.1.0: https://github.com/Thoth-soft/sekha

Persistent memory for Claude Code. Plain markdown files under ~/.sekha/,
six MCP tools Claude can use to save/search/delete memories. Tell it a
preference in one session, ask about it in the next, it remembers.

Bonus: it's the only memory system I found that can actually HARD-BLOCK
dangerous tool calls. Uses the PreToolUse hook with permissionDecision:
deny, which survives --dangerously-skip-permissions. Write a rule for
rm -rf and Claude literally can't run it.

Zero Python deps, Python 3.11+, cross-platform. pip install sekha.

Scope honesty: hard-blocks only work for regex-matchable tool patterns.
Behavioral rules ("always confirm") stay prompt-level. Threat model in
README is explicit.

Feedback welcome - especially edge cases in memory retrieval and rule
ideas for common foot-guns.
```

## If a mod bumps you to #off-topic or similar

Fine. Repost verbatim and move on.

## Follow-up plan

- Check replies twice a day for the first week
- Offer to help any user who hits install issues — first-week supporters matter
- Don't repost in the same channel; instead drop into specific threads where
  someone complains about Claude forgetting things or ignoring rules
