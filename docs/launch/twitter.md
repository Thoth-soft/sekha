# Twitter / X launch thread

Post from your account. 5 tweets. Tweet 1 standalone; tweets 2-5 reply to
form a thread.

## Tweet 1 (hook + memory GIF)

```
You tell Claude Code something in one session.
Open a new session tomorrow.
Claude forgot.

Sekha fixes that. Plus it can actually block rm -rf.

[attach docs/demo-memory.gif — cross-session memory demo]

https://github.com/Thoth-soft/sekha
```

## Tweet 2 (memory mechanism, reply to #1)

```
Sekha stores memories as plain markdown under ~/.sekha/. Claude calls
sekha_save via MCP when you tell it something worth keeping — preferences,
decisions, project context — and sekha_search to find it later.

Zero Python deps. No database. Just files + grep.
```

## Tweet 3 (blocking differentiator, reply to #2)

```
The other thing Sekha does that no one else does: hard-blocks destructive
tool calls.

Claude Code's PreToolUse hook can return permissionDecision: deny. That
survives --dangerously-skip-permissions.

Write a rule for rm -rf, git push --force, DROP TABLE. Claude literally
can't run it.

[attach docs/demo-block.gif — rm -rf blocked]
```

## Tweet 4 (honest scope, reply to #3)

```
What Sekha doesn't do: enforce behavioral rules like "always confirm
before acting." Those stay prompt-level and the AI can ignore them.

No PreReason hook exists. Sekha is a consistency enforcer for specific
tool patterns, not a security sandbox. README threat model is honest
about this.
```

## Tweet 5 (install + ask, reply to #4)

```
pip install sekha
sekha init
claude mcp add sekha -- sekha serve

Python 3.11+, cross-platform, MIT, 337 tests.

Trying persistent memory a different way? Would love to hear what
worked and what didn't.
```

## Hashtags (add to tweet 1 only, 2-3 max)

#ClaudeCode #AIcoding #MCP

## Timing

Same window as HN: Tuesday/Wednesday 8-10am PT. Retweet once ~6 hours later
to catch a second timezone.
