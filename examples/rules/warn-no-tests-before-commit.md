---
severity: warn
triggers: [PreToolUse]
matches: [Bash]
pattern: 'git\s+commit'
priority: 20
anchored: false
---
You're about to commit. Did you run the tests? `python -m unittest discover -s tests` for this repo, or the equivalent for yours.

<!--
Use case: nudge before every `git commit` to run tests first.

Why warn, not block: tests-before-commit is a suggestion, not a hard gate.
The hook emits additionalContext to remind the AI without stopping the call
(HOOK-04 behavior). Raise severity to `block` if you want a hard gate -- be
warned that this will also block merge commits, amend commits, and
commit --allow-empty flows, which may be noisy.

Variations: narrow the pattern to 'git\s+commit\s+-m' to only fire on direct
commits (skipping interactive editor flows), or add a sibling rule matching
`npm test`, `cargo test`, etc. for your ecosystem.
-->
