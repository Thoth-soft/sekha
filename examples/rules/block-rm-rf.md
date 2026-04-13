---
severity: block
triggers: [PreToolUse]
matches: [Bash]
pattern: 'rm\s+-rf\s+(/|\*|~|\.)'
priority: 100
anchored: false
---
rm -rf against root, home, wildcard, or current-dir paths is almost never what you want. If you're sure, run it in a sandbox.

<!--
Use case: prevent catastrophic deletions in shells Claude spawns.

This pattern tightens the base 'rm\s+-rf' to only fire on dangerous targets
(/, *, ~, .) so safe uses like `rm -rf node_modules` or `rm -rf build/` still
work. If you want the broader rule, drop the trailing group and use
'rm\s+-rf' instead. If you want stricter, add more targets to the alternation
(e.g. '|\$HOME') or raise priority above 100.
-->
