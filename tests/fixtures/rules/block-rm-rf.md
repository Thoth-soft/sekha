---
severity: block
triggers: [PreToolUse]
matches: [Bash]
pattern: 'rm\s+-rf'
priority: 100
anchored: false
---
Never run rm -rf — catastrophic data loss.
