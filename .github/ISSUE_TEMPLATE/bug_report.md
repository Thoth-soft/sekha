---
name: Bug report
about: Something isn't working as expected
title: "[BUG] "
labels: bug
---

## What happened

A clear, specific description of what went wrong. If Claude Code was involved,
include what you asked it to do and what you observed.

## What you expected

What should have happened instead.

## Reproduction

Minimum steps to reproduce. Ideally:

1. Run `sekha init` (or whatever the setup was)
2. Add rule: `<paste rule file contents>`
3. Invoke `<the tool call or command>`
4. Observe `<what you saw>`

## Environment

- Sekha version: (run `sekha --version` or check installed package)
- Python version: (run `python --version`)
- OS: Windows / macOS / Linux (and distro/version)
- Claude Code version: (from Claude Code's about/status)

## Sekha doctor output

Paste the output of `sekha doctor` (or `python -m sekha.cli doctor`):

```
<paste here>
```

## Relevant log lines

If `~/.sekha/hook-errors.log` has recent entries, paste the last ~20 lines:

```
<paste here>
```

## Additional context

Screenshots, config files, anything else that helps.
