---
name: Rule idea
about: Propose a new example rule for examples/rules/
title: "[RULE] "
labels: rule-idea
---

## Rule name

Proposed filename (without `.md`). E.g., `block-docker-rmi-force`.

## What it guards against

The actual risk or bad behavior. A sentence or two. Ideally with a real-world
anecdote of when it would have saved you.

## Severity

- [ ] `block` — hard deny (rare, use only for actually destructive patterns)
- [ ] `warn` — inject reminder via additionalContext (soft, overridable)

## Tool matches

Which tools does this apply to? Usually a single entry like `Bash` or `Write`.
Wildcard `*` is allowed but be cautious — broad warn rules become noise fast
(we removed `warn-no-assumptions` for this reason).

## Proposed pattern

The regex. Make it as narrow as safely possible.

```
<regex>
```

## Proposed message

What Claude Code surfaces when the rule fires. Explain the risk and, if
useful, the safer alternative.

## Test cases

Commands/inputs that **should** fire the rule:

- `...`

Commands/inputs that **should not** fire the rule (false-positive check):

- `...`

## Anything else

Links to blog posts about the underlying risk, upstream issue trackers,
related rules already in `examples/rules/`.
